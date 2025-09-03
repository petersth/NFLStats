# src/infrastructure/cache/league_stats_cache.py - League statistics cache

import json
import logging
import time
from datetime import datetime
from typing import Dict, Tuple, Optional
import pandas as pd

from ...domain.exceptions import CacheError
from ...domain.entities import Team, Season
from ...utils.league_stats_utils import extract_stats_for_averaging, calculate_league_averages
from ...utils.configuration_utils import apply_configuration_to_data
from ...utils.ranking_utils import calculate_team_rankings, calculate_all_rankings
from .simple_cache import SimpleCache

logger = logging.getLogger(__name__)


def _process_team_parallel(args):
    """Process a single team's statistics (for multiprocessing)."""
    team_abbr, season_year, team_data, team_game_results = args
    try:
        # Import inside the function for multiprocessing
        from src.domain.entities import Team, Season
        from src.domain.nfl_stats_calculator import NFLStatsCalculator
        from src.domain.game_processor import GameProcessor
        from src.utils.league_stats_utils import extract_stats_for_averaging
        import pandas as pd
        
        # team_data is already a DataFrame - no conversion needed!
        
        if len(team_data) == 0:
            return None
        
        team = Team.from_abbreviation(team_abbr)
        season = Season(season_year)
        
        # Create a fresh calculator instance for this process
        calculator = NFLStatsCalculator()
        
        # Calculate season stats
        season_stats = calculator.calculate_season_stats(
            team_data, team, season, pre_calculated=None
        )
        
        # If we have game results, update TOER Allowed
        if season_stats and team_game_results:
            game_processor = GameProcessor()
            avg_toer, avg_toer_allowed = game_processor.get_team_toer_stats(team_game_results, team_abbr)
            season_stats.toer_allowed = avg_toer_allowed
        
        if season_stats:
            stats_for_avg = extract_stats_for_averaging(season_stats)
            return (team_abbr, season_stats, stats_for_avg)
        return None
            
    except Exception as e:
        import logging
        logging.error(f"Failed to process team {team_abbr}: {e}")
        return None


