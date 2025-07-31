# src/infrastructure/data/unified_nfl_repository.py - Unified NFL data repository

import logging
from typing import Optional, Tuple, Dict, Protocol
import pandas as pd
import nfl_data_py as nfl
from datetime import datetime, timedelta

from ...domain.interfaces.repository import DataRepositoryInterface
from ...domain.exceptions import DataAccessError, DataNotFoundError
from ...domain.services import ConfigurationService
from ..database.query_executor import SupabaseQueryExecutor

logger = logging.getLogger(__name__)


class DataStorageStrategy(Protocol):
    """Protocol for data storage strategies."""
    
    def store_data(self, data: pd.DataFrame, season: int, timestamp: datetime, 
                   progress_callback=None) -> bool:
        """Store play-by-play data."""
        ...
    
    def retrieve_data(self, season: int) -> Tuple[Optional[pd.DataFrame], Optional[datetime]]:
        """Retrieve play-by-play data and its timestamp."""
        ...
    
    def check_freshness(self, season: int) -> bool:
        """Check if stored data is fresh."""
        ...
    
    def get_aggregates(self, season: int, season_type: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get pre-aggregated data if available."""
        ...


class DatabaseStrategy:
    """Database storage strategy using Supabase."""
    
    def __init__(self, query_executor: SupabaseQueryExecutor, aggregated_repo=None):
        self._query_executor = query_executor
        self._aggregated_repo = aggregated_repo
    
    def store_data(self, data: pd.DataFrame, season: int, timestamp: datetime, 
                   progress_callback=None) -> bool:
        """Store data in database."""
        try:
            if progress_callback:
                progress_callback.update(0.1, f"Preparing {len(data)} plays for storage...")
            
            # Clear existing season data
            if progress_callback:
                progress_callback.update(0.2, f"Clearing existing {season} data...")
            
            clear_query = """
                DELETE FROM raw_play_data 
                WHERE season = %(season)s
            """
            self._query_executor.execute_command(clear_query, {'season': season})
            
            # Prepare data for insertion
            data_copy = data.copy()
            data_copy['nfl_data_timestamp'] = timestamp
            
            # Insert in batches
            batch_size = 5000
            total_rows = len(data_copy)
            
            for i in range(0, total_rows, batch_size):
                if progress_callback:
                    progress = 0.3 + (0.5 * i / total_rows)
                    progress_callback.update(progress, f"Storing batch {i//batch_size + 1}...")
                
                batch = data_copy.iloc[i:i + batch_size]
                self._insert_batch(batch)
            
            logger.info(f"Successfully stored {total_rows} plays for season {season}")
            
            # Try to refresh aggregates
            try:
                if self._aggregated_repo:
                    self._aggregated_repo.refresh_aggregates(season)
            except Exception as e:
                logger.warning(f"Could not refresh aggregates: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store data: {e}")
            return False
    
    def _insert_batch(self, batch_data: pd.DataFrame) -> None:
        """Insert a batch of play data."""
        if len(batch_data) == 0:
            return
        
        # Convert DataFrame to list of dicts
        records = batch_data.to_dict('records')
        
        # Build INSERT query
        columns = list(batch_data.columns)
        placeholders = ', '.join([f'%({col})s' for col in columns])
        
        insert_query = f"""
            INSERT INTO raw_play_data ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (game_id, play_id) DO UPDATE SET
                {', '.join([f'{col} = EXCLUDED.{col}' for col in columns if col not in ['game_id', 'play_id']])}
        """
        
        # Clean records for insertion
        cleaned_records = []
        for record in records:
            cleaned_record = {}
            for key, value in record.items():
                if pd.isna(value):
                    cleaned_record[key] = None
                elif hasattr(value, 'item'):  # numpy scalar
                    cleaned_record[key] = value.item()
                elif isinstance(value, pd.Timestamp):
                    cleaned_record[key] = value.isoformat()
                else:
                    cleaned_record[key] = value
            cleaned_records.append(cleaned_record)
        
        # Execute batch insert
        self._query_executor.execute_command(insert_query, cleaned_records)
    
    def retrieve_data(self, season: int) -> Tuple[Optional[pd.DataFrame], Optional[datetime]]:
        """Retrieve data from database using the same approach as RawPlayDataRepository."""
        try:
            # Check if season exists first
            check_query = """
                SELECT EXISTS(SELECT 1 FROM raw_play_data WHERE season = %(season)s LIMIT 1) as exists
            """
            result = self._query_executor.execute_query(check_query, {'season': season})
            
            if not result or not result[0]['exists']:
                return None, None
            
            # Use targeted column selection like the original RawPlayDataRepository
            columns = [
                'game_id', 'posteam', 'season_type', 'game_date', 'home_team', 'away_team', 'defteam', 'week',
                'play_type', 'down', 'ydstogo', 'yards_gained', 'drive', 'yardline_100',
                'posteam_score_post', 'defteam_score_post',
                'rush_attempt', 'pass_attempt', 'sack', 'touchdown', 'first_down',
                'interception', 'fumble', 'fumble_lost', 'penalty', 'penalty_team', 'penalty_yards',
                'first_down_rush', 'first_down_pass', 'first_down_penalty',
                'complete_pass', 'incomplete_pass', 'pass_touchdown', 'rush_touchdown',
                'two_point_attempt', 'two_point_conv_result', 'extra_point_result', 'field_goal_result',
                'passing_yards', 'rushing_yards', 'receiving_yards', 'td_team', 'success', 'epa', 'qb_kneel'
            ]
            
            # Build query with specific columns
            data_query = f"SELECT {', '.join(columns)} FROM raw_play_data WHERE season = %(season)s ORDER BY game_id, play_id"
            data_result = self._query_executor.execute_query(data_query, {'season': season})
            
            # Convert to DataFrame
            if data_result:
                data = pd.DataFrame(data_result)
            else:
                return None, None
            
            # Get timestamp
            timestamp_query = """
                SELECT DISTINCT nfl_data_timestamp 
                FROM raw_play_data 
                WHERE season = %(season)s 
                LIMIT 1
            """
            timestamp_result = self._query_executor.execute_query(timestamp_query, {'season': season})
            timestamp = timestamp_result[0]['nfl_data_timestamp'] if timestamp_result else None
            
            return data, timestamp
            
        except Exception as e:
            logger.error(f"Failed to retrieve data: {e}")
            return None, None
    
    def check_freshness(self, season: int) -> bool:
        """Check if database data is fresh."""
        try:
            _, timestamp = self.retrieve_data(season)
            if not timestamp:
                return False
            
            # Convert string timestamp if needed
            if isinstance(timestamp, str):
                from dateutil.parser import parse
                timestamp = parse(timestamp)
            
            now = datetime.now()
            current_year = now.year
            
            # Completed seasons are always fresh
            if season < current_year:
                return True
            
            # Current season: check if within 24 hours
            if timestamp.tzinfo and not now.tzinfo:
                now = now.replace(tzinfo=timestamp.tzinfo)
            elif now.tzinfo and not timestamp.tzinfo:
                timestamp = timestamp.replace(tzinfo=now.tzinfo)
            
            return (now - timestamp) < timedelta(hours=24)
            
        except Exception as e:
            logger.error(f"Failed to check freshness: {e}")
            return False
    
    def get_aggregates(self, season: int, season_type: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get pre-aggregated data if available."""
        if not self._aggregated_repo:
            return None
        
        try:
            return self._aggregated_repo.get_all_teams_season_stats(season, season_type)
        except Exception as e:
            logger.warning(f"Failed to get aggregates: {e}")
            return None


class InMemoryStrategy:
    """In-memory caching strategy for direct NFL API access."""
    
    def __init__(self):
        self._cache = {}
    
    def store_data(self, data: pd.DataFrame, season: int, timestamp: datetime, 
                   progress_callback=None) -> bool:
        """Store data in memory cache."""
        cache_key = f"pbp_{season}"
        self._cache[cache_key] = (data, timestamp)
        return True
    
    def retrieve_data(self, season: int) -> Tuple[Optional[pd.DataFrame], Optional[datetime]]:
        """Retrieve data from memory cache."""
        cache_key = f"pbp_{season}"
        return self._cache.get(cache_key, (None, None))
    
    def check_freshness(self, season: int) -> bool:
        """In-memory cache is always considered stale to ensure fresh data."""
        return False
    
    def get_aggregates(self, season: int, season_type: Optional[str] = None) -> Optional[pd.DataFrame]:
        """In-memory strategy doesn't support aggregates."""
        return None


class UnifiedNFLRepository(DataRepositoryInterface):
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
    
    def __init__(self, config_service: ConfigurationService, storage_strategy: DataStorageStrategy):
        self._config_service = config_service
        self._storage = storage_strategy
    
    def get_play_by_play_data(self, season: int, progress_callback=None) -> Tuple[Optional[pd.DataFrame], Optional[pd.Timestamp]]:
        """Load play-by-play data for a given season."""
        try:
            if progress_callback:
                progress_callback.update(0.1, f"Checking for {season} data...")
            
            # Try to get from storage
            data, timestamp = self._storage.retrieve_data(season)
            
            # Check if we need to refresh
            if data is not None and self._storage.check_freshness(season):
                if progress_callback:
                    progress_callback.update(0.9, f"Using cached {season} data...")
                logger.info(f"Using cached data for season {season}")
                pd_timestamp = pd.Timestamp(timestamp) if timestamp else None
                return data, pd_timestamp
            
            # If no data found, we need to fetch it (both strategies)
            if progress_callback:
                progress_callback.update(0.3, f"Downloading {season} NFL data...")
            
            logger.info(f"Fetching fresh data for season {season} from NFL API")
            nfl_data = nfl.import_pbp_data([season], columns=self.NEEDED_COLUMNS)
            
            if nfl_data is None or len(nfl_data) == 0:
                logger.error(f"No NFL data available for season {season}")
                return None, None
            
            # Get timestamp from latest game
            latest_game = pd.to_datetime(nfl_data['game_date']).max()
            timestamp = latest_game.to_pydatetime() if latest_game else datetime.now()
            
            if progress_callback:
                progress_callback.update(0.6, f"Storing {len(nfl_data)} plays...")
            
            # Store the data
            self._storage.store_data(nfl_data, season, timestamp, progress_callback)
            
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
            team_data = self._config_service.apply_configuration_to_data(team_data, configuration)
        
        return team_data
    
    def refresh_season_data(self, season: int, progress_callback=None, force: bool = False) -> bool:
        """Refresh data for a season."""
        try:
            # For in-memory strategy, just clear cache
            if isinstance(self._storage, InMemoryStrategy):
                cache_key = f"pbp_{season}"
                if hasattr(self._storage, '_cache') and cache_key in self._storage._cache:
                    del self._storage._cache[cache_key]
                return True
            
            # For database strategy, re-fetch if not fresh or forced
            if not force and self._storage.check_freshness(season):
                logger.info(f"Data for season {season} is already fresh")
                return True
            
            # Force re-fetch by temporarily clearing
            data, timestamp = self.get_play_by_play_data(season, progress_callback)
            return data is not None
            
        except Exception as e:
            logger.error(f"Failed to refresh season data: {e}")
            return False
    
    def get_league_aggregates(self, season: int, season_type: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get pre-calculated league aggregates if available."""
        return self._storage.get_aggregates(season, season_type)
    
    def supports_aggregated_data(self) -> bool:
        """Whether this repository can provide pre-aggregated data."""
        return isinstance(self._storage, DatabaseStrategy) and self._storage._aggregated_repo is not None
    
    def requires_calculation(self) -> bool:
        """Whether this repository requires calculation of statistics."""
        return True  # Always true for raw data
    
    def get_data_source_name(self) -> str:
        """Human-readable name of this data source."""
        if isinstance(self._storage, DatabaseStrategy):
            return "NFL Data (Database-backed)"
        else:
            return "NFL Data (Direct API)"
    
    def get_data_timestamp(self, season: int) -> Optional[datetime]:
        """Get the timestamp for when data was last updated for a season."""
        _, timestamp = self._storage.retrieve_data(season)
        return timestamp