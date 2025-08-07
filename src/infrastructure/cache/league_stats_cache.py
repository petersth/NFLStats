# src/infrastructure/cache/league_stats_cache.py - Simplified single concrete cache class

import json
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
import pandas as pd

from ...domain.exceptions import CacheError
from ...domain.entities import Team, Season
from ...utils.league_stats_utils import extract_stats_for_averaging, calculate_league_averages
from ...utils.configuration_utils import apply_configuration_to_data
from ...utils.ranking_utils import calculate_team_rankings, calculate_all_rankings

logger = logging.getLogger(__name__)


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
        
        # Simple in-memory caches
        self._memory_cache = {}
        self._rankings_cache = {}
        self._raw_data_cache = {}  # Cache for raw play-by-play data
        
        logger.info("Initialized LeagueStatsCache using NFL API with in-memory caching")
    
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
        complete_data = self._raw_data_cache.get(complete_cache_key)
        
        if complete_data is not None:
            # Filter the complete data by season type if needed
            if season_type and season_type != 'ALL':
                return complete_data[complete_data['season_type'] == season_type].copy()
            else:
                return complete_data.copy()
        
        # Fallback: try to get the specific season type cache (for backward compatibility)
        specific_cache_key = f"raw_data_{season_year}_{season_type}"
        return self._raw_data_cache.get(specific_cache_key)
    
    # === Main Interface Methods ===
    
    def get_or_compute_league_stats(self, season_year: int, season_type: str, 
                                   config_hash: str, _pbp_data: pd.DataFrame, 
                                   _statistics_calculator, _configuration: Dict, progress_callback=None) -> Tuple[Dict, Dict, datetime]:
        """Get or compute league statistics with simplified logic."""
        cache_key = self.get_cache_key(season_year, season_type, config_hash)
        
        try:
            # Check memory cache first
            cached_result = self._get_cached_data(cache_key, season_year)
            if cached_result:
                self._ensure_rankings_cached(cache_key, cached_result[0])
                return cached_result
            
            # Compute league statistics
            logger.info(f"Computing league statistics for {season_year} {season_type}")
            
            if self._nfl_data_repo:
                team_stats_dict, league_averages, data_timestamp = self._compute_from_raw_data(
                    season_year, season_type, _configuration, progress_callback
                )
            else:
                logger.error("No NFL data repository available")
                return {}, {}, datetime.now()
            
            if not team_stats_dict:
                logger.warning(f"No statistics computed for season {season_year}")
                return {}, {}, datetime.now()
            
            # Cache rankings and results
            self._ensure_rankings_cached(cache_key, team_stats_dict)
            self._cache_results(cache_key, team_stats_dict, league_averages, data_timestamp, season_year)
            
            logger.info(f"Computed and cached statistics for {len(team_stats_dict)} teams")
            return team_stats_dict, league_averages, data_timestamp
            
        except Exception as e:
            logger.error(f"Failed to get/compute league stats for {season_year}: {e}")
            raise CacheError(f"League stats computation failed: {e}", cache_key, "get_or_compute_league_stats")
    
    def get_team_rankings(self, team_abbr: str, team_stats_dict: Dict) -> Dict:
        """Get pre-computed rankings for a specific team."""
        # Always calculate fresh rankings from the current team_stats_dict
        # to ensure consistency with the displayed statistics
        logger.info(f"Calculating fresh rankings for {team_abbr} to ensure consistency")
        try:
            return calculate_team_rankings(team_abbr, team_stats_dict)
        except Exception as e:
            logger.error(f"Failed to calculate team rankings for {team_abbr}: {e}")
            raise CacheError(f"Team rankings calculation failed: {e}", operation="get_team_rankings")
    
    def get_cache_info(self) -> Dict:
        """Get information about current cache state."""
        return {
            'cache_type': 'league_stats',
            'description': 'Simplified league statistics cache',
            'cached_items': len(self._memory_cache),
            'rankings_cached_items': len(self._rankings_cache),
            'data_source': 'nfl_library'
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
        """Generate hash for configuration to detect changes."""
        try:
            from ...utils.config_hasher import get_config_hash
            return get_config_hash(configuration)
        except Exception as e:
            logger.error(f"Failed to generate config hash: {e}")
            raise CacheError(f"Config hash generation failed: {e}", operation="get_config_hash")
    
    def clear_cache(self, season_year: Optional[int] = None) -> None:
        """Clear cached league statistics."""
        try:
            if season_year:
                # Remove only caches for specific season
                keys_to_remove = [k for k, v in self._memory_cache.items() 
                                if v.get('season_year') == season_year]
                for key in keys_to_remove:
                    del self._memory_cache[key]
                logger.info(f"Cleared cache for season {season_year}")
            else:
                # Clear all cached data
                self._memory_cache.clear()
                self._rankings_cache.clear()
                logger.info("Cleared all cached league statistics")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise CacheError(f"Cache clear operation failed: {e}", operation="clear_cache")
    
    # === Private Implementation Methods ===
    
    def _compute_from_raw_data(self, season_year: int, season_type: str, configuration: Dict, progress_callback=None) -> Tuple[Dict, Dict, datetime]:
        """Use raw data when aggregates unavailable."""
        try:
            if not self._nfl_data_repo:
                logger.error("No NFL data repository available for raw data computation")
                return {}, {}, datetime.now()
            
            complete_cache_key = f"raw_data_{season_year}_ALL"
            timestamp_cache_key = f"timestamp_{season_year}_ALL"
            
            pbp_data = self._raw_data_cache.get(complete_cache_key)
            data_timestamp = self._raw_data_cache.get(timestamp_cache_key)
            
            if pbp_data is None:
                # Fetch complete dataset (regular season + playoffs)
                if progress_callback:
                    progress_callback.update(0.4, "Fetching NFL data from API...")
                pbp_data, data_timestamp = self._nfl_data_repo.get_play_by_play_data(season_year, progress_callback)
                if pbp_data is None or len(pbp_data) == 0:
                    logger.warning(f"No raw data found for season {season_year}")
                    return {}, {}, datetime.now()
                
                # Cache both the raw unfiltered dataset and its timestamp
                self._raw_data_cache[complete_cache_key] = pbp_data
                self._raw_data_cache[timestamp_cache_key] = data_timestamp
                
                # Also ensure the repository's own cache has the timestamp
                if self._nfl_data_repo and hasattr(self._nfl_data_repo, '_cache'):
                    repo_cache_key = f"pbp_{season_year}"
                    self._nfl_data_repo._cache[repo_cache_key] = (pbp_data, data_timestamp)
                
                logger.info(f"Cached complete dataset for season {season_year}")
            else:
                logger.info(f"Using cached complete dataset for season {season_year}")
                # Use the cached timestamp (from original NFL data)
            
            # Now filter by season type and apply configuration for this specific request
            if progress_callback:
                progress_callback.update(0.7, "Applying filters...")
            filtered_data = pbp_data.copy()
            if season_type and season_type != 'ALL':
                filtered_data = filtered_data[filtered_data['season_type'] == season_type]
            
            # Apply configuration filtering to the data before calculating statistics
            if configuration:
                filtered_data = apply_configuration_to_data(filtered_data, configuration)
            
            if progress_callback:
                progress_callback.update(0.8, "Processing team statistics...")
            
            # Note: We don't cache the filtered data since configuration can change
            # The raw data is cached above and filtering is fast
            
            # Calculate statistics for all teams in the filtered data
            teams = sorted(filtered_data['posteam'].dropna().unique())
            team_stats_dict = {}
            all_stats_for_averaging = []
            
            for team_abbr in teams:
                try:
                    team = Team.from_abbreviation(team_abbr)
                    season = Season(season_year)
                    
                    # Get team-specific data from filtered dataset
                    team_data = filtered_data[filtered_data['posteam'] == team_abbr].copy()
                    if len(team_data) == 0:
                        continue
                    
                    # Calculate season stats
                    season_stats = self._statistics_calculator.calculate_season_stats(
                        team_data, team, season, pre_calculated=None
                    )
                    
                    if season_stats:
                        team_stats_dict[team_abbr] = season_stats
                        all_stats_for_averaging.append(extract_stats_for_averaging(season_stats))
                        
                except Exception as e:
                    logger.error(f"Failed to process team {team_abbr}: {e}")
                    continue
            
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
        if cache_key not in self._rankings_cache and team_stats_dict:
            logger.info(f"Computing rankings for all {len(team_stats_dict)} teams...")
            all_rankings = calculate_all_rankings(team_stats_dict)
            self._rankings_cache[cache_key] = all_rankings
            logger.info(f"Pre-computed rankings for {len(all_rankings)} teams")
    
    def _cache_results(self, cache_key: str, team_stats: Dict, 
                      league_averages: Dict, timestamp: datetime, season_year: int) -> None:
        """Cache the results in memory."""
        try:
            self._memory_cache[cache_key] = {
                'team_stats': team_stats,
                'league_averages': league_averages,
                'timestamp': timestamp,
                'computed_at': datetime.now(),
                'season_year': season_year
            }
        except Exception as e:
            logger.warning(f"Failed to cache results: {e}")
    
    def _get_cached_data(self, cache_key: str, season_year: int) -> Optional[Tuple[Dict, Dict, datetime]]:
        """Get data from memory cache if valid."""
        try:
            if cache_key in self._memory_cache:
                cached_data = self._memory_cache[cache_key]
                if self._is_cache_valid_for_season(cached_data, season_year):
                    logger.info(f"Using cached league statistics for season {season_year}")
                    return cached_data['team_stats'], cached_data['league_averages'], cached_data['timestamp']
                else:
                    # Remove stale cache
                    del self._memory_cache[cache_key]
            return None
        except Exception as e:
            logger.warning(f"Failed to retrieve cached data: {e}")
            return None
    
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