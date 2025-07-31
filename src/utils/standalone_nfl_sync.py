#!/usr/bin/env python3
"""
Standalone NFL Data Synchronization Utility

This utility compares NFL play-by-play data from the nfl_data_py library 
with data stored in the Supabase database and updates when missing data is found.
This version is completely standalone and doesn't rely on the main codebase imports.
"""

import logging
import pandas as pd
import nfl_data_py as nfl
import requests
from datetime import datetime
from typing import Optional, Dict, List
import argparse

logger = logging.getLogger(__name__)


class SimpleSupabaseClient:
    """Simple Supabase client for NFL data operations."""
    
    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.key = key
        self.headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def get_season_play_count(self, season: int) -> int:
        """Get count of plays in database for a season."""
        try:
            url = f"{self.url}/rest/v1/raw_play_data"
            params = {
                'season': f'eq.{season}',
                'select': 'count'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            return result[0]['count'] if result and 'count' in result[0] else 0
            
        except Exception as e:
            logger.error(f"Failed to get play count: {e}")
            return 0
    
    def get_season_games(self, season: int) -> set:
        """Get set of game IDs in database for a season."""
        try:
            url = f"{self.url}/rest/v1/raw_play_data"
            params = {
                'season': f'eq.{season}',
                'select': 'game_id'
            }
            
            all_games = []
            offset = 0
            limit = 1000
            
            while True:
                query_params = params.copy()
                query_params['limit'] = str(limit)
                query_params['offset'] = str(offset)
                
                response = requests.get(url, headers=self.headers, params=query_params)
                response.raise_for_status()
                
                batch = response.json()
                if not batch:
                    break
                
                all_games.extend([row['game_id'] for row in batch if 'game_id' in row])
                
                if len(batch) < limit:
                    break
                
                offset += limit
            
            return set(all_games)
            
        except Exception as e:
            logger.error(f"Failed to get games: {e}")
            return set()
    
    def get_season_teams(self, season: int) -> set:
        """Get set of teams in database for a season."""
        try:
            url = f"{self.url}/rest/v1/raw_play_data"
            params = {
                'season': f'eq.{season}',
                'select': 'posteam',
                'posteam': 'not.is.null'
            }
            
            all_teams = []
            offset = 0
            limit = 1000
            
            while True:
                query_params = params.copy()
                query_params['limit'] = str(limit)
                query_params['offset'] = str(offset)
                
                response = requests.get(url, headers=self.headers, params=query_params)
                response.raise_for_status()
                
                batch = response.json()
                if not batch:
                    break
                
                all_teams.extend([row['posteam'] for row in batch if 'posteam' in row])
                
                if len(batch) < limit:
                    break
                
                offset += limit
            
            return set(all_teams)
            
        except Exception as e:
            logger.error(f"Failed to get teams: {e}")
            return set()
    
    def delete_season_data(self, season: int) -> bool:
        """Delete existing data for a season."""
        try:
            url = f"{self.url}/rest/v1/raw_play_data"
            params = {'season': f'eq.{season}'}
            
            response = requests.delete(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            logger.info(f"Deleted existing data for season {season}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete season data: {e}")
            return False
    
    def insert_play_data(self, data: List[Dict]) -> bool:
        """Insert play data in batches."""
        try:
            url = f"{self.url}/rest/v1/raw_play_data"
            
            # Use upsert to handle conflicts
            upsert_headers = self.headers.copy()
            upsert_headers['Prefer'] = 'resolution=merge-duplicates'
            
            batch_size = 200
            total_rows = len(data)
            
            for i in range(0, total_rows, batch_size):
                batch = data[i:i + batch_size]
                
                response = requests.post(url, headers=upsert_headers, json=batch)
                
                if response.status_code not in [200, 201]:
                    logger.error(f"Batch insert failed: {response.status_code} - {response.text}")
                    return False
                
                logger.info(f"Inserted batch {i//batch_size + 1}/{(total_rows//batch_size) + 1}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert data: {e}")
            return False


class NFLDataSync:
    """Main synchronization class."""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client = SimpleSupabaseClient(supabase_url, supabase_key)
        
        # NFL columns based on your database schema
        # Required columns
        self.required_columns = [
            'game_id', 'play_id', 'season', 'season_type', 'week', 'game_date',
            'home_team', 'away_team', 'posteam', 'defteam',
            'qtr', 'down', 'ydstogo', 'yardline_100', 'play_type',
            'yards_gained', 'touchdown', 'first_down',
            'rush_attempt', 'pass_attempt', 'sack', 'fumble', 'interception',
            'penalty', 'two_point_attempt'
        ]
        
        # Critical columns for detailed calculations
        self.critical_columns = [
            'fumble_lost', 'extra_point_result', 'two_point_conv_result', 'field_goal_result',
            'first_down_rush', 'first_down_pass', 'first_down_penalty', 'penalty_team',
            'drive', 'complete_pass', 'incomplete_pass', 'pass_touchdown', 'rush_touchdown',
            'passing_yards', 'rushing_yards', 'receiving_yards'
        ]
        
        # Optional columns
        self.optional_columns = [
            'td_team', 'penalty_yards', 'success', 'epa', 'qb_kneel',
            'posteam_score_post', 'defteam_score_post'
        ]
    
    def sync_season(self, season: int) -> Dict:
        """Sync a season's data."""
        result = {
            'season': season,
            'sync_performed': False,
            'api_plays': 0,
            'db_plays_before': 0,
            'db_plays_after': 0,
            'missing_games': [],
            'missing_teams': [],
            'new_plays_added': 0,
            'errors': []
        }
        
        try:
            # Step 1: Get NFL API data
            logger.info(f"Fetching NFL data for season {season}...")
            all_columns = self.required_columns + self.critical_columns + self.optional_columns
            api_data = nfl.import_pbp_data([season], columns=all_columns)
            
            if api_data is None or len(api_data) == 0:
                result['errors'].append(f"No data from NFL API for season {season}")
                return result
            
            result['api_plays'] = len(api_data)
            api_games = set(api_data['game_id'].unique())
            api_teams = set(api_data['posteam'].dropna().unique())
            
            logger.info(f"API data: {len(api_data)} plays, {len(api_games)} games, {len(api_teams)} teams")
            
            # Step 2: Check database data
            logger.info(f"Checking database for season {season}...")
            db_play_count = self.client.get_season_play_count(season)
            db_games = self.client.get_season_games(season)
            db_teams = self.client.get_season_teams(season)
            
            result['db_plays_before'] = db_play_count
            
            logger.info(f"Database data: {db_play_count} plays, {len(db_games)} games, {len(db_teams)} teams")
            
            # Step 3: Compare and decide if sync needed
            missing_games = api_games - db_games
            missing_teams = api_teams - db_teams
            play_diff = len(api_data) - db_play_count
            
            result.update({
                'missing_games': sorted(list(missing_games)),
                'missing_teams': sorted(list(missing_teams))
            })
            
            needs_sync = (
                play_diff > 0 or 
                len(missing_games) > 0 or 
                len(missing_teams) > 0
            )
            
            if not needs_sync:
                logger.info(f"Season {season} is already up to date")
                result['db_plays_after'] = db_play_count
                return result
            
            # Step 4: Perform sync
            logger.info(f"Syncing season {season}...")
            logger.info(f"  Play difference: {play_diff}")
            logger.info(f"  Missing games: {len(missing_games)}")
            logger.info(f"  Missing teams: {len(missing_teams)}")
            
            # Prepare data for insertion
            data_records = self._prepare_data(api_data, season)
            
            # Delete existing data
            if db_play_count > 0:
                logger.info(f"Deleting existing data for season {season}...")
                if not self.client.delete_season_data(season):
                    result['errors'].append("Failed to delete existing data")
                    return result
            
            # Insert new data
            logger.info(f"Inserting {len(data_records)} plays...")
            if self.client.insert_play_data(data_records):
                result['sync_performed'] = True
                result['db_plays_after'] = len(data_records)
                result['new_plays_added'] = len(data_records) - db_play_count
                logger.info(f"Successfully synced season {season}")
            else:
                result['errors'].append("Failed to insert new data")
            
        except Exception as e:
            error_msg = f"Error syncing season {season}: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
        
        return result
    
    def _prepare_data(self, df: pd.DataFrame, season: int) -> List[Dict]:
        """Prepare DataFrame for database insertion."""
        # Filter to only columns that exist in both API data and our schema
        all_schema_columns = self.required_columns + self.critical_columns + self.optional_columns
        available_columns = [col for col in all_schema_columns if col in df.columns]
        
        logger.info(f"Using {len(available_columns)} columns out of {len(all_schema_columns)} possible")
        
        # Select only available columns
        cleaned = df[available_columns].copy()
        
        # Handle column mapping (qtr -> quarter)
        if 'qtr' in cleaned.columns:
            cleaned['quarter'] = cleaned['qtr']
            cleaned = cleaned.drop('qtr', axis=1)
        
        # Add timestamp
        latest_game = pd.to_datetime(df['game_date']).max()
        nfl_timestamp = latest_game.isoformat() if pd.notna(latest_game) else datetime.now().isoformat()
        cleaned['nfl_data_timestamp'] = nfl_timestamp
        
        # Handle boolean-like columns (convert to float as per your schema)
        bool_like_columns = [
            'touchdown', 'first_down', 'rush_attempt', 'pass_attempt', 
            'sack', 'fumble', 'interception', 'penalty', 'two_point_attempt',
            'fumble_lost', 'first_down_rush', 'first_down_pass', 'first_down_penalty',
            'complete_pass', 'incomplete_pass', 'pass_touchdown', 'rush_touchdown'
        ]
        
        for col in bool_like_columns:
            if col in cleaned.columns:
                cleaned[col] = cleaned[col].fillna(0.0).astype(float)
        
        # Handle qb_kneel specially (keep as boolean if exists, otherwise calculate)
        if 'qb_kneel' in cleaned.columns:
            cleaned['qb_kneel'] = cleaned['qb_kneel'].fillna(False).astype(bool)
        elif 'play_type' in cleaned.columns:
            cleaned['qb_kneel'] = cleaned['play_type'] == 'qb_kneel'
        
        # Handle missing values
        if 'penalty_yards' in cleaned.columns:
            cleaned['penalty_yards'] = cleaned['penalty_yards'].fillna(0)
        
        cleaned['yards_gained'] = cleaned['yards_gained'].fillna(0)
        
        # Filter out invalid plays (missing game_id or play_id)
        cleaned = cleaned.dropna(subset=['game_id', 'play_id'])
        
        # Convert to records
        records = cleaned.to_dict('records')
        
        # Clean numpy types and handle special values
        cleaned_records = []
        for record in records:
            cleaned_record = {}
            for key, value in record.items():
                if pd.isna(value):
                    cleaned_record[key] = None
                elif hasattr(value, 'item'):  # numpy scalar
                    cleaned_record[key] = value.item()
                elif isinstance(value, (pd.Timestamp, datetime)):
                    cleaned_record[key] = value.isoformat()
                elif isinstance(value, bool):
                    cleaned_record[key] = value
                else:
                    cleaned_record[key] = value
            cleaned_records.append(cleaned_record)
        
        logger.info(f"Prepared {len(cleaned_records)} play records for insertion")
        return cleaned_records


def main():
    parser = argparse.ArgumentParser(description='NFL Data Synchronization Utility')
    parser.add_argument('--season', type=int, required=True, help='NFL season year (e.g., 2024)')
    parser.add_argument('--supabase-url', required=True, help='Supabase project URL')
    parser.add_argument('--supabase-key', required=True, help='Supabase API key')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create sync utility
    sync = NFLDataSync(args.supabase_url, args.supabase_key)
    
    # Run sync
    print(f"Starting NFL data sync for season {args.season}...")
    result = sync.sync_season(args.season)
    
    # Print results
    print(f"\nSync Results for Season {result['season']}:")
    print(f"  Sync Performed: {result['sync_performed']}")
    print(f"  API Plays: {result['api_plays']}")
    print(f"  DB Plays Before: {result['db_plays_before']}")
    print(f"  DB Plays After: {result['db_plays_after']}")
    print(f"  New Plays Added: {result['new_plays_added']}")
    
    if result.get('missing_games'):
        print(f"  Missing Games: {len(result['missing_games'])}")
    
    if result.get('missing_teams'):
        print(f"  Missing Teams: {result['missing_teams']}")
    
    if result.get('errors'):
        print(f"  Errors: {result['errors']}")
    
    print("\nSync complete!")


if __name__ == "__main__":
    main()