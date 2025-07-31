# src/infrastructure/database/repositories/aggregated_stats_repository.py

import logging
from typing import Optional
import pandas as pd
from datetime import datetime

from ..query_executor import SupabaseQueryExecutor

logger = logging.getLogger(__name__)


class AggregatedStatsRepository:
    """Repository using pre-aggregated database views."""
    
    def __init__(self, query_executor: SupabaseQueryExecutor):
        self._query_executor = query_executor
    
    def _build_filter_params(self, season: int, season_type: Optional[str] = None, team: Optional[str] = None) -> dict:
        """Build standardized query parameters for filtering."""
        params = {'season': season}
        if season_type and season_type != 'ALL':
            params['season_type'] = season_type
        if team:
            params['team'] = team
        return params
    
    def _add_season_type_filter(self, query: str, season_type: Optional[str]) -> str:
        """Add season type filter to query if needed."""
        if season_type and season_type != 'ALL':
            return query + " AND season_type = %(season_type)s"
        return query
    
    def _execute_query_safely(self, query: str, params: dict, operation: str) -> pd.DataFrame:
        """Execute query with consistent error handling and logging."""
        try:
            result = self._query_executor.execute_query(query, params)
            
            if not result:
                logger.info(f"No data found for {operation}")
                return pd.DataFrame()
            
            logger.info(f"Retrieved {len(result)} records for {operation}")
            return pd.DataFrame(result)
            
        except Exception as e:
            logger.error(f"Failed to {operation}: {e}")
            return pd.DataFrame()
    
    def get_all_teams_season_stats(self, season: int, season_type: Optional[str] = None) -> pd.DataFrame:
        """
        Get pre-aggregated season stats for all teams in one ultra-fast query.
        This replaces the 11-second raw data fetch with a <1 second query.
        """
        # Build query using utilities - use team_season_stats_complete which has proper play filtering
        query = "SELECT * FROM team_season_stats_complete WHERE season = %(season)s"
        query = self._add_season_type_filter(query, season_type)
        query += " ORDER BY posteam"
        
        params = self._build_filter_params(season, season_type)
        operation = f"aggregated season stats for season {season}"
        
        return self._execute_query_safely(query, params, operation)
    
    def check_aggregates_exist(self, season: int) -> bool:
        """Check if aggregated data exists for a season."""
        try:
            query = """
                SELECT COUNT(*) as count 
                FROM team_season_aggregates 
                WHERE season = %(season)s
            """
            result = self._query_executor.execute_query(query, {'season': season})
            return result[0]['count'] > 0 if result else False
            
        except Exception as e:
            logger.error(f"Failed to check aggregate existence: {e}")
            return False
    
    def refresh_aggregates(self, season: int) -> bool:
        """Refresh the materialized views for a season."""
        try:
            logger.info(f"Attempting to refresh aggregated views for season {season}")
            
            # Try to call the refresh function if it exists
            try:
                query = "SELECT * FROM refresh_season_aggregates(%(season)s)"
                result = self._query_executor.execute_query(query, {'season': season})
                
                if result and len(result) > 0:
                    views_refreshed = result[0].get('views_refreshed', 0)
                    message = result[0].get('message', 'Unknown result')
                    
                    if views_refreshed > 0:
                        logger.info(f"Successfully refreshed {views_refreshed} aggregated views: {message}")
                        self._update_refresh_log_safely()
                        return True
                    else:
                        logger.warning(f"No views refreshed: {message}")
                        return False
                        
            except Exception as e:
                logger.warning(f"Could not call refresh function (may not exist yet): {e}")
                
            # Fallback: Check if we have any aggregated data for this season
            season_data = self.get_all_teams_season_stats(season)
            
            if len(season_data) > 0:
                logger.info(f"Found {len(season_data)} teams in aggregated data for season {season}")
                self._update_refresh_log_safely()
                return True
            else:
                logger.warning(f"No aggregated data found for season {season}")
                logger.info("Note: Materialized views may need manual refresh in Supabase SQL editor:")
                logger.info("  REFRESH MATERIALIZED VIEW team_game_aggregates;")
                logger.info("  REFRESH MATERIALIZED VIEW team_season_aggregates;")
                return False
            
        except Exception as e:
            logger.error(f"Failed to refresh aggregates for season {season}: {e}")
            return False
    
    def _update_refresh_log_safely(self) -> bool:
        """Update refresh log if table exists."""
        try:
            # First check if table exists by attempting a simple query
            self._query_executor.execute_query("SELECT COUNT(*) FROM aggregate_refresh_log LIMIT 1", {})
            
            # Table exists, update it
            update_log_query = """
                UPDATE aggregate_refresh_log 
                SET last_refresh = NOW() 
                WHERE view_name IN ('team_game_aggregates', 'team_season_aggregates')
            """
            self._query_executor.execute_command(update_log_query, {})
            logger.debug("Updated refresh log successfully")
            return True
            
        except Exception:
            logger.debug("aggregate_refresh_log table not found, skipping refresh log update")
            return False
    
    def get_aggregate_freshness(self) -> Optional[datetime]:
        """Get when aggregates were last refreshed."""
        try:
            # Check if refresh log table exists first
            self._query_executor.execute_query("SELECT COUNT(*) FROM aggregate_refresh_log LIMIT 1", {})
            
            # Table exists, query it
            query = "SELECT MIN(last_refresh) as oldest_refresh FROM aggregate_refresh_log"
            result = self._query_executor.execute_query(query, {})
            
            if result and result[0]['oldest_refresh']:
                return result[0]['oldest_refresh']
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not get aggregate freshness (table may not exist): {e}")
            return None
    
    def get_team_game_details(self, season: int, team: str, season_type: Optional[str] = None) -> pd.DataFrame:
        """Get game-by-game aggregated data for a specific team.
        
        Note: team_game_aggregates view doesn't have season_type column since games are complete units.
        Season type filtering would need to be done at the application level if needed.
        """
        query = "SELECT * FROM team_game_aggregates WHERE season = %(season)s AND posteam = %(posteam)s"
        query += " ORDER BY game_id"
        
        # Don't add season_type filter since team_game_aggregates doesn't have that column
        params = {'season': season, 'posteam': team}
        operation = f"game details for team {team} in season {season}"
        
        return self._execute_query_safely(query, params, operation)
    
    # NEW: Data source capability methods
    def requires_calculation(self) -> bool:
        """Aggregated data doesn't need calculation."""
        return False
    
    def get_data_source_name(self) -> str:
        """Human-readable name of this data source."""
        return "Database Materialized Views"
    
    def supports_aggregated_data(self) -> bool:
        """This repository only provides aggregated data."""
        return True