# src/utils/season_filters.py - Season filtering utility functions

import logging

logger = logging.getLogger(__name__)


def apply_season_type_filter(data, season_type_filter: str):
    """Apply season type filtering to data.
    
    Args:
        data: DataFrame containing NFL play data
        season_type_filter: Filter type ('ALL', 'REG', 'POST')
        
    Returns:
        Filtered DataFrame based on season type
    """
    if season_type_filter == "ALL":
        # Return both regular season and playoffs
        filtered_data = data[data['season_type'].isin(['REG', 'POST'])]
    elif season_type_filter == "REG":
        # Return only regular season
        filtered_data = data[data['season_type'] == 'REG']
    elif season_type_filter == "POST":
        # Return only playoffs
        filtered_data = data[data['season_type'] == 'POST']
        
        # Log warning if no playoff data found
        if len(filtered_data) == 0 and len(data) > 0:
            # Check if this team had any games at all
            teams_in_data = set()
            if 'posteam' in data.columns:
                teams_in_data.update(data['posteam'].dropna().unique())
            if 'home_team' in data.columns:
                teams_in_data.update(data['home_team'].dropna().unique())
            if 'away_team' in data.columns:
                teams_in_data.update(data['away_team'].dropna().unique())
                
            if teams_in_data:
                team_str = ', '.join(sorted(teams_in_data)[:3])  # Show first few teams
                logger.info(f"No playoff data found for team(s): {team_str} - team likely did not make playoffs")
    else:
        # Default to all games
        filtered_data = data
        
    return filtered_data