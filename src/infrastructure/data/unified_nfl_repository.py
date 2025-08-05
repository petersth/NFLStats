# src/infrastructure/data/unified_nfl_repository.py - Unified NFL data repository

import logging
from typing import Optional, Tuple, Dict
import pandas as pd
import nfl_data_py as nfl
from datetime import datetime

from ...domain.exceptions import DataAccessError, DataNotFoundError
from ...utils.configuration_utils import apply_configuration_to_data

logger = logging.getLogger(__name__)



class UnifiedNFLRepository:
    """Unified repository for NFL data with pluggable storage strategies."""
    
    # Column list for efficient data fetching
    NEEDED_COLUMNS = [
        'game_id', 'play_id', 'season', 'season_type', 'week', 'game_date',
        'home_team', 'away_team', 'posteam', 'defteam', 'qtr', 'down', 
        'ydstogo', 'yardline_100', 'play_type', 'yards_gained', 'touchdown', 
        'first_down', 'rush_attempt', 'pass_attempt', 'sack', 'fumble', 
        'interception', 'penalty', 'two_point_attempt', 'fumble_lost', 
        'extra_point_result', 'two_point_conv_result', 'field_goal_result',
        'first_down_rush', 'first_down_pass', 'first_down_penalty', 
        'penalty_team', 'drive', 'complete_pass', 'incomplete_pass', 
        'pass_touchdown', 'rush_touchdown', 'passing_yards', 'rushing_yards', 
        'receiving_yards', 'td_team', 'penalty_yards', 'success', 'epa',
        'qb_kneel', 'posteam_score_post', 'defteam_score_post'
    ]
    
    def __init__(self):
        self._cache = {}  # In-memory cache for play-by-play data
    
    def get_play_by_play_data(self, season: int, progress_callback=None) -> Tuple[Optional[pd.DataFrame], Optional[pd.Timestamp]]:
        """Load play-by-play data for a given season."""
        try:
            if progress_callback:
                progress_callback.update(0.1, f"Checking for {season} data...")
            
            # Try to get from cache
            cache_key = f"pbp_{season}"
            data, timestamp = self._cache.get(cache_key, (None, None))
            
            # In-memory cache is always considered stale to ensure fresh data
            if data is not None and False:  # Always refresh for fresh data
                if progress_callback:
                    progress_callback.update(0.9, f"Using cached {season} data...")
                logger.info(f"Using cached data for season {season}")
                pd_timestamp = pd.Timestamp(timestamp) if timestamp else None
                return data, pd_timestamp
            
            # If no data found, we need to fetch it (both strategies)
            if progress_callback:
                progress_callback.update(0.3, f"Downloading {season} NFL data...")
            
            logger.info(f"Fetching fresh data for season {season} from NFL API")
            
            # Unfortunately nfl_data_py doesn't support progress callbacks,
            # but we can provide intermediate updates to keep the timer moving
            import threading
            import time
            
            download_complete = threading.Event()
            nfl_data = None
            download_error = None
            
            def download_data():
                nonlocal nfl_data, download_error
                try:
                    nfl_data = nfl.import_pbp_data([season], columns=self.NEEDED_COLUMNS)
                except Exception as e:
                    download_error = e
                finally:
                    download_complete.set()
            
            # Start download in background thread
            download_thread = threading.Thread(target=download_data)
            download_thread.start()
            
            # Provide progress updates while download is happening
            progress_step = 0.3
            while not download_complete.is_set():
                download_complete.wait(0.5)  # Check every 500ms
                if not download_complete.is_set() and progress_callback:
                    progress_step = min(progress_step + 0.05, 0.55)  # Gradually increase to 55%
                    progress_callback.update(progress_step, f"Downloading {season} NFL data...")
            
            # Wait for thread to complete and check for errors
            download_thread.join()
            if download_error:
                raise download_error
            
            if nfl_data is None or len(nfl_data) == 0:
                logger.error(f"No NFL data available for season {season}")
                return None, None
            
            # Get timestamp from latest game
            latest_game = pd.to_datetime(nfl_data['game_date']).max()
            timestamp = latest_game.to_pydatetime() if latest_game else datetime.now()
            
            if progress_callback:
                progress_callback.update(0.6, f"Storing {len(nfl_data)} plays...")
            
            # Store the data in memory cache
            self._cache[cache_key] = (nfl_data, timestamp)
            
            if progress_callback:
                progress_callback.update(1.0, f"Loaded {len(nfl_data)} plays for {season}")
            
            pd_timestamp = pd.Timestamp(timestamp)
            return nfl_data, pd_timestamp
            
        except Exception as e:
            logger.error(f"Error loading NFL data for season {season}: {e}")
            raise DataAccessError(f"Failed to load {season} data: {str(e)}")
    
    def get_team_data(self, pbp_data: pd.DataFrame, team_abbreviation: str, 
                     configuration: Optional[Dict] = None) -> pd.DataFrame:
        """Filter play-by-play data for a specific team."""
        if pbp_data is None or len(pbp_data) == 0:
            raise DataAccessError("No play-by-play data available")
        
        # Filter to plays where the team had possession
        team_data = pbp_data[pbp_data['posteam'] == team_abbreviation].copy()
        
        if len(team_data) == 0:
            available_teams = sorted(pbp_data['posteam'].dropna().unique())
            season_types = set(pbp_data['season_type'].unique()) if 'season_type' in pbp_data.columns else set()
            
            # Check for playoff-only data
            if season_types == {'POST'}:
                from ...config.nfl_constants import TEAM_DATA
                team_name = TEAM_DATA.get(team_abbreviation, {}).get('name', team_abbreviation)
                raise DataNotFoundError(
                    f"{team_name} did not make the playoffs. "
                    f"Try selecting 'Regular Season' or 'Regular Season + Playoffs' instead. "
                    f"Playoff teams available: {', '.join(available_teams)}"
                )
            
            raise DataNotFoundError(
                f"No data found for team {team_abbreviation}. "
                f"Available teams: {', '.join(available_teams)}"
            )
        
        # Apply configuration-based filtering if provided
        if configuration and len(team_data) > 0:
            team_data = apply_configuration_to_data(team_data, configuration)
        
        return team_data
    
    def refresh_season_data(self, season: int, progress_callback=None, force: bool = False) -> bool:
        """Refresh data for a season."""
        try:
            # Clear cache to force fresh data fetch
            cache_key = f"pbp_{season}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            # Force re-fetch by getting fresh data
            data, timestamp = self.get_play_by_play_data(season, progress_callback)
            return data is not None
            
        except Exception as e:
            logger.error(f"Failed to refresh season data: {e}")
            return False
    
    def get_league_aggregates(self, season: int, season_type: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get pre-calculated league aggregates if available."""
        return None  # In-memory strategy doesn't support aggregates
    
    def supports_aggregated_data(self) -> bool:
        """Whether this repository can provide pre-aggregated data."""
        return False
    
    def requires_calculation(self) -> bool:
        """Whether this repository requires calculation of statistics."""
        return True
    
    def get_data_source_name(self) -> str:
        """Human-readable name of this data source."""
        return "NFL Data (Direct API)"
    
    def get_data_timestamp(self, season: int) -> Optional[datetime]:
        """Get the timestamp for when data was last updated for a season."""
        cache_key = f"pbp_{season}"
        _, timestamp = self._cache.get(cache_key, (None, None))
        return timestamp