class LeagueStatsCache:
    """
    Single concrete league statistics cache class using NFL API data.
    
    This cache implementation uses only the NFL API (nfl_data_py library) for data retrieval.
    All statistics are computed from raw play-by-play data with in-memory caching for performance.
    """
    
    def __init__(self, nfl_data_repo=None, statistics_calculator=None):
        # Core dependencies
        self._nfl_data_repo = nfl_data_repo
        self._statistics_calculator = statistics_calculator
        
        # Initialize caches with different TTL strategies and memory limits
        from datetime import datetime
        current_year = datetime.now().year
        self._memory_cache = SimpleCache(
            default_ttl=1800,   # 30 minutes for computed statistics (reduced from 1 day)
            max_size=10         # Limit concurrent season computations (reduced from 100)
        )
        
        self._rankings_cache = SimpleCache(
            default_ttl=1800,   # 30 minutesfor rankings (reduced from 1 day)
            max_size=50         # More rankings entries (reduced from 500)
        )
        
        self._raw_data_cache = SimpleCache(
            default_ttl=1800,   # 30 minutes for raw data (reduced from 1 day)
            max_size=5          # Fewer but larger entries (reduced from 50)
        )
        
        logger.info("Initialized LeagueStatsCache with caching (TTL: 1 day for all caches)")
    
    def get_cached_play_data(self, season_year: int, season_type: str = 'ALL', configuration: Dict = None) -> Optional[pd.DataFrame]:
        """Get cached raw play-by-play data if available.
        
        Cache Strategy:
        - Raw NFL play-by-play data is cached independently of user configuration
        - Configuration settings only affect data processing, not data fetching
        - Uses hierarchical caching: complete season data cached as 'ALL', 
          then filtered for specific season types on retrieval
        - Provides significant performance improvement for repeated analyses
        
        Args:
            season_year: NFL season year (e.g., 2023)
            season_type: 'ALL', 'REG', or 'POST' 
            configuration: User configuration dict (doesn't affect caching)
            
        Returns:
            Cached DataFrame of play-by-play data or None if not cached
        """
        if configuration is None:
            configuration = {}

        complete_cache_key = f"raw_data_{season_year}_ALL"
        
        def validate_data(data_tuple):
            """Validate cached play-by-play data tuple."""
            if not isinstance(data_tuple, tuple) or len(data_tuple) != 2:
                return False
            pbp_data, timestamp = data_tuple
            return (pbp_data is not None and len(pbp_data) > 0 and 
                   'season_type' in pbp_data.columns and timestamp is not None)
        
        cached_result = self._raw_data_cache.get(complete_cache_key, validator=validate_data)
        
        if cached_result is None:
            return None
        
        # Extract DataFrame from tuple
        complete_data, _ = cached_result
        
        if complete_data is not None:
            # Filter the complete data by season type if needed
            if season_type and season_type != 'ALL':
                return complete_data[complete_data['season_type'] == season_type].copy()
            else:
                return complete_data.copy()
        
        # Fallback: try to get the specific season type cache (for backward compatibility)
        specific_cache_key = f"raw_data_{season_year}_{season_type}"
        return self._raw_data_cache.get(specific_cache_key, validator=validate_data)
    
    # === Main Interface Methods ===
    
    def get_or_compute_league_stats(self, season_year: int, season_type: str, 
                                   config_hash: str, _pbp_data: pd.DataFrame, 
                                   _statistics_calculator, _configuration: Dict, progress_callback=None) -> Tuple[Dict, Dict, datetime]:
        """Get or compute league statistics with simplified logic."""
        cache_key = self.get_cache_key(season_year, season_type, config_hash)
        
        try:
            # Use get_or_compute for main statistics
            def compute_stats():
                if self._nfl_data_repo:
                    logger.info(f"Computing fresh statistics for season {season_year} (cache miss or expired)")
                    return self._compute_from_raw_data(
                        season_year, season_type, _configuration, progress_callback
                    )
                else:
                    logger.error("No NFL data repository available")
                    return {}, {}, datetime.now()
            
            def validate_stats(result):
                """Validate computed statistics."""
                team_stats, league_averages, timestamp = result
                return (isinstance(team_stats, dict) and len(team_stats) > 0 and
                       isinstance(league_averages, dict) and timestamp is not None)
            
            # Use adaptive TTL based on season with memory optimization
            current_year = datetime.now().year
            ttl = 600 if season_year == current_year else 1800  # 10 min vs 30 min (reduced)
            
            # Check if data was already cached before calling get_or_compute
            was_cached = cache_key in self._memory_cache._cache
            
            result = self._memory_cache.get_or_compute(
                key=cache_key,
                compute_func=compute_stats,
                validator=validate_stats,
                ttl=ttl
            )
            
            team_stats_dict, league_averages, data_timestamp = result
            
            if not team_stats_dict:
                logger.warning(f"No statistics computed for season {season_year}")
                return {}, {}, datetime.now()
            
            # Ensure rankings are cached
            self._ensure_rankings_cached(cache_key, team_stats_dict)
            
            logger.info(f"Retrieved statistics for {len(team_stats_dict)} teams (cached: {was_cached})")
            return team_stats_dict, league_averages, data_timestamp
            
        except Exception as e:
            logger.error(f"Failed to get/compute league stats for {season_year}: {e}")
            raise CacheError(f"League stats computation failed: {e}", cache_key, "get_or_compute_league_stats")
    
    def get_team_rankings(self, team_abbr: str, team_stats_dict: Dict, cache_key: str = None) -> Dict:
        """Get pre-computed rankings for a specific team from cache."""
        try:
            # If no cache_key provided, create one from team_stats_dict
            if not cache_key and team_stats_dict:
                first_team_stats = list(team_stats_dict.values())[0]
                cache_key = self.get_cache_key(
                    first_team_stats.season.year,
                    'ALL',  # Default season type
                    'default'  # Default config hash
                )
            
            if cache_key:
                # Try to get cached rankings using the same key as _ensure_rankings_cached
                all_rankings = self._rankings_cache.get(cache_key)
                
                if all_rankings and team_abbr in all_rankings:
                    logger.debug(f"Retrieved cached rankings for {team_abbr}")
                    return all_rankings[team_abbr]
            
            # Fallback to fresh calculation if not in cache
            logger.info(f"Calculating fresh rankings for {team_abbr} (not found in cache)")
            return calculate_team_rankings(team_abbr, team_stats_dict)
                
        except Exception as e:
            logger.error(f"Failed to get team rankings for {team_abbr}: {e}")
            # Fallback to fresh calculation
            return calculate_team_rankings(team_abbr, team_stats_dict)
    
    def get_cache_info(self) -> Dict:
        """Get comprehensive information about current cache state."""
        return {
            'cache_type': 'league_stats_simple',
            'description': 'League statistics cache with TTL and validation',
            'memory_cache': self._memory_cache.get_stats(),
            'rankings_cache': self._rankings_cache.get_stats(),
            'raw_data_cache': self._raw_data_cache.get_stats(),
            'data_source': 'nfl_library',
            'total_entries': (self._memory_cache.get_stats()['size'] + 
                            self._rankings_cache.get_stats()['size'] + 
                            self._raw_data_cache.get_stats()['size'])
        }
    
    # === Utility Methods (formerly in base class) ===
    
    def get_cache_key(self, season_year: int, season_type: str, config_hash: str) -> str:
        """Generate cache key for league stats lookup."""
        try:
            key_data = {
                'season_year': season_year,
                'season_type': season_type,
                'config_hash': config_hash,
                'cache_type': self.__class__.__name__
            }
            key_string = json.dumps(key_data, sort_keys=True)
            import hashlib
            return hashlib.md5(key_string.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to generate cache key: {e}")
            raise CacheError(f"Cache key generation failed: {e}", operation="get_cache_key")
    
    def get_config_hash(self, configuration: Dict) -> str:
        """Generate hash for configuration to detect changes.
        
        Only hashes the configuration settings that affect statistics calculation:
        - include_qb_kneels_rushing
        - include_qb_kneels_success_rate
        - include_spikes_completion
        - include_spikes_success_rate
        
        This reduces cache fragmentation by ignoring unrelated config changes.
        """
        try:
            # Extract only the relevant configuration keys that affect stats
            relevant_config = {
                'include_qb_kneels_rushing': configuration.get('include_qb_kneels_rushing', False),
                'include_qb_kneels_success_rate': configuration.get('include_qb_kneels_success_rate', False),
                'include_spikes_completion': configuration.get('include_spikes_completion', False),
                'include_spikes_success_rate': configuration.get('include_spikes_success_rate', False)
            }
            
            from ...utils.config_hasher import get_config_hash
            return get_config_hash(relevant_config)
        except Exception as e:
            logger.error(f"Failed to generate config hash: {e}")
            raise CacheError(f"Config hash generation failed: {e}", operation="get_config_hash")
    
    def clear_cache(self, season_year: Optional[int] = None) -> Dict[str, int]:
        """Clear cached league statistics."""
        try:
            cleared_stats = {}
            
            if season_year:
                # Pattern-based clearing for specific season
                pattern = f"_{season_year}_"
                cleared_stats['memory'] = self._memory_cache.clear(pattern)
                cleared_stats['rankings'] = self._rankings_cache.clear(pattern)
                cleared_stats['raw_data'] = self._raw_data_cache.clear(pattern)
                logger.info(f"Cleared cache for season {season_year}: {cleared_stats}")
            else:
                # Clear all cached data
                cleared_stats['memory'] = self._memory_cache.clear()
                cleared_stats['rankings'] = self._rankings_cache.clear()
                cleared_stats['raw_data'] = self._raw_data_cache.clear()
                logger.info(f"Cleared all cached league statistics: {cleared_stats}")
                
            return cleared_stats
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise CacheError(f"Cache clear operation failed: {e}", operation="clear_cache")
    
    def clear_repository_cache(self, season_year: Optional[int] = None) -> int:
        """Clear repository cache separately to avoid serialization issues.
        
        This method should be called separately from clear_cache to ensure
        the repository's cache is also cleared when needed.
        """
        try:
            if self._nfl_data_repo and hasattr(self._nfl_data_repo, '_cache'):
                if season_year:
                    # Clear specific season
                    pattern = f"pbp_{season_year}"
                    count = self._nfl_data_repo._cache.clear(pattern)
                    logger.info(f"Cleared {count} repository cache entries for season {season_year}")
                else:
                    # Clear all
                    count = self._nfl_data_repo._cache.clear()
                    logger.info(f"Cleared {count} repository cache entries")
                return count
            return 0
        except Exception as e:
            logger.error(f"Failed to clear repository cache: {e}")
            return 0
    
    def force_cleanup(self) -> Dict[str, int]:
        """Force cleanup of expired entries across all caches.
        
        Returns:
            Dictionary with cleanup counts for each cache type
        """
        try:
            cleanup_stats = {
                'memory': self._memory_cache.force_cleanup(),
                'rankings': self._rankings_cache.force_cleanup(), 
                'raw_data': self._raw_data_cache.force_cleanup()
            }
            
            total_cleaned = sum(cleanup_stats.values())
            if total_cleaned > 0:
                logger.info(f"Force cleanup removed {total_cleaned} expired entries: {cleanup_stats}")
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Failed to force cleanup: {e}")
            raise CacheError(f"Force cleanup failed: {e}", operation="force_cleanup")
    
    # === Private Implementation Methods ===
    
    def _compute_from_raw_data(self, season_year: int, season_type: str, configuration: Dict, progress_callback=None) -> Tuple[Dict, Dict, datetime]:
        """Use raw data when aggregates unavailable."""
        try:
            if not self._nfl_data_repo:
                logger.error("No NFL data repository available for raw data computation")
                return {}, {}, datetime.now()
            
            # Use caching for raw play-by-play data
            complete_cache_key = f"raw_data_{season_year}_ALL"
            
            def fetch_pbp_data():
                """Fetch play-by-play data from repository."""
                fetch_start = time.time()
                if progress_callback:
                    progress_callback.update(0.4, "Fetching NFL data from API...")
                pbp_data, data_timestamp = self._nfl_data_repo.get_play_by_play_data(season_year, progress_callback)
                fetch_end = time.time()
                logger.info(f"NFL data fetch took {fetch_end - fetch_start:.2f}s")
                
                if pbp_data is None or len(pbp_data) == 0:
                    logger.warning(f"No raw data found for season {season_year}")
                    return None, datetime.now()
                
                return (pbp_data, data_timestamp)
            
            def validate_pbp_data(data_tuple):
                """Validate cached play-by-play data."""
                if not isinstance(data_tuple, tuple) or len(data_tuple) != 2:
                    return False
                pbp_data, timestamp = data_tuple
                return (pbp_data is not None and len(pbp_data) > 0 and 
                       'season' in pbp_data.columns and timestamp is not None)
            
            # Use season-aware TTL for raw data with memory optimization
            current_year = datetime.now().year
            raw_data_ttl = 900 if season_year == current_year else 3600  # 15 min vs 1 hour (reduced)
            
            data_result = self._raw_data_cache.get_or_compute(
                key=complete_cache_key,
                compute_func=fetch_pbp_data,
                validator=validate_pbp_data,
                ttl=raw_data_ttl
            )
            
            if data_result is None or data_result[0] is None:
                logger.warning(f"Failed to fetch raw data for season {season_year}")
                return {}, {}, datetime.now()
            
            pbp_data, data_timestamp = data_result
            logger.info(f"Retrieved complete dataset for season {season_year} ({len(pbp_data)} plays)")
            
            # Now filter by season type and apply configuration for this specific request
            if progress_callback:
                progress_callback.update(0.7, "Applying filters...")
                
            filter_start = time.time()
            # Memory optimization: Use views instead of copies where possible
            if season_type and season_type != 'ALL':
                filtered_data = pbp_data[pbp_data['season_type'] == season_type].copy()
            else:
                filtered_data = pbp_data.copy()
            
            # Apply configuration filtering to the data before calculating statistics
            if configuration:
                filtered_data = apply_configuration_to_data(filtered_data, configuration)
            filter_end = time.time()
            logger.info(f"Data filtering took {filter_end - filter_start:.2f}s")
            
            if progress_callback:
                progress_callback.update(0.8, "Processing team statistics...")
                
            from ...domain.game_processor import GameProcessor
            game_processor = GameProcessor()
            
            # Process all games to get TOER results for all teams
            logger.info("Processing all games for TOER calculations...")
            game_results_by_team = game_processor.process_all_games(filtered_data)
            
            # Calculate statistics for all teams in the filtered data
            teams = sorted(filtered_data['posteam'].dropna().unique())
            team_stats_dict = {}
            all_stats_for_averaging = []
            
            try:
                from joblib import Parallel, delayed
                use_joblib = True
                backend = 'loky'  # Better for CPU-bound tasks
            except ImportError:
                from concurrent.futures import ProcessPoolExecutor, as_completed
                from multiprocessing import cpu_count
                use_joblib = False
            
            start_team_processing = time.time()
            
            if use_joblib:
                # Use joblib for efficient parallel processing
                from multiprocessing import cpu_count
                num_processes = min(cpu_count(), 8, len(teams))
                logger.info(f"Processing {len(teams)} teams using joblib with {num_processes} processes")
                
                # Memory optimization: Only pass necessary columns for processing
                team_data_list = []
                for team_abbr in teams:
                    team_data = filtered_data[filtered_data['posteam'] == team_abbr]
                    if len(team_data) > 0:
                        # Memory optimization: reset index and drop unnecessary data
                        team_data = team_data.reset_index(drop=True)
                        # Include game results for TOER Allowed calculation
                        team_game_results = game_results_by_team.get(team_abbr, [])
                        team_data_list.append((team_abbr, season_year, team_data, team_game_results))
                
                # Process in parallel using joblib
                results = Parallel(n_jobs=num_processes, backend=backend)(
                    delayed(_process_team_parallel)(args) for args in team_data_list
                )
                
                # Collect results
                for result in results:
                    if result:
                        team_abbr, season_stats, stats_for_avg = result
                        team_stats_dict[team_abbr] = season_stats
                        all_stats_for_averaging.append(stats_for_avg)
            else:
                # Fallback to ProcessPoolExecutor
                team_data_args = []
                for team_abbr in teams:
                    team_data = filtered_data[filtered_data['posteam'] == team_abbr]
                    if len(team_data) > 0:
                        # Memory optimization: reset index and drop unnecessary data
                        team_data = team_data.reset_index(drop=True)
                        # Include game results for TOER Allowed calculation
                        team_game_results = game_results_by_team.get(team_abbr, [])
                        team_data_args.append((team_abbr, season_year, team_data, team_game_results))
                
                num_processes = min(cpu_count(), 8, len(team_data_args))
                logger.info(f"Processing {len(team_data_args)} teams using {num_processes} processes")
                
                with ProcessPoolExecutor(max_workers=num_processes) as executor:
                    future_to_team = {
                        executor.submit(_process_team_parallel, args): args[0] 
                        for args in team_data_args
                    }
                    
                    for future in as_completed(future_to_team):
                        try:
                            result = future.result(timeout=10)
                            if result:
                                team_abbr, season_stats, stats_for_avg = result
                                team_stats_dict[team_abbr] = season_stats
                                all_stats_for_averaging.append(stats_for_avg)
                        except Exception as e:
                            team_abbr = future_to_team[future]
                            logger.error(f"Failed to process team {team_abbr}: {e}")
            
            end_team_processing = time.time()
            logger.info(f"Team processing took {end_team_processing - start_team_processing:.2f}s for {len(teams)} teams (parallel)")
            
            if progress_callback:
                progress_callback.update(0.95, "Computing league averages...")
            league_averages = calculate_league_averages(all_stats_for_averaging)
            timestamp = data_timestamp if data_timestamp else datetime.now()
            
            return team_stats_dict, league_averages, timestamp
            
        except Exception as e:
            logger.error(f"Raw data computation failed: {e}")
            return {}, {}, datetime.now()
    
    def _ensure_rankings_cached(self, cache_key: str, team_stats_dict: Dict) -> None:
        """Ensure rankings are computed and cached."""
        if not team_stats_dict:
            return
            
        def compute_rankings():
            """Compute rankings for all teams."""
            logger.info(f"Computing rankings for all {len(team_stats_dict)} teams...")
            all_rankings = calculate_all_rankings(team_stats_dict)
            logger.info(f"Pre-computed rankings for {len(all_rankings)} teams")
            return all_rankings
        
        def validate_rankings(rankings):
            """Validate computed rankings."""
            return (isinstance(rankings, dict) and len(rankings) > 0 and 
                   all(isinstance(team_ranking, dict) for team_ranking in rankings.values()))
        
        self._rankings_cache.get_or_compute(
            key=cache_key,
            compute_func=compute_rankings,
            validator=validate_rankings
        )
    
    
    def _is_cache_valid_for_season(self, cached_data: Dict, season_year: int) -> bool:
        """Check if cached data is still valid for a season."""
        try:
            computed_at = cached_data.get('computed_at')
            if not computed_at:
                return False
            
            now = datetime.now()
            current_year = now.year
            
            # For completed seasons, cache is always valid
            if season_year < current_year:
                return True
            
            # For current/ongoing season, check if cache is recent
            from ...config.nfl_constants import CACHE_TTL_CURRENT_SEASON_HOURS
            age_hours = (now - computed_at).total_seconds() / 3600
            return age_hours < CACHE_TTL_CURRENT_SEASON_HOURS
            
        except Exception as e:
            logger.warning(f"Error checking cache validity: {e}")
            return False