#!/usr/bin/env python3
"""
NFL Data Loader CLI Utility

A robust command-line tool for managing NFL play-by-play data in the database.
Supports validation, incremental loading, and data integrity checks.

Usage:
    python scripts/data_loader.py --season 2024 --validate
    python scripts/data_loader.py --season 2024 --force-refresh
    python scripts/data_loader.py --check-integrity
    python scripts/data_loader.py --list-seasons
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional, Set
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.infrastructure.database.query_executor import SupabaseQueryExecutor
from src.infrastructure.database.supabase_client import SupabaseClient
from src.domain.services import ConfigurationService
from src.infrastructure.data.unified_nfl_repository import UnifiedNFLRepository, DatabaseStrategy
from src.infrastructure.database.repositories.aggregated_stats_repository import AggregatedStatsRepository
import nfl_data_py as nfl

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_loader.log')
    ]
)
logger = logging.getLogger(__name__)


class DataLoaderCLI:
    """Command-line interface for NFL data loading and management."""
    
    def __init__(self):
        """Initialize the data loader with database connections."""
        try:
            self.client = SupabaseClient()
            if not self.client.connect():
                raise Exception("Failed to connect to database")
            
            self.executor = SupabaseQueryExecutor(self.client)
            self.config_service = ConfigurationService()
            
            # Try to get aggregated repository
            try:
                aggregated_repo = AggregatedStatsRepository(self.executor)
            except Exception:
                aggregated_repo = None
            
            # Create database strategy and unified repository
            storage_strategy = DatabaseStrategy(self.executor, aggregated_repo)
            self.nfl_repo = UnifiedNFLRepository(self.config_service, storage_strategy)
            
            logger.info("Data loader initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize data loader: {e}")
            sys.exit(1)
    
    def check_database_integrity(self) -> bool:
        """Check overall database integrity and report status."""
        logger.info("Checking database integrity...")
        
        seasons = self.get_available_seasons()
        if not seasons:
            logger.warning("No data found in database")
            return False
        
        total_issues = 0
        for season in seasons:
            issues = self.validate_season_data(season, verbose=True)
            total_issues += len(issues)
        
        if total_issues == 0:
            logger.info("✓ Database integrity check passed")
            return True
        else:
            logger.error(f"✗ Database integrity check failed ({total_issues} issues found)")
            return False
    
    def validate_season_data(self, season: int, verbose: bool = False) -> List[str]:
        """Validate data for a specific season and return list of issues."""
        issues = []
        
        # Try to get season data
        try:
            pbp_data, _ = self.nfl_repo.get_play_by_play_data(season)
            if pbp_data is None or len(pbp_data) == 0:
                issues.append(f"Season {season} not found in database")
                return issues
        except Exception as e:
            issues.append(f"Season {season} error loading data: {str(e)}")
            return issues
        
        # Check play count
        play_count = len(pbp_data)
        if play_count == 0:
            issues.append(f"Season {season} has no plays")
        elif play_count < 40000:  # Typical season has ~50k plays
            issues.append(f"Season {season} has unusually low play count: {play_count}")
        
        # Check team count
        teams = set(pbp_data['posteam'].dropna().unique())
        if len(teams) < 30:
            issues.append(f"Season {season} missing teams (found {len(teams)}, expected 32): {sorted(teams)}")
        
        # Check for missing required columns
        if len(pbp_data) > 0:
            required_cols = ['game_id', 'play_id', 'posteam', 'yards_gained', 'play_type']
            missing_cols = [col for col in required_cols if col not in pbp_data.columns]
            if missing_cols:
                issues.append(f"Season {season} missing required columns: {missing_cols}")
        
        if verbose:
            if issues:
                logger.warning(f"Season {season}: {len(issues)} issues found")
                for issue in issues:
                    logger.warning(f"  - {issue}")
            else:
                logger.info(f"Season {season}: ✓ ({play_count} plays, {len(teams)} teams)")
        
        return issues
    
    def get_available_seasons(self) -> List[int]:
        """Get list of seasons available in the database."""
        try:
            query = "SELECT DISTINCT season FROM raw_play_data ORDER BY season DESC"
            result = self.executor.execute_query(query)
            return [r['season'] for r in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get available seasons: {e}")
            return []
    
    def get_missing_data_for_season(self, season: int) -> Dict[str, any]:
        """Analyze what data is missing for a season."""
        logger.info(f"Analyzing missing data for season {season}...")
        
        # Get expected data from NFL
        try:
            logger.info(f"Fetching expected data for {season} from NFL...")
            expected_data = nfl.import_pbp_data([season], columns=['game_id', 'play_id', 'posteam'])
            if expected_data is None or len(expected_data) == 0:
                return {'error': f'No NFL data available for season {season}'}
            
            expected_plays = len(expected_data)
            expected_games = len(expected_data['game_id'].unique())
            # Filter out None/NaN values more carefully
            valid_teams = expected_data['posteam'].dropna()
            valid_teams = valid_teams[valid_teams.notna()]  # Double-check for NaN
            expected_teams = sorted(valid_teams.unique())
            
        except Exception as e:
            logger.error(f"Failed to fetch expected data: {e}")
            return {'error': str(e)}
        
        # Get actual data from database
        try:
            pbp_data, _ = self.nfl_repo.get_play_by_play_data(season)
            if pbp_data is None or len(pbp_data) == 0:
                return {
                    'status': 'missing',
                    'expected_plays': expected_plays,
                    'expected_games': expected_games,
                    'expected_teams': expected_teams,
                    'actual_plays': 0,
                    'actual_teams': [],
                    'missing_teams': expected_teams
                }
            
            actual_plays = len(pbp_data)
            actual_teams = sorted(pbp_data['posteam'].dropna().unique())
        except Exception:
            return {
                'status': 'missing',
                'expected_plays': expected_plays,
                'expected_games': expected_games,
                'expected_teams': expected_teams,
                'actual_plays': 0,
                'actual_teams': [],
                'missing_teams': expected_teams
            }
        missing_teams = sorted(set(expected_teams) - set(actual_teams))
        
        return {
            'status': 'partial' if missing_teams or actual_plays != expected_plays else 'complete',
            'expected_plays': expected_plays,
            'expected_games': expected_games,
            'expected_teams': expected_teams,
            'actual_plays': actual_plays,
            'actual_teams': actual_teams,
            'missing_teams': missing_teams,
            'play_difference': expected_plays - actual_plays
        }
    
    def load_season_data(self, season: int, force: bool = False, validate_only: bool = False) -> bool:
        """Load or validate data for a specific season."""
        logger.info(f"{'Validating' if validate_only else 'Loading'} data for season {season}...")
        
        # Analyze current state
        analysis = self.get_missing_data_for_season(season)
        if 'error' in analysis:
            logger.error(f"Cannot analyze season {season}: {analysis['error']}")
            return False
        
        status = analysis['status']
        
        if status == 'complete' and not force:
            logger.info(f"Season {season} is already complete ({analysis['actual_plays']} plays, {len(analysis['actual_teams'])} teams)")
            return True
        
        if validate_only:
            if status == 'complete':
                logger.info(f"✓ Season {season} validation passed")
                return True
            else:
                logger.warning(f"✗ Season {season} validation failed:")
                logger.warning(f"  Expected: {analysis['expected_plays']} plays, {len(analysis['expected_teams'])} teams")
                logger.warning(f"  Actual: {analysis['actual_plays']} plays, {len(analysis['actual_teams'])} teams")
                if analysis['missing_teams']:
                    logger.warning(f"  Missing teams: {analysis['missing_teams']}")
                return False
        
        # Perform the actual data loading
        logger.info(f"Loading season {season}... (Expected: {analysis['expected_plays']} plays)")
        
        class SimpleProgress:
            def update(self, progress, message):
                logger.info(f"[{progress*100:.1f}%] {message}")
        
        progress = SimpleProgress()
        success = self.nfl_repo.refresh_season_data(season, progress, force=force)
        
        if success:
            # Validate the result
            final_analysis = self.get_missing_data_for_season(season)
            if final_analysis['status'] == 'complete':
                logger.info(f"✓ Successfully loaded season {season} ({final_analysis['actual_plays']} plays, {len(final_analysis['actual_teams'])} teams)")
                return True
            else:
                logger.error(f"✗ Data loading incomplete for season {season}")
                logger.error(f"  Expected: {final_analysis['expected_plays']} plays")
                logger.error(f"  Loaded: {final_analysis['actual_plays']} plays")
                if final_analysis['missing_teams']:
                    logger.error(f"  Missing teams: {final_analysis['missing_teams']}")
                return False
        else:
            logger.error(f"Failed to load data for season {season}")
            return False
    
    def list_seasons_status(self):
        """List all seasons and their status."""
        logger.info("Season Status Report:")
        logger.info("=" * 50)
        
        # Check what seasons are available from NFL
        current_year = datetime.now().year
        nfl_seasons = list(range(1999, current_year + 1))  # NFL data typically goes back to 1999
        
        db_seasons = set(self.get_available_seasons())
        
        for season in reversed(nfl_seasons[-10:]):  # Show last 10 seasons
            if season in db_seasons:
                analysis = self.get_missing_data_for_season(season)
                if 'error' not in analysis:
                    status = analysis['status']
                    plays = analysis['actual_plays']
                    teams = len(analysis['actual_teams'])
                    
                    if status == 'complete':
                        logger.info(f"  {season}: ✓ Complete ({plays:,} plays, {teams} teams)")
                    else:
                        logger.warning(f"  {season}: ⚠ Incomplete ({plays:,} plays, {teams} teams)")
                        if analysis['missing_teams']:
                            logger.warning(f"           Missing: {', '.join(analysis['missing_teams'])}")
                else:
                    logger.warning(f"  {season}: ✗ Error checking status")
            else:
                logger.info(f"  {season}: - Not loaded")
    
    def cleanup_invalid_data(self):
        """Remove incomplete or invalid data from the database."""
        logger.info("Cleaning up invalid data...")
        
        seasons = self.get_available_seasons()
        removed_seasons = []
        
        for season in seasons:
            issues = self.validate_season_data(season)
            if issues:
                logger.warning(f"Season {season} has issues, considering for removal:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
                
                # Remove seasons with critical issues
                critical_issues = [i for i in issues if 'no plays' in i or 'missing teams' in i]
                if critical_issues:
                    logger.info(f"Removing invalid data for season {season}")
                    query = "DELETE FROM raw_play_data WHERE season = %(season)s"
                    self.executor.execute_command(query, {'season': season})
                    removed_seasons.append(season)
        
        if removed_seasons:
            logger.info(f"Removed data for seasons: {removed_seasons}")
        else:
            logger.info("No invalid data found to remove")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NFL Data Loader - Manage play-by-play data in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-seasons                    # Show status of all seasons
  %(prog)s --season 2024 --validate         # Check if 2024 data is complete
  %(prog)s --season 2024 --load             # Load missing 2024 data
  %(prog)s --season 2024 --load --force     # Force reload all 2024 data
  %(prog)s --check-integrity                # Check database integrity
  %(prog)s --cleanup                        # Remove incomplete data
        """
    )
    
    parser.add_argument('--season', type=int, help='Season year to operate on')
    parser.add_argument('--validate', action='store_true', help='Validate data without loading')
    parser.add_argument('--load', action='store_true', help='Load missing data')
    parser.add_argument('--force', action='store_true', help='Force reload even if data exists')
    parser.add_argument('--list-seasons', action='store_true', help='List all seasons and their status')
    parser.add_argument('--check-integrity', action='store_true', help='Check database integrity')
    parser.add_argument('--cleanup', action='store_true', help='Remove incomplete/invalid data')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize the CLI
    cli = DataLoaderCLI()
    
    try:
        if args.list_seasons:
            cli.list_seasons_status()
        
        elif args.check_integrity:
            success = cli.check_database_integrity()
            sys.exit(0 if success else 1)
        
        elif args.cleanup:
            cli.cleanup_invalid_data()
        
        elif args.season:
            if args.validate:
                success = cli.load_season_data(args.season, validate_only=True)
                sys.exit(0 if success else 1)
            elif args.load:
                success = cli.load_season_data(args.season, force=args.force)
                sys.exit(0 if success else 1)
            else:
                # Just show analysis for the season
                analysis = cli.get_missing_data_for_season(args.season)
                if 'error' in analysis:
                    logger.error(f"Error analyzing season {args.season}: {analysis['error']}")
                    sys.exit(1)
                else:
                    logger.info(f"Season {args.season} Analysis:")
                    logger.info(f"  Status: {analysis['status']}")
                    logger.info(f"  Expected: {analysis['expected_plays']} plays, {len(analysis['expected_teams'])} teams")
                    logger.info(f"  Actual: {analysis['actual_plays']} plays, {len(analysis['actual_teams'])} teams")
                    if analysis['missing_teams']:
                        logger.info(f"  Missing teams: {', '.join(analysis['missing_teams'])}")
        
        else:
            parser.print_help()
            logger.info("\nTip: Use --list-seasons to see the current status")
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()