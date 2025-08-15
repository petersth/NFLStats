# src/utils/season_utils.py - Season-related utility functions

import logging
from typing import Dict, Optional
from datetime import datetime
from ..config.nfl_constants import NFL_SEASON_START_MONTH, NFL_DATA_START_YEAR, NFL_REGULAR_SEASON_GAMES
from ..domain.entities import Season

logger = logging.getLogger(__name__)


def get_current_nfl_season_info() -> Dict:
    """Get comprehensive current NFL season information."""
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    if current_month >= NFL_SEASON_START_MONTH:  # September or later
        current_season = current_year
        season_status = "in_progress"
    elif current_month <= 2:  # January-February (playoffs/Super Bowl)
        current_season = current_year - 1
        season_status = "playoffs" if current_month == 1 else "completed"
    else:  # March-August (offseason)
        current_season = current_year - 1
        season_status = "completed"

    # Get the expected games based on the current season year
    expected_games = get_regular_season_games(current_season)

    if season_status == "completed":
        data_complete = True
    elif season_status == "playoffs":
        data_complete = True
    else:  # in_progress
        data_complete = False
    
    return {
        'current_season': current_season,
        'season_status': season_status,
        'expected_games': expected_games,
        'data_complete': data_complete,
        'available_seasons': list(range(current_season, NFL_DATA_START_YEAR - 1, -1))
    }


def get_season_context_message(season: Season, actual_games: Optional[int] = None) -> Dict[str, str]:
    """Get contextual message about the selected season."""
    season_info = get_current_nfl_season_info()
    
    if season.year == season_info['current_season']:
        if season_info['season_status'] == 'in_progress':
            if actual_games and actual_games < season_info['expected_games']:
                return {
                    'message': f"{season.year} season in progress • {actual_games}/{season_info['expected_games']} games played",
                    'type': 'info'
                }
            else:
                return {'message': f"{season.year} season in progress", 'type': 'info'}
        elif season_info['season_status'] == 'playoffs':
            return {'message': f"{season.year} season: Playoffs in progress", 'type': 'info'}
        else:
            return {'message': f"{season.year} season: Complete", 'type': 'success'}
    elif season.year > season_info['current_season']:
        return {'message': f"{season.year} season hasn't started yet", 'type': 'warning'}
    else:
        return {'message': f"{season.year} season: Historical data", 'type': 'success'}


def get_regular_season_weeks(season_year: int) -> int:
    """Get the number of regular season weeks for a given NFL season.
    
    Args:
        season_year: The NFL season year
        
    Returns:
        Number of regular season weeks (last week of regular season)
    """
    if season_year >= 2021:
        return 18  # 17-game regular season (weeks 1-18)
    elif season_year >= 1990:
        return 17  # 16-game regular season (weeks 1-17)
    else:
        # Pre-1990 seasons varied, defaulting to 16 weeks
        # This covers most cases from 1978-1989
        return 16


def get_regular_season_games(season_year: int) -> int:
    """Get the number of regular season games for a given NFL season.
    
    Args:
        season_year: The NFL season year
        
    Returns:
        Number of regular season games per team
    """
    if season_year >= 2021:
        return 17  # 17-game regular season
    elif season_year >= 1978:
        return 16  # 16-game regular season
    else:
        # Pre-1978 seasons varied (14 games, 12 games, etc.)
        return 14  # Most common pre-1978


def is_playoff_week(week: int, season_year: int) -> bool:
    """Determine if a given week is a playoff week for the season.
    
    Args:
        week: The week number
        season_year: The NFL season year
        
    Returns:
        True if the week is a playoff week, False otherwise
    """
    regular_season_weeks = get_regular_season_weeks(season_year)
    return week > regular_season_weeks


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
        
        # Handle case where team didn't make playoffs
        if len(filtered_data) == 0 and len(data) > 0:
            # Extract team identifiers from multiple possible columns to provide context
            # Different datasets may use different column names for team identification
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