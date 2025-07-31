# src/infrastructure/statistics/calculators/play_filter.py

import logging
from typing import List
import pandas as pd

logger = logging.getLogger(__name__)


class PlayFilter:
    """Handles filtering of plays for different calculation contexts."""
    
    def get_offensive_plays(self, data: pd.DataFrame) -> pd.DataFrame:
        """Get official offensive plays using consistent NFL methodology.
        
        Returns plays that count toward official offensive statistics:
        - Rush attempts (rush_attempt = 1)
        - Pass attempts (pass_attempt = 1)  
        - Excludes two-point conversions (scoring plays, not offensive plays)
        - Excludes plays with missing yards_gained data
        """
        if len(data) == 0:
            return data
        
        required_columns = ['rush_attempt', 'pass_attempt', 'two_point_attempt', 'yards_gained']
        if not self._has_required_columns(data, required_columns):
            logger.warning("Missing required columns for offensive plays filter")
            return pd.DataFrame()
        
        # Official offensive plays: rush attempts + pass attempts
        offensive_mask = (
            (data['rush_attempt'] == 1) | 
            (data['pass_attempt'] == 1)
        )
        
        # Exclude two-point conversions (scoring plays, not offensive plays)
        offensive_mask &= (data['two_point_attempt'] != 1)
        
        # Exclude plays with missing yards_gained
        offensive_mask &= data['yards_gained'].notna()
        
        return data[offensive_mask].copy()
    
    def get_rushing_plays(self, data: pd.DataFrame) -> pd.DataFrame:
        """Get rushing plays with configuration exclusions."""
        if len(data) == 0:
            return data
        
        if 'rush_attempt' not in data.columns:
            logger.warning("Missing 'rush_attempt' column for rushing plays filter")
            return pd.DataFrame()
        
        rushing_plays = data[
            (data['rush_attempt'] == 1) & 
            data['yards_gained'].notna() &
            (data['two_point_attempt'] != 1)
        ].copy()
        
        # Apply rushing-specific exclusions
        if '_qb_kneel_context' in rushing_plays.columns:
            rushing_plays = rushing_plays[rushing_plays['_qb_kneel_context'] != 'exclude_rushing']
        
        return rushing_plays
    
    def get_passing_plays(self, data: pd.DataFrame) -> pd.DataFrame:
        """Get passing plays excluding sacks and two-point conversions."""
        if len(data) == 0:
            return data
        
        required_columns = ['pass_attempt', 'sack', 'two_point_attempt']
        if not self._has_required_columns(data, required_columns):
            logger.warning("Missing required columns for passing plays filter")
            return pd.DataFrame()
        
        return data[
            (data['pass_attempt'] == 1) & 
            (data['sack'] == 0) &
            (data['two_point_attempt'] != 1)
        ].copy()
    
    def get_third_down_attempts(self, data: pd.DataFrame) -> pd.DataFrame:
        """Get third down attempts excluding two-point conversions."""
        if len(data) == 0:
            return data
        
        required_columns = ['down', 'rush_attempt', 'pass_attempt', 'two_point_attempt']
        if not self._has_required_columns(data, required_columns):
            logger.warning("Missing required columns for third down filter")
            return pd.DataFrame()
        
        third_downs = data[
            (data['down'] == 3) & 
            ((data['rush_attempt'] == 1) | (data['pass_attempt'] == 1)) &
            (data['two_point_attempt'] != 1)
        ].copy()
        
        # Apply QB kneel context filtering for efficiency metrics
        if '_qb_kneel_context' in third_downs.columns:
            third_downs = third_downs[third_downs['_qb_kneel_context'] != 'exclude_success_rate']
        
        return third_downs
    
    def get_offensive_touchdowns(self, data: pd.DataFrame, team_abbr: str = None) -> pd.DataFrame:
        """Get offensive touchdowns scored BY the team (excludes defensive TDs scored against the team).
        
        Uses td_team column to ensure we only count TDs actually scored by the team,
        not defensive TDs scored by opponents when the team had possession.
        """
        if len(data) == 0:
            return data
        
        if 'touchdown' not in data.columns:
            logger.warning("Missing 'touchdown' column for touchdown filter")
            return pd.DataFrame()
        
        # Use td_team to identify who actually scored the TD
        # This excludes pick-6s and fumble returns by opponents
        if 'td_team' in data.columns and team_abbr:
            return data[
                (data['touchdown'] == 1) & 
                (data['td_team'] == team_abbr)
            ].copy()
        else:
            # Fallback to old method if td_team not available
            return data[
                (data['touchdown'] == 1) & 
                (
                    (data['yards_gained'] > 0) |  # Positive yard TDs
                    ((data['yards_gained'] == 0) & 
                     ((data['rush_attempt'] == 1) | (data['pass_attempt'] == 1)))  # Zero-yard offensive TDs
                )
            ].copy()
    
    def apply_success_rate_exclusions(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply success rate specific exclusions based on configuration."""
        if len(data) == 0:
            return data
        
        filtered_data = data.copy()
        
        # Apply configuration filtering for success rate stats
        if '_qb_kneel_context' in filtered_data.columns:
            filtered_data = filtered_data[filtered_data['_qb_kneel_context'] != 'exclude_success_rate']
        
        return filtered_data
    
    def _has_required_columns(self, data: pd.DataFrame, required_columns: List[str]) -> bool:
        """Check if all required columns exist in the dataframe."""
        missing_columns = [col for col in required_columns if col not in data.columns]
        return len(missing_columns) == 0