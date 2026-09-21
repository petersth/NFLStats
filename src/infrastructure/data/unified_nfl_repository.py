# src/infrastructure/data/unified_nfl_repository.py - NFL data repository

import logging
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict
import pandas as pd
import nflreadpy as nfl
from nflreadpy.config import CacheMode, update_config
from datetime import datetime

from ...domain.exceptions import DataAccessError, DataNotFoundError
from ..cache.simple_cache import SimpleCache
from ...utils.cache_policy import get_season_cache_ttl

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlayByPlaySnapshot:
    """A source frame and its original freshness deadline, kept together."""

    data: pd.DataFrame
    latest_game_date: pd.Timestamp
    expires_at: float


class UnifiedNFLRepository:
    """Unified repository for NFL data with caching."""

    REQUIRED_COLUMNS = {
        'season', 'season_type', 'week', 'game_id', 'game_date',
        'home_team', 'away_team', 'posteam', 'defteam', 'play_type'
    }
    
    # Columns consumed by calculations or presentation.
    NEEDED_COLUMNS_ESSENTIAL = [
        # Core game identification
        'season', 'season_type', 'week', 'game_id', 'game_date',
        'home_team', 'away_team', 'posteam', 'defteam',
        'home_score', 'away_score',
        
        # Essential game state
        'yardline_100', 'down', 'ydstogo', 'drive', 'play_type',
        
        # Essential play details
        'yards_gained', 'rush_attempt', 'pass_attempt', 'complete_pass',
        'sack', 'two_point_attempt',
        
        # Scoring (all needed for calculations)
        'touchdown', 'field_goal_result', 'extra_point_result', 
        'two_point_conv_result', 'td_team', 'posteam_score_post', 
        'defteam_score_post',
        
        # Turnovers and outcomes
        'interception', 'fumble_lost', 'first_down', 
        'first_down_rush', 'first_down_pass', 'first_down_penalty',
        'third_down_converted', 'third_down_failed',
        'fumbled_1_team', 'fumbled_2_team',
        'fumble_recovery_1_team', 'fumble_recovery_2_team', 'touchback',
        
        # Penalties
        'penalty_team', 'penalty_yards',
        
        # Calculated field (if needed by downstream)
        'success'
    ]
    CALCULATION_REQUIRED_COLUMNS = set(NEEDED_COLUMNS_ESSENTIAL) - {'success'}
    
    def __init__(self):
        # The repository owns a smaller pandas cache, so retaining nflreadpy's full
        # Polars frame would unnecessarily double memory usage in Streamlit Cloud.
        update_config(cache_mode=CacheMode.OFF, verbose=False, timeout=120)

        # Cache for NFL data with TTL and size limits
        self._cache = SimpleCache(
            default_ttl=1800,   # 30 minutes default TTL
            max_size=3          # Maximum cached seasons
        )
        
        logger.debug("Initialized UnifiedNFLRepository with caching")

    def _load_play_by_play_data(self, season: int) -> pd.DataFrame:
        """Load one nflverse season and retain only columns used by the app."""
        raw_data = nfl.load_pbp(season)
        available_columns = set(raw_data.columns)

        missing_required = self.CALCULATION_REQUIRED_COLUMNS - available_columns
        if missing_required:
            missing_list = ", ".join(sorted(missing_required))
            raise DataNotFoundError(
                f"The {season} nflverse dataset is missing required columns: {missing_list}"
            )

        selected_columns = [
            column for column in self.NEEDED_COLUMNS_ESSENTIAL
            if column in available_columns
        ]
        missing_optional = set(self.NEEDED_COLUMNS_ESSENTIAL) - available_columns
        if missing_optional:
            logger.warning(
                "The %s nflverse dataset is missing optional columns: %s",
                season,
                ", ".join(sorted(missing_optional)),
            )

        return raw_data.select(selected_columns).to_pandas()
    
    def get_play_by_play_data(self, season: int, progress_callback=None) -> Tuple[pd.DataFrame, pd.Timestamp]:
        """Load play-by-play data and its latest game date."""
        snapshot = self.get_play_by_play_snapshot(season, progress_callback)
        return snapshot.data, snapshot.latest_game_date

    def get_play_by_play_snapshot(self, season: int, progress_callback=None) -> PlayByPlaySnapshot:
        """Load source data with a deadline that derived caches must preserve."""
        try:
            if progress_callback:
                progress_callback.update(0.1, f"Checking for {season} data...")
            
            cache_key = f"pbp_{season}"
            ttl = get_season_cache_ttl(season)
            
            def fetch_nfl_data():
                """Fetch NFL play-by-play data from API."""
                if progress_callback:
                    progress_callback.update(0.3, f"Downloading {season} NFL data...")
                
                logger.info(f"Fetching fresh data for season {season} from nflverse")
                
                # Use background thread for download with progress updates
                import threading
                
                download_complete = threading.Event()
                nfl_data = None
                download_error = None
                
                def download_data():
                    nonlocal nfl_data, download_error
                    try:
                        nfl_data = self._load_play_by_play_data(season)
                    except Exception as e:
                        download_error = e
                    finally:
                        download_complete.set()
                
                # Optimize data types for memory efficiency after loading
                def optimize_data_types(df):
                    """Optimize DataFrame memory usage by converting data types."""
                    if df is None or len(df) == 0:
                        return df
                    
                    # Convert boolean-like float columns to actual booleans
                    boolean_cols = ['rush_attempt', 'pass_attempt', 'complete_pass', 'sack', 
                                   'two_point_attempt', 'touchdown', 'interception', 'fumble_lost',
                                   'first_down', 'first_down_rush', 'first_down_pass', 'first_down_penalty', 'success']
                    
                    for col in boolean_cols:
                        if col in df.columns:
                            df[col] = df[col].fillna(0).astype(bool)
                    
                    # Convert team columns to categories (huge memory savings for repeated values)
                    team_cols = ['home_team', 'away_team', 'posteam', 'defteam', 'td_team', 'penalty_team']
                    for col in team_cols:
                        if col in df.columns:
                            df[col] = df[col].astype('category')
                    
                    # Convert play_type to category
                    if 'play_type' in df.columns:
                        df['play_type'] = df['play_type'].astype('category')
                    
                    # Convert result columns to categories (limited values)
                    result_cols = ['field_goal_result', 'extra_point_result', 'two_point_conv_result']
                    for col in result_cols:
                        if col in df.columns:
                            df[col] = df[col].astype('category')
                    
                    # Convert small integer columns to smaller dtypes
                    if 'week' in df.columns:
                        df['week'] = df['week'].astype('int8')  # Weeks are 1-22
                    
                    return df
                
                # Start download
                download_thread = threading.Thread(target=download_data)
                download_thread.start()
                
                # Provide progress updates
                progress_step = 0.3
                while not download_complete.is_set():
                    download_complete.wait(0.5)
                    if progress_callback and progress_step < 0.8:
                        progress_step += 0.1
                        progress_callback.update(progress_step, f"Downloading {season} data...")
                
                download_thread.join()
                
                if download_error:
                    raise download_error
                
                if nfl_data is None or len(nfl_data) == 0:
                    raise DataNotFoundError(f"No NFL data found for season {season}")
                
                # Optimize memory usage of loaded data
                if progress_callback:
                    progress_callback.update(0.9, "Optimizing data types...")
                nfl_data = optimize_data_types(nfl_data)
                
                timestamp = pd.to_datetime(nfl_data['game_date']).max()
                if pd.isna(timestamp):
                    raise DataNotFoundError(
                        f"The {season} nflverse dataset has no valid game dates"
                    )
                    
                if progress_callback:
                    progress_callback.update(0.9, f"Processing {season} data...")
                
                logger.info(f"Successfully fetched {len(nfl_data)} plays for season {season}, latest game: {timestamp}")
                return PlayByPlaySnapshot(nfl_data, timestamp, time.time() + ttl)
            
            result = self._cache.get_or_compute(
                key=cache_key,
                compute_func=fetch_nfl_data,
                validator=self._is_valid_snapshot,
                ttl=ttl
            )
            
            if progress_callback:
                progress_callback.update(1.0, f"Loaded {season} data")
            
            return result
            
        except DataNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error loading NFL data for season {season}: {e}")
            raise DataAccessError(
                f"Failed to load {season} data: {str(e)}", season_year=season
            ) from e

    def get_data_source_name(self) -> str:
        """Get the name of this data source."""
        return "nflreadpy"

    def get_cached_play_by_play_data(
        self, season: int
    ) -> Optional[Tuple[pd.DataFrame, pd.Timestamp]]:
        """Return an already-cached season without triggering a download."""
        cache_key = f"pbp_{season}"

        snapshot = self._cache.get(cache_key, validator=self._is_valid_snapshot)
        if snapshot is None:
            return None
        return snapshot.data, snapshot.latest_game_date

    @staticmethod
    def _is_valid_snapshot(snapshot) -> bool:
        return (
            isinstance(snapshot, PlayByPlaySnapshot)
            and not snapshot.data.empty
            and 'season' in snapshot.data.columns
            and snapshot.latest_game_date is not None
            and time.time() < snapshot.expires_at
        )

    def clear_cache(self, season: Optional[int] = None) -> int:
        """Clear one cached season or the complete repository cache."""
        return self._cache.clear(f"pbp_{season}" if season is not None else None)

    def get_data_timestamp(self, season: int) -> Optional[datetime]:
        """Get the timestamp of when season data was last updated."""
        cached_data = self.get_cached_play_by_play_data(season)
        if cached_data and isinstance(cached_data, tuple) and len(cached_data) == 2:
            return cached_data[1].to_pydatetime() if cached_data[1] else None
        return None
    
    def get_cache_stats(self) -> Dict:
        """Get repository cache statistics."""
        return {
            'cache_type': 'nfl_repository_data_cache',
            'description': 'NFL play-by-play data cache with season-aware TTL',
            'stats': self._cache.get_stats()
        }
