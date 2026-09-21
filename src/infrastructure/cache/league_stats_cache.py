# src/infrastructure/cache/league_stats_cache.py - League statistics cache

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple, Optional
import pandas as pd

from ...domain.exceptions import CacheError, DataNotFoundError
from ...domain.entities import Team, Season
from ...domain.game_processor import GameProcessor
from ...config.nfl_constants import VALID_TEAMS
from ...utils.league_stats_utils import extract_stats_for_averaging, calculate_league_averages
from ...utils.configuration_utils import apply_configuration_to_data
from ...utils.ranking_utils import calculate_team_rankings, calculate_all_rankings
from ...utils.season_utils import get_current_nfl_season_info
from .simple_cache import SimpleCache

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LeagueAnalysisSnapshot:
    """One calculation's source data and derived results, cached as a unit.

    The repository frame is shared, not copied for each configuration. Consumers
    must treat it as read-only and filter/copy before applying configuration.
    """

    team_stats: Dict
    league_averages: Dict
    data_timestamp: datetime
    complete_pbp_data: pd.DataFrame
    game_results: Dict


class LeagueStatsCache:
    """
    Single concrete league statistics cache class using nflverse data.
    
    This cache implementation uses nflverse data (via nflreadpy) for data retrieval.
    All statistics are computed from raw play-by-play data with in-memory caching for performance.
    """
    
    def __init__(self, nfl_data_repo=None, statistics_calculator=None):
        # Core dependencies
        self._nfl_data_repo = nfl_data_repo
        self._statistics_calculator = statistics_calculator
        
        # Initialize caches with different TTL strategies and memory limits
        self._memory_cache = SimpleCache(
            default_ttl=1800,   # 30 minutes for computed statistics (reduced from 1 day)
            max_size=10         # Limit concurrent season computations (reduced from 100)
        )
        
        self._rankings_cache = SimpleCache(
            default_ttl=1800,   # 30 minutesfor rankings (reduced from 1 day)
            max_size=50         # More rankings entries (reduced from 500)
        )

        logger.info("Initialized LeagueStatsCache with 30-minute statistics caches")
    
    def get_cached_play_data(self, season_year: int, season_type: str = 'ALL') -> Optional[pd.DataFrame]:
        """Get cached raw play-by-play data if available.
        
        Cache Strategy:
        - The repository owns the single raw play-by-play cache
        - Configuration settings only affect data processing, not data fetching
        - Complete seasons are filtered on retrieval without creating another raw cache
        - Provides significant performance improvement for repeated analyses
        
        Args:
            season_year: NFL season year (e.g., 2023)
            season_type: 'ALL', 'REG', or 'POST' 
        Returns:
            Cached DataFrame of play-by-play data or None if not cached
        """
        if not self._nfl_data_repo:
            return None

        cached_result = self._nfl_data_repo.get_cached_play_by_play_data(season_year)
        if cached_result is None:
            return None

        complete_data, _ = cached_result
        if season_type and season_type != 'ALL':
            return complete_data[complete_data['season_type'] == season_type].copy()
        return complete_data.copy()

    def get_play_data(
        self, season_year: int, season_type: str = 'ALL', progress_callback=None
    ) -> pd.DataFrame:
        """Return play data, loading it through the repository on a cache miss."""
        cached_data = self.get_cached_play_data(season_year, season_type)
        if cached_data is not None:
            return cached_data
        if not self._nfl_data_repo:
            raise CacheError("No NFL data repository available", operation="get_play_data")

        complete_data, _ = self._nfl_data_repo.get_play_by_play_data(
            season_year, progress_callback
        )
        if season_type and season_type != 'ALL':
            return complete_data[complete_data['season_type'] == season_type].copy()
        return complete_data.copy()

    def get_cached_game_results(
        self, season_year: int, season_type: str, config_hash: str
    ) -> Optional[Dict]:
        """Return game results from the currently cached aggregate snapshot."""
        cache_key = self.get_cache_key(season_year, season_type, config_hash)
        snapshot = self._memory_cache.get(cache_key)
        return snapshot.game_results if snapshot is not None else None
    
    # === Main Interface Methods ===
    
    def get_or_compute_league_stats(
        self,
        season_year: int,
        season_type: str,
        config_hash: str,
        configuration: Dict,
        progress_callback=None,
    ) -> Tuple[Dict, Dict, datetime]:
        """Return the aggregate view of a consistently cached analysis."""
        snapshot = self.get_or_compute_analysis_snapshot(
            season_year, season_type, config_hash, configuration, progress_callback
        )
        return snapshot.team_stats, snapshot.league_averages, snapshot.data_timestamp

    def get_or_compute_analysis_snapshot(
        self,
        season_year: int,
        season_type: str,
        config_hash: str,
        configuration: Dict,
        progress_callback=None,
    ) -> LeagueAnalysisSnapshot:
        """Load all inputs/results for an analysis with one TTL and eviction policy."""
        cache_key = self.get_cache_key(season_year, season_type, config_hash)
        
        try:
            # Use get_or_compute for main statistics
            def compute_stats():
                if self._nfl_data_repo:
                    logger.info(f"Computing fresh statistics for season {season_year} (cache miss or expired)")
                    return self._compute_from_raw_data(
                        season_year, season_type, configuration, cache_key, progress_callback
                    )
                raise CacheError("No NFL data repository available", cache_key, "compute_stats")
            
            def validate_stats(result):
                """Reject incomplete snapshots instead of mixing cache entries."""
                return (
                    isinstance(result, LeagueAnalysisSnapshot)
                    and isinstance(result.team_stats, dict) and bool(result.team_stats)
                    and isinstance(result.league_averages, dict)
                    and result.data_timestamp is not None
                    and isinstance(result.complete_pbp_data, pd.DataFrame)
                    and not result.complete_pbp_data.empty
                    and isinstance(result.game_results, dict) and bool(result.game_results)
                )
            
            # Use adaptive TTL based on season with memory optimization
            season_info = get_current_nfl_season_info()
            is_live_season = (
                season_year == season_info['current_season']
                and season_info['season_status'] in {'in_progress', 'playoffs'}
            )
            ttl = 600 if is_live_season else 1800
            
            # Check if data was already cached before calling get_or_compute
            was_cached = cache_key in self._memory_cache._cache
            
            result = self._memory_cache.get_or_compute(
                key=cache_key,
                compute_func=compute_stats,
                validator=validate_stats,
                ttl=ttl
            )
            
            # Ensure rankings are cached
            self._ensure_rankings_cached(cache_key, result.team_stats)
            
            logger.info(f"Retrieved statistics for {len(result.team_stats)} teams (cached: {was_cached})")
            return result
            
        except (CacheError, DataNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Failed to get/compute league stats for {season_year}: {e}")
            raise CacheError(
                f"League stats computation failed: {e}",
                cache_key,
                "get_or_compute_analysis_snapshot",
                e,
            ) from e
    
    def get_team_rankings(self, team_abbr: str, team_stats_dict: Dict, cache_key: str = None) -> Dict:
        """Return rankings belonging to the supplied aggregate snapshot."""
        if cache_key:
            all_rankings = self._ensure_rankings_cached(cache_key, team_stats_dict)
            return all_rankings.get(team_abbr, {})

        logger.info(f"Calculating fresh rankings for {team_abbr} (not found in cache)")
        return calculate_team_rankings(team_abbr, team_stats_dict)
    
    def get_cache_info(self) -> Dict:
        """Get comprehensive information about current cache state."""
        return {
            'cache_type': 'league_stats_simple',
            'description': 'League statistics cache with TTL and validation',
            'memory_cache': self._memory_cache.get_stats(),
            'rankings_cache': self._rankings_cache.get_stats(),
            'data_source': 'nflverse',
            'total_entries': (self._memory_cache.get_stats()['size'] + 
                            self._rankings_cache.get_stats()['size'])
        }
    
    # === Utility Methods (formerly in base class) ===
    
    def get_cache_key(self, season_year: int, season_type: str, config_hash: str) -> str:
        """Generate cache key for league stats lookup."""
        normalized_season_type = season_type or 'ALL'
        return f"league_stats:{season_year}:{normalized_season_type}:{config_hash}"
    
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
                'include_qb_kneels_rushing': configuration.get('include_qb_kneels_rushing', True),
                'include_qb_kneels_success_rate': configuration.get('include_qb_kneels_success_rate', True),
                'include_spikes_completion': configuration.get('include_spikes_completion', True),
                'include_spikes_success_rate': configuration.get('include_spikes_success_rate', True)
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
                pattern = f"league_stats:{season_year}:"
                cleared_stats['memory'] = self._memory_cache.clear(pattern)
                cleared_stats['rankings'] = self._rankings_cache.clear(pattern)
                logger.info(f"Cleared cache for season {season_year}: {cleared_stats}")
            else:
                cleared_stats['memory'] = self._memory_cache.clear()
                cleared_stats['rankings'] = self._rankings_cache.clear()
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
            if self._nfl_data_repo:
                count = self._nfl_data_repo.clear_cache(season_year)
                logger.info(f"Cleared {count} repository cache entries")
                return count
            return 0
        except Exception as e:
            logger.error(f"Failed to clear repository cache: {e}")
            raise CacheError(
                f"Repository cache clear failed: {e}",
                operation="clear_repository_cache",
                cause=e,
            ) from e
    
    def force_cleanup(self) -> Dict[str, int]:
        """Force cleanup of expired entries across all caches.
        
        Returns:
            Dictionary with cleanup counts for each cache type
        """
        try:
            cleanup_stats = {
                'memory': self._memory_cache.force_cleanup(),
                'rankings': self._rankings_cache.force_cleanup(),
            }
            
            total_cleaned = sum(cleanup_stats.values())
            if total_cleaned > 0:
                logger.info(f"Force cleanup removed {total_cleaned} expired entries: {cleanup_stats}")
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Failed to force cleanup: {e}")
            raise CacheError(f"Force cleanup failed: {e}", operation="force_cleanup")
    
    # === Private Implementation Methods ===
    
    def _compute_from_raw_data(
        self,
        season_year: int,
        season_type: str,
        configuration: Dict,
        cache_key: str,
        progress_callback=None,
    ) -> LeagueAnalysisSnapshot:
        """Use raw data when aggregates unavailable."""
        if not self._nfl_data_repo:
            raise CacheError("No NFL data repository available", cache_key, "raw_data")

        fetch_start = time.time()
        if progress_callback:
            progress_callback.update(0.4, "Fetching NFL data from nflverse...")
        pbp_data, data_timestamp = self._nfl_data_repo.get_play_by_play_data(
            season_year, progress_callback
        )
        logger.info("NFL data fetch took %.2fs", time.time() - fetch_start)

        if pbp_data is None or len(pbp_data) == 0:
            raise DataNotFoundError(f"No NFL data found for season {season_year}", season_year)

        if progress_callback:
            progress_callback.update(0.7, "Applying filters...")

        filter_start = time.time()
        if season_type and season_type != 'ALL':
            filtered_data = pbp_data[pbp_data['season_type'] == season_type].copy()
        else:
            filtered_data = pbp_data.copy()
        if configuration:
            filtered_data = apply_configuration_to_data(filtered_data, configuration)
        logger.info("Data filtering took %.2fs", time.time() - filter_start)

        if filtered_data.empty:
            raise DataNotFoundError(
                f"No {season_type or 'ALL'} play data found for season {season_year}",
                season_year,
                season_type,
            )

        if progress_callback:
            progress_callback.update(0.8, "Processing team statistics...")

        logger.info("Processing all games with the shared statistics calculator")
        game_results_by_team = self._statistics_calculator.process_all_games(filtered_data)
        team_data_by_abbr = self._group_team_data(filtered_data)
        teams = sorted(team_data_by_abbr)
        if not teams:
            raise DataNotFoundError(
                f"No valid NFL team play data found for season {season_year}",
                season_year,
                season_type,
            )

        start_team_processing = time.time()
        logger.info("Processing statistics for %s teams", len(teams))
        results = [
            self._calculate_team_statistics(
                team_abbr,
                season_year,
                team_data_by_abbr[team_abbr],
                game_results_by_team.get(team_abbr, []),
            )
            for team_abbr in teams
        ]

        team_stats_dict = {result[0]: result[1] for result in results}
        all_stats_for_averaging = [result[2] for result in results]
        missing_teams = sorted(set(teams) - set(team_stats_dict))
        if missing_teams:
            raise CacheError(
                f"Statistics were not calculated for: {', '.join(missing_teams)}",
                cache_key,
                "team_statistics",
            )

        logger.info(
            "Team processing took %.2fs for %s teams",
            time.time() - start_team_processing,
            len(teams),
        )
        if progress_callback:
            progress_callback.update(0.95, "Computing league averages...")

        league_averages = calculate_league_averages(all_stats_for_averaging)
        return LeagueAnalysisSnapshot(
            team_stats=team_stats_dict,
            league_averages=league_averages,
            data_timestamp=data_timestamp,
            complete_pbp_data=pbp_data,
            game_results=game_results_by_team,
        )

    @staticmethod
    def _group_team_data(filtered_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Group offensive data only for team identifiers supported by the app."""
        valid_offensive_data = filtered_data[
            filtered_data['posteam'].isin(VALID_TEAMS)
        ]
        ignored_possession_values = sorted(
            str(value)
            for value in filtered_data['posteam'].dropna().unique()
            if str(value) not in VALID_TEAMS and str(value).strip()
        )
        if ignored_possession_values:
            logger.warning(
                "Ignoring unsupported possession-team values: %s",
                ", ".join(ignored_possession_values),
            )

        return {
            str(team_abbr): team_data.copy()
            for team_abbr, team_data in valid_offensive_data.groupby(
                'posteam', sort=True, observed=True
            )
        }

    def _calculate_team_statistics(
        self, team_abbr: str, season_year: int, team_data: pd.DataFrame, team_game_results
    ):
        """Calculate one team using the cache's canonical statistics engine."""
        if team_data.empty:
            raise ValueError(
                f"Cannot calculate statistics for {team_abbr} without play data"
            )
        if not team_game_results:
            raise ValueError(
                f"No processed game results were produced for {team_abbr}"
            )

        avg_toer, avg_toer_allowed = GameProcessor.get_team_toer_stats(
            team_game_results, team_abbr
        )
        season_stats = self._statistics_calculator.calculate_season_stats(
            team_data,
            Team.from_abbreviation(team_abbr),
            Season(season_year),
            avg_toer=avg_toer,
            avg_toer_allowed=avg_toer_allowed,
        )
        return team_abbr, season_stats, extract_stats_for_averaging(season_stats)
    
    def _ensure_rankings_cached(self, cache_key: str, team_stats_dict: Dict) -> Dict:
        """Cache rankings together with the aggregate snapshot they describe.

        Aggregate refreshes replace the statistics dictionary. A longer ranking
        TTL or a different eviction policy must not reuse an earlier snapshot.
        Keep the snapshot reference so even callers holding older statistics get
        matching ranks rather than whichever ranks were cached most recently.
        """
        if not team_stats_dict:
            return {}
            
        def compute_rankings():
            """Compute rankings for all teams."""
            logger.info(f"Computing rankings for all {len(team_stats_dict)} teams...")
            all_rankings = calculate_all_rankings(team_stats_dict)
            logger.info(f"Pre-computed rankings for {len(all_rankings)} teams")
            return team_stats_dict, all_rankings
        
        def validate_rankings(result):
            snapshot, rankings = result
            return (snapshot is team_stats_dict and isinstance(rankings, dict)
                    and len(rankings) > 0
                    and all(isinstance(rank, dict) for rank in rankings.values()))
        
        _, rankings = self._rankings_cache.get_or_compute(
            key=cache_key,
            compute_func=compute_rankings,
            validator=validate_rankings
        )
        return rankings
