# src/utils/team_code_mapper.py - Handle historical team display names

"""
Team display name mapper for showing historically accurate team names.

The nfl_data_py library uses current team codes for all historical data.
For example, the St. Louis Rams (1995-2015) are coded as 'LA' in the data.

This module provides the correct display names based on the year.
"""


def get_team_display_name(team_code: str, year: int = None) -> str:
    """
    Get the display name for a team, accounting for historical names.
    
    Args:
        team_code: The team code (e.g., 'LA', 'LV', 'LAC')
        year: Optional year for historical context
        
    Returns:
        The team's display name appropriate for that year
    """
    # Check if this team had a different name in the given year
    if year:
        # LA Rams -> St. Louis Rams (1995-2015)
        if team_code == 'LA' and 1995 <= year <= 2015:
            return 'St. Louis Rams'
        
        # LV Raiders -> Oakland Raiders (1995-2019)
        if team_code == 'LV' and 1995 <= year <= 2019:
            return 'Oakland Raiders'
        
        # LAC Chargers -> San Diego Chargers (1960-2016)
        if team_code == 'LAC' and year <= 2016:
            return 'San Diego Chargers'
    
    # Otherwise use the current team data
    from ..config.nfl_constants import TEAM_DATA
    if team_code in TEAM_DATA:
        return TEAM_DATA[team_code]['name']
    
    return f"Unknown Team ({team_code})"