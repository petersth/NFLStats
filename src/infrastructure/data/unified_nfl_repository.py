# src/infrastructure/data/unified_nfl_repository.py - NFL data repository

import logging
from typing import Optional, Tuple, Dict
import pandas as pd
import nfl_data_py as nfl
from datetime import datetime

from ...domain.exceptions import DataAccessError, DataNotFoundError
from ...utils.configuration_utils import apply_configuration_to_data
from ..cache.simple_cache import SimpleCache

logger = logging.getLogger(__name__)



class UnifiedNFLRepository:
    """Unified repository for NFL data with caching."""
    
    # Essential columns for NFL statistics calculation
    # Contains only columns actually used in the codebase (36 of 242 total columns)
    NEEDED_COLUMNS_ESSENTIAL = [
        # Core game identification
        'season', 'season_type', 'week', 'game_id', 'game_date',
        'home_team', 'away_team', 'posteam', 'defteam',
        
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
        
        # Penalties
        'penalty_team', 'penalty_yards',
        
        # Calculated field (if needed by downstream)
        'success'
    ]
    
    # Full column set (use only when specifically needed)
    NEEDED_COLUMNS = [
        # Game identification
        'season', 'season_type', 'week', 'game_id', 'game_date', 'old_game_id',
        'home_team', 'away_team', 'posteam', 'defteam',
        
        # Game state
        'side_of_field', 'yardline_100', 'quarter_seconds_remaining', 
        'half_seconds_remaining', 'game_seconds_remaining', 'game_half', 
        'quarter_end', 'drive', 'sp', 'qtr', 'down', 'goal_to_go', 'time', 
        'yrdln', 'ydstogo', 'ydsnet', 'desc',
        
        # Play details
        'play_type', 'yards_gained', 'shotgun', 'no_huddle', 'qb_dropback', 
        'qb_kneel', 'qb_spike', 'qb_scramble', 'pass_length', 'pass_location', 
        'air_yards', 'yards_after_catch', 'run_location', 'run_gap',
        
        # Scoring plays
        'field_goal_result', 'kick_distance', 'extra_point_result', 
        'two_point_conv_result', 'td_team', 'touchdown', 'pass_touchdown', 
        'rush_touchdown', 'return_touchdown',
        
        # Game management
        'home_timeouts_remaining', 'away_timeouts_remaining', 'timeout', 
        'timeout_team', 'posteam_timeouts_remaining', 'defteam_timeouts_remaining',
        
        # Scores
        'total_home_score', 'total_away_score', 'posteam_score', 'defteam_score', 
        'score_differential', 'posteam_score_post', 'defteam_score_post', 
        'score_differential_post',
        
        # Win probability and EPA
        'no_score_prob', 'opp_fg_prob', 'opp_safety_prob', 'opp_td_prob', 
        'fg_prob', 'safety_prob', 'td_prob', 'extra_point_prob', 
        'two_point_conversion_prob', 'ep', 'epa',
        'wp', 'def_wp', 'home_wp', 'away_wp', 'wpa', 'vegas_wpa', 'vegas_home_wpa', 
        'home_wp_post', 'away_wp_post', 'vegas_wp', 'vegas_home_wp',
        
        # Advanced EPA metrics
        'total_home_epa', 'total_away_epa', 'total_home_rush_epa', 'total_away_rush_epa', 
        'total_home_pass_epa', 'total_away_pass_epa', 'air_epa', 'yac_epa', 
        'comp_air_epa', 'comp_yac_epa', 'total_home_comp_air_epa', 'total_away_comp_air_epa', 
        'total_home_comp_yac_epa', 'total_away_comp_yac_epa', 'total_home_raw_air_epa', 
        'total_away_raw_air_epa', 'total_home_raw_yac_epa', 'total_away_raw_yac_epa',
        
        # Advanced WPA metrics
        'total_home_rush_wpa', 'total_away_rush_wpa', 'total_home_pass_wpa', 
        'total_away_pass_wpa', 'air_wpa', 'yac_wpa', 'comp_air_wpa', 'comp_yac_wpa', 
        'total_home_comp_air_wpa', 'total_away_comp_air_wpa', 'total_home_comp_yac_wpa', 
        'total_away_comp_yac_wpa', 'total_home_raw_air_wpa', 'total_away_raw_air_wpa', 
        'total_home_raw_yac_wpa', 'total_away_raw_yac_wpa',
        
        # Play outcomes
        'punt_blocked', 'first_down_rush', 'first_down_pass', 'first_down_penalty', 
        'third_down_converted', 'third_down_failed', 'fourth_down_converted', 
        'fourth_down_failed', 'incomplete_pass', 'touchback', 'interception', 
        'punt_inside_twenty', 'punt_in_endzone', 'punt_out_of_bounds', 
        'punt_downed', 'punt_fair_catch', 'kickoff_inside_twenty', 'kickoff_in_endzone', 
        'kickoff_out_of_bounds', 'kickoff_downed', 'kickoff_fair_catch',
        
        # Defensive plays
        'fumble_forced', 'fumble_not_forced', 'fumble_out_of_bounds', 'solo_tackle', 
        'safety', 'penalty', 'tackled_for_loss', 'fumble_lost', 'own_kickoff_recovery', 
        'own_kickoff_recovery_td', 'qb_hit', 'sack', 'fumble', 'assist_tackle',
        
        # Play types
        'rush_attempt', 'pass_attempt', 'extra_point_attempt', 'two_point_attempt', 
        'field_goal_attempt', 'kickoff_attempt', 'punt_attempt', 'complete_pass',
        
        # Players
        'passer_player_id', 'passer_player_name', 'receiver_player_id', 
        'receiver_player_name', 'rusher_player_id', 'rusher_player_name',
        'punter_player_id', 'punter_player_name', 'kicker_player_name', 'kicker_player_id',
        
        # Returns and laterals
        'lateral_reception', 'lateral_rush', 'lateral_return', 'lateral_recovery', 
        'punt_returner_player_id', 'punt_returner_player_name', 
        'kickoff_returner_player_name', 'kickoff_returner_player_id', 
        'return_yards',
        
        # Penalties
        'penalty_team', 'penalty_player_id', 'penalty_player_name', 'penalty_yards', 
        'replay_or_challenge', 'replay_or_challenge_result', 'penalty_type',
        
        # Special situations
        'defensive_two_point_attempt', 'defensive_two_point_conv', 
        'defensive_extra_point_attempt', 'defensive_extra_point_conv', 
        'safety_player_name', 'safety_player_id',
        
        # Drive information
        'drive_real_start_time', 'drive_play_count', 'drive_time_of_possession', 
        'drive_first_downs', 'drive_inside20', 'drive_ended_with_score', 
        'drive_quarter_start', 'drive_quarter_end', 'drive_yards_penalized', 
        'drive_start_transition', 'drive_end_transition', 'drive_game_clock_start', 
        'drive_game_clock_end', 'drive_start_yard_line', 'drive_end_yard_line', 
        'drive_play_id_started', 'drive_play_id_ended', 'fixed_drive', 'fixed_drive_result',
        
        # Series and play tracking
        'series', 'series_success', 'series_result', 'order_sequence', 'play_id', 
        'nfl_api_id', 'play_clock', 'play_deleted', 'play_type_nfl', 
        'special_teams_play', 'st_play_type',
        
        # Game context
        'time_of_day', 'stadium', 'weather', 'home_opening_kickoff', 'success', 
        'passer', 'passer_jersey_number', 'rusher', 'rusher_jersey_number', 
        'receiver', 'receiver_jersey_number', 'pass', 'rush', 'first_down', 
        'aborted_play',
        
        # Calculated fields that some queries use
        'receiving_yards', 'passing_yards', 'rushing_yards'
    ]
    
    def __init__(self):
        # Cache for NFL data with TTL and size limits
        self._cache = SimpleCache(
            default_ttl=1800,   # 30 minutes default TTL
            max_size=3          # Maximum cached seasons
        )
        
        logger.debug("Initialized UnifiedNFLRepository with caching")
    
    def get_play_by_play_data(self, season: int, progress_callback=None) -> Tuple[Optional[pd.DataFrame], Optional[pd.Timestamp]]:
        """Load play-by-play data for a given season with caching."""
        try:
            if progress_callback:
                progress_callback.update(0.1, f"Checking for {season} data...")
            
            cache_key = f"pbp_{season}"
            
            def fetch_nfl_data():
                """Fetch NFL play-by-play data from API."""
                if progress_callback:
                    progress_callback.update(0.3, f"Downloading {season} NFL data...")
                
                logger.info(f"Fetching fresh data for season {season} from NFL API")
                
                # Use background thread for download with progress updates
                import threading
                
                download_complete = threading.Event()
                nfl_data = None
                download_error = None
                
                def download_data():
                    nonlocal nfl_data, download_error
                    try:
                        # Use essential columns for faster loading
                        # Fall back to full column set if essential columns fail
                        try:
                            nfl_data = nfl.import_pbp_data([season], columns=self.NEEDED_COLUMNS_ESSENTIAL)
                        except Exception as e:
                            logger.warning(f"Failed with essential columns, using full set: {e}")
                            nfl_data = nfl.import_pbp_data([season], columns=self.NEEDED_COLUMNS)
                    except Exception as e:
                        download_error = e
                    finally:
                        download_complete.set()
                
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
                
                # Get the latest game date from the actual data (represents when NFL data was last updated)
                if 'game_date' in nfl_data.columns:
                    # Find the most recent game date in the data
                    latest_game_date = pd.to_datetime(nfl_data['game_date']).max()
                    timestamp = latest_game_date
                else:
                    # Fallback to current time if game_date column is not available
                    timestamp = pd.Timestamp.now()
                    
                if progress_callback:
                    progress_callback.update(0.9, f"Processing {season} data...")
                
                logger.info(f"Successfully fetched {len(nfl_data)} plays for season {season}, latest game: {timestamp}")
                return (nfl_data, timestamp)
            
            def validate_data(data_tuple):
                """Validate cached play-by-play data."""
                if not isinstance(data_tuple, tuple) or len(data_tuple) != 2:
                    return False
                data, timestamp = data_tuple
                return (data is not None and len(data) > 0 and 
                       'season' in data.columns and timestamp is not None)
            
            # Set TTL for cache entries
            ttl = 1800  # 30 minutes
            
            result = self._cache.get_or_compute(
                key=cache_key,
                compute_func=fetch_nfl_data,
                validator=validate_data,
                ttl=ttl
            )
            
            if progress_callback:
                progress_callback.update(1.0, f"Loaded {season} data")
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading NFL data for season {season}: {e}")
            raise DataAccessError(f"Failed to load {season} data: {str(e)}")
    
    def get_team_data(self, pbp_data: pd.DataFrame, team_abbreviation: str, 
                     configuration: Optional[Dict] = None) -> pd.DataFrame:
        """Filter play-by-play data for a specific team."""
        try:
            if pbp_data is None or len(pbp_data) == 0:
                return pd.DataFrame()
            
            # Filter for team's offensive plays
            team_data = pbp_data[
                (pbp_data['posteam'] == team_abbreviation) & 
                (pbp_data['play_type'].isin(['pass', 'run']))
            ].copy()
            
            # Apply configuration if provided
            if configuration:
                team_data = apply_configuration_to_data(team_data, configuration)
            
            return team_data
        except Exception as e:
            logger.error(f"Error filtering team data for {team_abbreviation}: {e}")
            return pd.DataFrame()
    
    def refresh_season_data(self, season: int, progress_callback=None, force: bool = False) -> bool:
        """Refresh cached season data."""
        try:
            cache_key = f"pbp_{season}"
            if force:
                # Clear existing cache entry
                self._cache.invalidate(cache_key)
                logger.info(f"Forcefully cleared cache for season {season}")
            
            # Re-fetch data
            data, _ = self.get_play_by_play_data(season, progress_callback)
            return data is not None
        except Exception as e:
            logger.error(f"Error refreshing season {season} data: {e}")
            return False

    def get_league_aggregates(self, season: int, season_type: Optional[str] = None) -> Optional[pd.DataFrame]:
        """This repository requires calculation - no aggregates available."""
        # season_type parameter not used - this repository doesn't support pre-aggregated data
        return None

    def supports_aggregated_data(self) -> bool:
        """Whether this repository provides pre-aggregated statistics."""
        return False

    def requires_calculation(self) -> bool:
        """Whether this repository requires calculation from raw play-by-play data."""
        return True

    def get_data_source_name(self) -> str:
        """Get the name of this data source."""
        return "nfl_data_py"

    def get_data_timestamp(self, season: int) -> Optional[datetime]:
        """Get the timestamp of when season data was last updated."""
        cache_key = f"pbp_{season}"
        cached_data = self._cache.get(cache_key)
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