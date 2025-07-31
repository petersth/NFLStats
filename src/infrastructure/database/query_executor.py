# src/infrastructure/database/query_executor.py

import logging
from typing import Dict, List, Optional, Any
import requests

from ...domain.interfaces.database import (
    DatabaseConnectionInterface, DatabaseError
)
from .supabase_base import SupabaseConnectionBase

logger = logging.getLogger(__name__)


class SupabaseConnection(DatabaseConnectionInterface, SupabaseConnectionBase):
    """Supabase connection wrapper."""
    
    def __init__(self, url: str, key: str):
        SupabaseConnectionBase.__init__(self, url, key)
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to Supabase (validate credentials)."""
        self._connected = bool(self.url and self.key)
        return self._connected
    
    def disconnect(self) -> None:
        """Disconnect from Supabase."""
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information (delegates to base class)."""
        return SupabaseConnectionBase.get_connection_info(self)
    
    def test_connection(self) -> bool:
        """Test database connectivity (delegates to base class)."""
        return SupabaseConnectionBase.test_connection(self)


class SupabaseQueryExecutor:
    """Supabase-specific query executor for raw play data."""
    
    def __init__(self, connection: DatabaseConnectionInterface):
        self._connection = connection
        self._in_transaction = False
        self._transaction_operations = []
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute a SELECT query using Supabase REST API."""
        if not self._connection.is_connected():
            raise DatabaseError("Database connection not available")
        
        try:
            return self._execute_rest_query(query, params)
        except requests.RequestException as e:
            logger.error(f"Query execution failed: {e}")
            raise DatabaseError(f"Query execution failed: {e}")
    
    def execute_command(self, command: str, params: Optional[Dict] = None) -> int:
        """Execute INSERT/UPDATE/DELETE using Supabase REST API."""
        if not self._connection.is_connected():
            raise DatabaseError("Database connection not available")
        
        try:
            if self._in_transaction:
                self._transaction_operations.append(('command', command, params))
                return 1  # Assume success for now
            
            return self._execute_rest_command(command, params)
        except requests.RequestException as e:
            logger.error(f"Command execution failed: {e}")
            raise DatabaseError(f"Command execution failed: {e}")
    
    def execute_script(self, script: str) -> None:
        """Execute a SQL script (multiple statements)."""
        if not self._connection.is_connected():
            raise DatabaseError("Database connection not available")
        
        # Split script into individual statements
        statements = [stmt.strip() for stmt in script.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement.upper().startswith('SELECT'):
                self.execute_query(statement)
            else:
                self.execute_command(statement)
    
    def begin_transaction(self, isolation_level: str = "READ_COMMITTED") -> None:
        """Begin a database transaction."""
        if self._in_transaction:
            raise DatabaseError("Transaction already in progress")
        
        self._in_transaction = True
        self._transaction_operations = []
        logger.debug(f"Transaction started with isolation level: {isolation_level.value}")
    
    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        if not self._in_transaction:
            raise DatabaseError("No transaction in progress")
        
        try:
            # Execute all queued operations
            for op_type, statement, params in self._transaction_operations:
                if op_type == 'query':
                    self.execute_query(statement, params)
                elif op_type == 'command':
                    self._execute_rest_command(statement, params)
            
            self._in_transaction = False
            self._transaction_operations = []
            logger.debug("Transaction committed successfully")
        except Exception as e:
            self.rollback_transaction()
            raise DatabaseError(f"Transaction commit failed: {e}")
    
    def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        if not self._in_transaction:
            raise DatabaseError("No transaction in progress")
        
        self._in_transaction = False
        self._transaction_operations = []
        logger.debug("Transaction rolled back")
    
    def _execute_rest_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute query using Supabase REST API."""
        connection_info = self._connection.get_connection_info()
        base_url = connection_info.get('url')
        headers = connection_info.get('headers', {})
        
        if 'FROM raw_play_data' in query:
            return self._handle_raw_play_data_query(query, params, base_url, headers)
        elif 'FROM team_season_aggregates' in query:
            return self._handle_aggregated_view_query(query, params, base_url, headers, 'team_season_aggregates')
        elif 'FROM team_season_stats_complete' in query:
            return self._handle_aggregated_view_query(query, params, base_url, headers, 'team_season_stats_complete')
        elif 'FROM team_game_aggregates' in query:
            return self._handle_aggregated_view_query(query, params, base_url, headers, 'team_game_aggregates')
        elif 'FROM aggregate_refresh_log' in query:
            return self._handle_simple_table_query(query, params, base_url, headers, 'aggregate_refresh_log')
        elif 'SELECT COUNT(*)' in query:
            return self._handle_count_query(query, params, base_url, headers)
        elif 'DISTINCT posteam' in query and 'FROM raw_play_data' in query:
            return self._handle_distinct_teams_query(query, params, base_url, headers)
        else:
            logger.warning(f"Unsupported query pattern: {query}")
            return []
    
    def _execute_rest_command(self, command: str, params: Optional[Dict] = None) -> int:
        """Execute command using Supabase REST API."""
        connection_info = self._connection.get_connection_info()
        base_url = connection_info.get('url')
        headers = connection_info.get('headers', {})
        
        if 'INSERT INTO raw_play_data' in command:
            return self._handle_raw_play_data_insert(command, params, base_url, headers)
        elif command.startswith('UPDATE raw_play_data'):
            return self._handle_raw_play_data_update(command, params, base_url, headers)
        elif command.startswith('DELETE FROM raw_play_data'):
            return self._handle_raw_play_data_delete(command, params, base_url, headers)
        elif 'REFRESH MATERIALIZED VIEW' in command:
            # Materialized view refresh - needs to be done via SQL editor
            logger.warning(f"Materialized view refresh not supported via REST API: {command}")
            logger.info("Please refresh materialized views manually in Supabase SQL editor")
            return 1  # Return success to continue flow
        elif 'UPDATE aggregate_refresh_log' in command:
            return self._handle_refresh_log_update(command, params, base_url, headers)
        elif 'CALL refresh_team_aggregates' in command:
            # Function calls need SQL editor
            logger.warning("Function calls not supported via REST API")
            return 1
        elif 'CREATE TABLE' in command or 'CREATE INDEX' in command:
            logger.info(f"Schema command: {command[:100]}... (handled by database admin)")
            return 1  # Assume success for now
        else:
            logger.warning(f"Unsupported command pattern: {command}")
            return 0
    
    def _handle_raw_play_data_query(self, query: str, params: Optional[Dict], 
                                   base_url: str, headers: Dict) -> List[Dict]:
        """Handle raw_play_data SELECT queries with pagination support."""
        url = f"{base_url}/rest/v1/raw_play_data"
        
        # Build query parameters
        query_params = {}
        if params:
            if 'season' in params:
                query_params['season'] = f"eq.{params['season']}"
            if 'season_type' in params:
                query_params['season_type'] = f"eq.{params['season_type']}"
            if 'posteam' in params:
                query_params['posteam'] = f"eq.{params['posteam']}"
        
        # Handle specific query types
        if 'nfl_data_timestamp' in query:
            # For timestamp queries, select only timestamp column and order/limit
            query_params['select'] = 'nfl_data_timestamp'
            query_params['order'] = 'nfl_data_timestamp.desc'
            query_params['limit'] = '1'
            # Filter out null timestamps
            query_params['nfl_data_timestamp'] = 'not.is.null'
            
            response = requests.get(url, headers=headers, params=query_params)
            response.raise_for_status()
            return response.json()
        elif 'SELECT COUNT(*)' in query:
            # For count queries
            query_params['select'] = 'count'
            response = requests.get(url, headers=headers, params=query_params)
            response.raise_for_status()
            return response.json()
        elif 'SELECT EXISTS(' in query:
            # For EXISTS queries - check if any records exist with the given filters
            # The REST API equivalent is to get count and check if > 0
            query_params['select'] = 'count'
            response = requests.get(url, headers=headers, params=query_params)
            response.raise_for_status()
            result = response.json()
            count = result[0]['count'] if result else 0
            return [{'exists': count > 0}]
        else:
            # For regular queries, check if we need column selection
            if 'SELECT ' in query and ' FROM raw_play_data' in query:
                # Extract column list from SQL query
                select_part = query.split('SELECT ')[1].split(' FROM')[0].strip()
                if select_part != '*':
                    # Clean up column names and create select parameter
                    columns = [col.strip() for col in select_part.split(',')]
                    query_params['select'] = ','.join(columns)
            
            # For regular queries, handle pagination to get ALL data
            return self._paginated_query(url, headers, query_params)
    
    def _paginated_query(self, url: str, headers: Dict, base_params: Dict) -> List[Dict]:
        """Execute a paginated query to retrieve all results from Supabase."""
        all_results = []
        offset = 0
        limit = 10000  # Supabase maximum limit for optimal performance
        
        logger.info("Starting paginated query to retrieve all data...")
        
        while True:
            # Build pagination parameters
            query_params = base_params.copy()
            query_params['limit'] = str(limit)
            query_params['offset'] = str(offset)
            
            # Add ordering only if appropriate columns are selected
            selected_columns = query_params.get('select', '*')
            if selected_columns == '*' or ('game_id' in selected_columns and 'play_id' in selected_columns):
                query_params['order'] = 'game_id,play_id'  # Ensure consistent ordering
            elif 'posteam' in selected_columns:
                query_params['order'] = 'posteam'  # Order by the selected column
            # For other cases, let Supabase use default ordering
            
            # Add headers to request higher limits from Supabase
            request_headers = headers.copy()
            request_headers['Range'] = f'{offset}-{offset + limit - 1}'
            request_headers['Prefer'] = 'count=exact'
            
            logger.debug(f"Fetching rows {offset} to {offset + limit - 1}")
            
            response = requests.get(url, headers=request_headers, params=query_params)
            response.raise_for_status()
            
            batch_results = response.json()
            
            if not batch_results:
                # No more results
                break
            
            all_results.extend(batch_results)
            
            # If we got fewer results than what Supabase can return in one batch (1000), we've reached the end
            # Note: Supabase limits responses to 1000 rows regardless of our limit parameter
            supabase_max_batch = 1000
            if len(batch_results) < supabase_max_batch:
                break
            
            offset += len(batch_results)  # Use actual returned batch size
            
            # Progress logging for large datasets  
            if offset % 10000 == 0:
                logger.info(f"Retrieved {len(all_results)} rows so far...")
        
        logger.info(f"Paginated query complete: retrieved {len(all_results)} total rows")
        return all_results
    
    def _handle_raw_play_data_insert(self, command: str, params: Optional[Dict], 
                                    base_url: str, headers: Dict) -> int:
        """Handle raw_play_data INSERT commands."""
        url = f"{base_url}/rest/v1/raw_play_data"
        
        if params:
            # Use upsert instead of insert to handle conflicts
            upsert_headers = headers.copy()
            upsert_headers['Prefer'] = 'resolution=merge-duplicates'
            
            # Handle both single records and arrays of records
            if isinstance(params, list):
                # Bulk insert
                response = requests.post(url, headers=upsert_headers, json=params)
                logger.info(f"Bulk inserting {len(params)} records")
            else:
                # Single record insert
                response = requests.post(url, headers=upsert_headers, json=params)
                logger.info("Inserting single record")
            
            if response.status_code not in [201, 200]:
                logger.error(f"Supabase upsert failed: {response.status_code} - {response.text}")
                if isinstance(params, list):
                    logger.error(f"Bulk insert size: {len(params)} records")
                else:
                    logger.error(f"Request data: {params}")
            response.raise_for_status()
            return len(params) if isinstance(params, list) else 1
        return 0
    
    def _handle_raw_play_data_update(self, command: str, params: Optional[Dict], 
                                    base_url: str, headers: Dict) -> int:
        """Handle raw_play_data UPDATE commands."""
        # Implementation would depend on specific update requirements
        logger.warning("Raw play data updates not implemented")
        return 0
    
    def _handle_raw_play_data_delete(self, command: str, params: Optional[Dict], 
                                    base_url: str, headers: Dict) -> int:
        """Handle raw_play_data DELETE commands."""
        url = f"{base_url}/rest/v1/raw_play_data"
        
        query_params = {}
        if params and 'season' in params:
            query_params['season'] = f"eq.{params['season']}"
        
        response = requests.delete(url, headers=headers, params=query_params)
        response.raise_for_status()
        return 1
    
    def _handle_count_query(self, query: str, params: Optional[Dict], 
                           base_url: str, headers: Dict) -> List[Dict]:
        """Handle COUNT queries."""
        url = f"{base_url}/rest/v1/raw_play_data"
        
        # Build query parameters for counting
        query_params = {'select': 'count'}
        if params:
            if 'season' in params:
                query_params['season'] = f"eq.{params['season']}"
        
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        result = response.json()
        
        # Supabase returns count as an array with count property
        if result and len(result) > 0 and 'count' in result[0]:
            return [{'count': result[0]['count']}]
        else:
            # Fallback: get all records and count manually
            all_params = {}
            if params and 'season' in params:
                all_params['season'] = f"eq.{params['season']}"
            all_params['select'] = 'game_id'  # Minimal data
            
            all_response = requests.get(url, headers=headers, params=all_params)
            all_response.raise_for_status()
            all_data = all_response.json()
            return [{'count': len(all_data)}]
    
    def _handle_distinct_teams_query(self, query: str, params: Optional[Dict], 
                                    base_url: str, headers: Dict) -> List[Dict]:
        """Handle DISTINCT posteam queries."""
        url = f"{base_url}/rest/v1/raw_play_data"
        
        # Build query parameters
        query_params = {'select': 'posteam'}
        if params:
            if 'season' in params:
                query_params['season'] = f"eq.{params['season']}"
        
        # Filter out null values
        query_params['posteam'] = 'not.is.null'
        
        # Use pagination to get all teams
        all_results = self._paginated_query(url, headers, query_params)
        
        # Get unique teams
        unique_teams = sorted(list(set([r['posteam'] for r in all_results if r.get('posteam')])))
        return [{'posteam': team} for team in unique_teams]
    
    def _handle_aggregated_view_query(self, query: str, params: Optional[Dict], 
                                     base_url: str, headers: Dict, view_name: str) -> List[Dict]:
        """Handle queries against aggregated materialized views."""
        url = f"{base_url}/rest/v1/{view_name}"
        
        # Build query parameters
        query_params = {}
        if params:
            if 'season' in params:
                query_params['season'] = f"eq.{params['season']}"
            if 'season_type' in params:
                query_params['season_type'] = f"eq.{params['season_type']}"
            if 'posteam' in params:
                query_params['posteam'] = f"eq.{params['posteam']}"
        
        # Add ordering if specified
        if 'ORDER BY' in query:
            query_params['order'] = 'posteam'  # Default ordering
        
        # Handle COUNT queries
        if 'COUNT(*)' in query:
            query_params['select'] = 'count'
        
        response = requests.get(url, headers=headers, params=query_params)
        
        if response.status_code == 404:
            # View doesn't exist yet
            logger.warning(f"Aggregated view {view_name} not found. Needs to be created.")
            return []
        
        response.raise_for_status()
        return response.json()
    
    def _handle_simple_table_query(self, query: str, params: Optional[Dict], 
                                  base_url: str, headers: Dict, table_name: str) -> List[Dict]:
        """Handle queries against simple tables like aggregate_refresh_log."""
        url = f"{base_url}/rest/v1/{table_name}"
        
        query_params = {}
        
        # Handle MIN/MAX aggregations
        if 'MIN(last_refresh)' in query:
            query_params['select'] = 'last_refresh'
            query_params['order'] = 'last_refresh'
            query_params['limit'] = '1'
            
            response = requests.get(url, headers=headers, params=query_params)
            response.raise_for_status()
            result = response.json()
            
            if result and len(result) > 0:
                return [{'oldest_refresh': result[0]['last_refresh']}]
            return [{'oldest_refresh': None}]
        
        # Default: return all records
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        return response.json()
    
    def _handle_refresh_log_update(self, command: str, params: Optional[Dict], 
                                  base_url: str, headers: Dict) -> int:
        """Handle updates to aggregate_refresh_log table."""
        url = f"{base_url}/rest/v1/aggregate_refresh_log"
        
        # Update specific rows
        update_data = {'last_refresh': 'now()'}
        update_params = {
            'view_name': 'in.(team_game_aggregates,team_season_aggregates)'
        }
        
        response = requests.patch(url, headers=headers, json=update_data, params=update_params)
        
        if response.status_code == 404:
            logger.warning("aggregate_refresh_log table not found")
            return 0
        
        response.raise_for_status()
        return 1