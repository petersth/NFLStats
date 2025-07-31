# src/infrastructure/cache/league_stats_cache.py - Simplified single concrete cache class

import json
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
import pandas as pd

from ...domain.exceptions import CacheError
from ...domain.entities import Team, Season
from ...utils.league_stats_utils import extract_stats_for_averaging, calculate_league_averages
from .utilities import TeamRankingCalculator

logger = logging.getLogger(__name__)


class LeagueStatsCache:
    """
    Single concrete league statistics cache class.
    
    Simplified from the previous abstract base class + concrete implementation pattern.
    All functionality is now in one place without unnecessary abstraction.
    """
    
    def __init__(self, aggregated_repo=None, nfl_data_repo=None, 
                 statistics_calculator=None, config_service=None, use_database=True):
        # Core dependencies
        self._aggregated_repo = aggregated_repo
        self._nfl_data_repo = nfl_data_repo
        self._statistics_calculator = statistics_calculator
        self._config_service = config_service
        self._use_database = use_database
        
        # Simple in-memory caches
        self._memory_cache = {}
        self._rankings_cache = {}
        self._raw_data_cache = {}  # Cache for raw play-by-play data
        
        data_source = "database" if use_database else "NFL library"
        logger.info(f"Initialized LeagueStatsCache using {data_source}")
    
    def get_cached_play_data(self, season_year: int, season_type: str = 'ALL', configuration: Dict = None) -> Optional[pd.DataFrame]:
        """Get cached raw play-by-play data if available."""
        if configuration is None:
            configuration = {}
        
        cache_key = f"raw_data_{season_year}_{season_type}_{hash(str(configuration))}"
        return self._raw_data_cache.get(cache_key)
    
    # === Main Interface Methods ===
    
    def get_or_compute_league_stats(self, season_year: int, season_type: str, 
                                   config_hash: str, _pbp_data: pd.DataFrame, 
                                   _statistics_calculator, _configuration: Dict) -> Tuple[Dict, Dict, datetime]:
        """Get or compute league statistics with simplified logic."""
        cache_key = self.get_cache_key(season_year, season_type, config_hash)
        
        try:
            # Check memory cache first
            cached_result = self._get_cached_data(cache_key, season_year)
            if cached_result:
                self._ensure_rankings_cached(cache_key, cached_result[0])
                return cached_result
            
            # Compute using simplified two-path logic
            logger.info(f"Computing league statistics for {season_year} {season_type}")
            
            if self._use_database and self._aggregated_repo:
                # Path 1: Use aggregated data when available
                team_stats_dict, league_averages, data_timestamp = self._compute_from_aggregates(
                    season_year, season_type, _configuration
                )
            elif self._nfl_data_repo:
                # Path 2: Use raw data from NFL library
                team_stats_dict, league_averages, data_timestamp = self._compute_from_raw_data(
                    season_year, season_type, _configuration
                )
            else:
                logger.error("No data source available")
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
        # Check if we have pre-computed rankings
        for rankings in self._rankings_cache.values():
            if team_abbr in rankings:
                return rankings[team_abbr]
        
        # Fallback to calculating on-demand if not cached
        logger.info(f"No pre-computed rankings found for {team_abbr}, calculating on-demand")
        try:
            return TeamRankingCalculator.calculate_team_rankings(team_abbr, team_stats_dict)
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
            'data_source': 'database' if self._use_database else 'nfl_library'
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
            from ...utils.config_hasher import ConfigHasher
            return ConfigHasher.get_simple_hash(configuration)
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
    
    def _compute_from_aggregates(self, season_year: int, season_type: str, configuration: Dict) -> Tuple[Dict, Dict, datetime]:
        """Use materialized views for fast computation."""
        try:
            # Get aggregated data
            aggregated_data = self._aggregated_repo.get_all_teams_season_stats(season_year, season_type)
            
            if len(aggregated_data) == 0:
                # Fallback to raw data if no aggregates
                return self._compute_from_raw_data(season_year, season_type, configuration)
            
            # Process aggregated data
            team_stats_dict = {}
            all_stats_for_averaging = []
            
            for _, row in aggregated_data.iterrows():
                try:
                    team_abbr = row['posteam']
                    team = Team.from_abbreviation(team_abbr)
                    season = Season(season_year)
                    
                    # Use consistent calculation logic (same as orchestrator)
                    # Get team-specific raw data and calculate using standard methods
                    season_stats = self._calculate_season_stats_consistently(team, season, season_year, season_type, configuration)
                    
                    if season_stats:
                        team_stats_dict[team_abbr] = season_stats
                        all_stats_for_averaging.append(extract_stats_for_averaging(season_stats))
                        
                except Exception as e:
                    logger.warning(f"Failed to process aggregated data for team {row.get('posteam', 'unknown')}: {e}")
                    continue
            
            league_averages = calculate_league_averages(all_stats_for_averaging)
            data_timestamp = self._aggregated_repo.get_aggregate_freshness() or datetime.now()
            
            return team_stats_dict, league_averages, data_timestamp
            
        except Exception as e:
            logger.error(f"Aggregated computation failed: {e}")
            # Fallback to raw data
            return self._compute_from_raw_data(season_year, season_type, configuration)
    
    def _calculate_season_stats_consistently(self, team: Team, season: Season, season_year: int, season_type: str, configuration: Dict):
        """Calculate season stats using consistent logic (same as orchestrator)."""
        try:
            # Use the orchestrator's approach: get team-specific raw data efficiently
            if hasattr(self._aggregated_repo, '_query_executor') and self._aggregated_repo._query_executor:
                # Build team-specific query for efficiency (same as orchestrator)
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
                
                params = {'season': season_year, 'posteam': team.abbreviation}
                result = self._aggregated_repo._query_executor.execute_query(query, params)
                
                if result:
                    team_data = pd.DataFrame(result)
                    
                    # Apply season type filter if needed
                    if season_type and season_type != 'ALL':
                        team_data = team_data[team_data['season_type'] == season_type]
                    
                    # Apply configuration if needed  
                    if configuration and self._config_service:
                        team_data = self._config_service.apply_configuration_to_data(team_data, configuration)
                    
                    # Use the same calculation logic as orchestrator
                    return self._statistics_calculator.calculate_season_stats(team_data, team, season)
            
            # Fallback: should not happen in aggregate strategy, but handle gracefully
            logger.warning(f"Could not get team-specific data for {team.abbreviation}, returning None")
            return None
            
        except Exception as e:
            logger.error(f"Failed to calculate consistent season stats for {team.abbreviation}: {e}")
            return None
    
    def _compute_from_raw_data(self, season_year: int, season_type: str, configuration: Dict) -> Tuple[Dict, Dict, datetime]:
        """Use raw data when aggregates unavailable."""
        try:
            if not self._nfl_data_repo:
                logger.error("No NFL data repository available for raw data computation")
                return {}, {}, datetime.now()
            
            # Always try to get complete dataset first (check if already cached)
            complete_cache_key = f"raw_data_{season_year}_ALL_{hash(str(configuration))}"
            pbp_data = self._raw_data_cache.get(complete_cache_key)
            data_timestamp = None
            
            if pbp_data is None:
                # Fetch complete dataset (regular season + playoffs)
                pbp_data, data_timestamp = self._nfl_data_repo.get_play_by_play_data(season_year)
                if pbp_data is None or len(pbp_data) == 0:
                    logger.warning(f"No raw data found for season {season_year}")
                    return {}, {}, datetime.now()
                
                # Apply configuration filtering to complete dataset
                if self._config_service and configuration:
                    pbp_data = self._config_service.apply_configuration_to_data(pbp_data, configuration)
                
                # Cache the complete dataset
                self._raw_data_cache[complete_cache_key] = pbp_data
                logger.info(f"Cached complete dataset for season {season_year}")
            else:
                logger.info(f"Using cached complete dataset for season {season_year}")
                # For cached data, we need a timestamp
                data_timestamp = datetime.now()
            
            # Now filter by season type for this specific request
            filtered_data = pbp_data.copy()
            if season_type and season_type != 'ALL':
                filtered_data = filtered_data[filtered_data['season_type'] == season_type]
            
            # Cache the filtered data for this specific request too
            specific_cache_key = f"raw_data_{season_year}_{season_type}_{hash(str(configuration))}"
            self._raw_data_cache[specific_cache_key] = filtered_data
            
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
            from .utilities.team_ranking_calculator import TeamRankingCalculator
            all_rankings = TeamRankingCalculator.calculate_all_rankings(team_stats_dict)
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
            
            # For current/ongoing season, check if cache is recent (24 hours)
            age_hours = (now - computed_at).total_seconds() / 3600
            return age_hours < 24
            
        except Exception as e:
            logger.warning(f"Error checking cache validity: {e}")
            return False