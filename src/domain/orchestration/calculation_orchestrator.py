# src/domain/orchestration/calculation_orchestrator.py - Clean orchestration of data sources

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd

from ..entities import Team, Season, SeasonStats, GameStats, TeamRecord
from ..services import ConfigurationService
from ..interfaces.repository import DataRepositoryInterface
# Note: LeagueStatsCacheInterface removed - use concrete class directly

logger = logging.getLogger(__name__)


class CalculationOrchestrator:
    """Orchestrates between two data strategies for optimal performance.
    
    1. FRESH NFL DATA: Download fresh data from NFL API, cache in memory for session
    2. DATABASE OPTIMIZED: Use efficient team-specific database queries for same calculations

    Both strategies use identical calculation logic and produce identical results.
    The only difference is data source efficiency.

        """
    
    def __init__(
        self,
        data_repository: DataRepositoryInterface,
        statistics_calculator,  # NFLStatsCalculator - concrete class
        league_cache,  # LeagueStatsCache - concrete class
        configuration_service: ConfigurationService
    ):
        self._data_repository = data_repository
        self._statistics_calculator = statistics_calculator
        self._league_cache = league_cache
        self._configuration_service = configuration_service
    
    @property
    def league_cache(self):
        """Provide access to league cache for rankings calculation."""
        return self._league_cache
    
    @property
    def statistics_calculator(self):
        """Provide access to statistics calculator."""
        return self._statistics_calculator
    
    def calculate_team_analysis(
        self, 
        team: Team, 
        season: Season,
        season_type_filter: Optional[str] = None,
        configuration: Optional[Dict] = None,
        progress_callback = None
    ) -> Tuple[SeasonStats, List[GameStats], Optional[TeamRecord]]:
        """Calculate complete team analysis using optimal data path.
        
        Returns:
            Tuple of (season_stats, game_stats, team_record)
        """
        logger.info(f"Orchestrating calculation for {team.abbreviation} {season.year}")
        
        if progress_callback:
            progress_callback.update(0.1, "Selecting optimal data strategy...")
        
        # Determine optimal calculation strategy
        strategy = self._select_calculation_strategy(configuration)
        
        if progress_callback:
            progress_callback.update(0.2, f"Using {strategy} data path...")
        
        if strategy == "fresh_nfl":
            return self._calculate_from_fresh_nfl(team, season, season_type_filter, configuration, progress_callback)
        else:  # database_optimized
            return self._calculate_from_database_optimized(team, season, season_type_filter, configuration, progress_callback)
    
    def _select_calculation_strategy(self, configuration: Optional[Dict]) -> str:
        """Select calculation strategy:
        - fresh_nfl: Fetch fresh data from NFL API (with session caching)
        - database_optimized: Use team-specific database queries (same calculations, faster data access)
        """
        
        # Check if league cache is configured for fresh data (NFL library)
        is_using_fresh_data = (hasattr(self._league_cache, '_use_database') and 
                              not self._league_cache._use_database)
        
        if is_using_fresh_data:
            logger.info("Selected fresh NFL data strategy (direct API access)")
            return "fresh_nfl"
        else:
            logger.info("Selected database-optimized strategy (efficient team-specific queries)")
            return "database_optimized"
    
    def _calculate_from_fresh_nfl(
        self, 
        team: Team, 
        season: Season,
        season_type_filter: Optional[str],
        configuration: Optional[Dict],
        progress_callback = None
    ) -> Tuple[SeasonStats, List[GameStats], Optional[TeamRecord]]:
        """Calculate using fresh NFL data (with optional session caching)."""
        logger.info(f"Using fresh NFL data path for {team.abbreviation}")
        
        try:
            if progress_callback:
                progress_callback.update(0.3, "Loading from NFL API...")
            
            # Use league cache which has InMemoryStrategy repository
            config_hash = self._league_cache.get_config_hash(configuration or {})
            team_stats_dict, _, _ = self._league_cache.get_or_compute_league_stats(
                season.year, season_type_filter, config_hash,
                None, self._statistics_calculator, configuration or {}
            )
            
            if team.abbreviation not in team_stats_dict:
                logger.warning(f"Team {team.abbreviation} not found in fresh NFL data")
                return self._create_empty_results(team, season)
            
            season_stats = team_stats_dict[team.abbreviation]
            
            if progress_callback:
                progress_callback.update(0.8, "Computing game stats from fresh data...")
            
            # Get game stats from the cached raw data (avoids re-fetching from NFL API)
            pbp_data = self._league_cache.get_cached_play_data(season.year, season_type_filter or 'ALL', configuration or {})
            if pbp_data is not None:
                team_data = pbp_data[pbp_data['posteam'] == team.abbreviation].copy()
                
                # Apply filters
                if season_type_filter and season_type_filter != 'ALL':
                    team_data = team_data[team_data['season_type'] == season_type_filter]
                if configuration:
                    team_data = self._configuration_service.apply_configuration_to_data(team_data, configuration)
                
                game_stats = self._statistics_calculator.calculate_game_stats(team_data, team)
                team_record = self._statistics_calculator.calculate_team_record(team_data, team.abbreviation)
                
                return season_stats, game_stats, team_record
            else:
                logger.warning("No play data available for game stats from league cache repository")
                return season_stats, [], None
                
        except Exception as e:
            logger.error(f"Fresh NFL calculation failed: {e}")
            return self._create_empty_results(team, season)
    
    def _calculate_from_database_optimized(
        self, 
        team: Team, 
        season: Season,
        season_type_filter: Optional[str],
        configuration: Optional[Dict],
        progress_callback = None
    ) -> Tuple[SeasonStats, List[GameStats], Optional[TeamRecord]]:
        """Calculate using efficient team-specific database queries (same calculation logic as fresh NFL).
        
        This strategy:
        1. Validates database availability by checking if aggregates exist
        2. Uses efficient team-specific raw data queries (much faster than loading full dataset)  
        3. Uses identical calculation logic as fresh NFL strategy
        4. Produces identical results to fresh NFL strategy
        """
        logger.info(f"Using database-optimized path for {team.abbreviation}")
        
        try:
            # Check if database has data available (validate database connectivity)
            if progress_callback:
                progress_callback.update(0.3, "Validating database availability...")
            
            if self._can_use_database_queries(season.year, season_type_filter):
                logger.info(f"Database is available for {team.abbreviation}, using efficient team-specific queries")
                
                if progress_callback:
                    progress_callback.update(0.5, "Loading team data with optimized database queries...")
                
                team_data = self._get_team_raw_data(team, season, season_type_filter, configuration, progress_callback)
                if team_data is None or len(team_data) == 0:
                    logger.warning(f"No team data available for {team.abbreviation}, falling back to NFL API")
                    return self._calculate_from_nfl_fallback(team, season, season_type_filter, configuration, progress_callback)
                
                if progress_callback:
                    progress_callback.update(0.7, "Calculating season statistics...")
                
                # Use identical calculation logic as fresh NFL strategy
                season_stats = self._statistics_calculator.calculate_season_stats(team_data, team, season)
                
                if progress_callback:
                    progress_callback.update(0.8, "Computing game stats from team data...")
                
                # Get game stats using team-specific data (fast)
                game_stats, team_record = self._get_game_level_data_efficiently(
                    team, season, season_type_filter, configuration, progress_callback
                )
                
                return season_stats, game_stats, team_record
            
            # Database unavailable - fallback to NFL API
            logger.info(f"Database unavailable for {team.abbreviation}, falling back to NFL API")
            if progress_callback:
                progress_callback.update(0.4, "Database unavailable, fetching from NFL API...")
            
            return self._calculate_from_nfl_fallback(team, season, season_type_filter, configuration, progress_callback)
            
        except Exception as e:
            logger.error(f"Database-optimized calculation failed: {e}, falling back to NFL API")
            return self._calculate_from_nfl_fallback(team, season, season_type_filter, configuration, progress_callback)
    
    def _calculate_from_nfl_fallback(
        self, 
        team: Team, 
        season: Season,
        season_type_filter: Optional[str],
        configuration: Optional[Dict],
        progress_callback = None
    ) -> Tuple[SeasonStats, List[GameStats], Optional[TeamRecord]]:
        """Fallback to NFL API when database aggregates fail."""
        try:
            # Create a temporary InMemoryStrategy repository for NFL API access
            from ...infrastructure.data.unified_nfl_repository import UnifiedNFLRepository, InMemoryStrategy
            nfl_repo = UnifiedNFLRepository(self._configuration_service, InMemoryStrategy())
            
            # Get data from NFL API
            pbp_data, _ = nfl_repo.get_play_by_play_data(season.year, progress_callback)
            if pbp_data is None or len(pbp_data) == 0:
                logger.warning(f"No NFL API data available for season {season.year}")
                return self._create_empty_results(team, season)
            
            # Filter to team
            team_data = pbp_data[pbp_data['posteam'] == team.abbreviation].copy()
            if len(team_data) == 0:
                logger.warning(f"No NFL API data found for team {team.abbreviation}")
                return self._create_empty_results(team, season)
            
            # Apply filters
            if season_type_filter and season_type_filter != 'ALL':
                team_data = team_data[team_data['season_type'] == season_type_filter]
            if configuration:
                team_data = self._configuration_service.apply_configuration_to_data(team_data, configuration)
            
            # Calculate stats
            season_stats = self._statistics_calculator.calculate_season_stats(team_data, team, season)
            game_stats = self._statistics_calculator.calculate_game_stats(team_data, team)
            team_record = self._statistics_calculator.calculate_team_record(team_data, team.abbreviation)
            
            return season_stats, game_stats, team_record
            
        except Exception as e:
            logger.error(f"NFL API fallback failed: {e}")
            return self._create_empty_results(team, season)
    
    def _get_game_stats_from_nfl_fallback(
        self,
        season_stats: 'SeasonStats',
        team: Team, 
        season: Season,
        season_type_filter: Optional[str],
        configuration: Optional[Dict],
        progress_callback = None
    ) -> Tuple['SeasonStats', List['GameStats'], Optional['TeamRecord']]:
        """Get game stats from NFL API when we have season stats from aggregates."""
        try:
            # Use NFL API just for game-level data
            _, game_stats, team_record = self._calculate_from_nfl_fallback(
                team, season, season_type_filter, configuration, progress_callback
            )
            return season_stats, game_stats, team_record
            
        except Exception as e:
            logger.error(f"Game stats fallback failed: {e}")
            return season_stats, [], None
    
    def _can_use_database_queries(self, season_year: int, season_type_filter: Optional[str]) -> bool:
        """Check if database has data available (simple validation, not used for calculations)."""
        try:
            # Just check if we can get some aggregated data to validate database connectivity
            aggregates = self._data_repository.get_league_aggregates(season_year, season_type_filter)
            return aggregates is not None and len(aggregates) > 0
        except Exception as e:
            logger.warning(f"Database validation failed: {e}")
            return False
    
    def _get_game_level_data_efficiently(self, team: Team, season: Season, season_type_filter: Optional[str], configuration: Optional[Dict], progress_callback = None) -> Tuple[List['GameStats'], Optional['TeamRecord']]:
        """Get game stats and team record efficiently using team-specific raw data (original pattern)."""
        try:
            if progress_callback:
                progress_callback.update(0.85, f"Loading {team.abbreviation} specific data for games...")
            
            # Get team-specific raw data efficiently
            team_data = self._get_team_raw_data(team, season, season_type_filter, configuration, progress_callback)
            if team_data is None or len(team_data) == 0:
                logger.warning(f"No raw data available for {team.abbreviation} game stats")
                return [], None
            
            if progress_callback:
                progress_callback.update(0.95, "Calculating game statistics...")
            
            # Use existing calculator methods with raw data (original approach)
            game_stats = self._statistics_calculator.calculate_game_stats(team_data, team)
            team_record = self._statistics_calculator.calculate_team_record(team_data, team.abbreviation)
            
            logger.info(f"Calculated {len(game_stats)} game stats for {team.abbreviation} using team-specific data")
            return game_stats, team_record
            
        except Exception as e:
            logger.warning(f"Failed to get game-level data efficiently: {e}")
            return [], None
    
    def _get_team_raw_data(self, team: Team, season: Season, season_type_filter: Optional[str], configuration: Optional[Dict], progress_callback = None) -> Optional[pd.DataFrame]:
        """Get filtered team data using efficient team-specific queries (original pattern)."""
        try:
            if progress_callback:
                progress_callback.update(0.4, f"Loading {team.abbreviation} specific data...")
            
            # Try to get team-specific data efficiently from database storage
            if hasattr(self._data_repository._storage, '_query_executor') and self._data_repository._storage._query_executor:
                team_data = self._fetch_team_specific_data_from_database(season.year, team.abbreviation)
                if team_data is not None and len(team_data) > 0:
                    if progress_callback:
                        progress_callback.update(0.6, "Applying filters...")
                    
                    # Apply season type filter
                    if season_type_filter and season_type_filter != 'ALL':
                        team_data = team_data[team_data['season_type'] == season_type_filter]
                    
                    # Apply configuration if needed
                    if configuration:
                        team_data = self._configuration_service.apply_configuration_to_data(team_data, configuration)
                    
                    logger.info(f"Loaded {len(team_data)} plays for {team.abbreviation} using team-specific database query")
                    return team_data
            
            # Fallback: get from full dataset (less efficient but works)
            logger.info(f"Using fallback approach for {team.abbreviation} team data")
            pbp_data, _ = self._data_repository.get_play_by_play_data(season.year, progress_callback)
            if pbp_data is not None:
                team_data = pbp_data[pbp_data['posteam'] == team.abbreviation].copy()
                
                # Apply filters
                if season_type_filter and season_type_filter != 'ALL':
                    team_data = team_data[team_data['season_type'] == season_type_filter]
                if configuration:
                    team_data = self._configuration_service.apply_configuration_to_data(team_data, configuration)
                
                return team_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get team raw data: {e}")
            return None
    
    def _fetch_team_specific_data_from_database(self, season_year: int, team_abbreviation: str) -> Optional[pd.DataFrame]:
        """Fetch data for a specific team directly from database (efficient approach)."""
        try:
            # Build a team-specific query for efficiency
            query = """
                SELECT game_id, posteam, season_type, game_date, home_team, away_team, defteam, week,
                       play_type, down, ydstogo, yards_gained, drive, yardline_100,
                       posteam_score_post, defteam_score_post,
                       rush_attempt, pass_attempt, sack, touchdown, first_down,
                       interception, fumble, fumble_lost, penalty, penalty_team, penalty_yards,
                       first_down_rush, first_down_pass, first_down_penalty,
                       complete_pass, incomplete_pass, pass_touchdown, rush_touchdown,
                       two_point_attempt, two_point_conv_result, extra_point_result, field_goal_result,
                       passing_yards, rushing_yards, receiving_yards, td_team, success, epa, qb_kneel
                FROM raw_play_data 
                WHERE season = %(season)s AND posteam = %(posteam)s
                ORDER BY game_id, play_id
            """
            
            params = {'season': season_year, 'posteam': team_abbreviation}
            result = self._data_repository._storage._query_executor.execute_query(query, params)
            
            if result:
                team_data = pd.DataFrame(result)
                logger.info(f"Retrieved {len(team_data)} plays for team {team_abbreviation} with targeted query")
                return team_data
            else:
                logger.warning(f"No data found for team {team_abbreviation} in season {season_year}")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to fetch team-specific data from database: {e}")
            return None
    
    def _create_empty_results(self, team: Team, season: Season) -> Tuple[SeasonStats, List[GameStats], Optional[TeamRecord]]:
        """Create empty results for error cases."""
        from ..entities import SeasonStats
        
        empty_season_stats = SeasonStats(
            team=team,
            season=season,
            games_played=0,
            avg_yards_per_play=0.0,
            total_yards=0,
            total_plays=0,
            turnovers_per_game=0.0,
            completion_pct=0.0,
            rush_ypc=0.0,
            sacks_per_game=0.0,
            third_down_pct=0.0,
            success_rate=0.0,
            first_downs_per_game=0.0,
            points_per_drive=0.0,
            redzone_td_pct=0.0,
            penalty_yards_per_game=0.0
        )
        
        return empty_season_stats, [], None