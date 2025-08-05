# src/domain/services.py - Core business logic services

import logging
from datetime import datetime
from typing import Dict, List
import pandas as pd
from .entities import Season
from ..application.dto import DataStatusInfo

logger = logging.getLogger(__name__)


def get_data_status(latest_game_date: pd.Timestamp, season: Season) -> DataStatusInfo:
    """Get data status information based on the latest game date."""
    try:
        # Convert to datetime if needed
        if isinstance(latest_game_date, pd.Timestamp):
            game_date = latest_game_date.to_pydatetime()
        else:
            game_date = latest_game_date
        
        # Calculate days old
        now = datetime.now()
        days_old = (now - game_date).days
        
        # Format the date
        formatted_date = game_date.strftime("%Y-%m-%d")
        
        # Determine status based on age
        status_type = "info"
        status_message = f"Data is {days_old} days old"
        is_current = True
        
        return DataStatusInfo(
            latest_game_date=formatted_date,
            days_old=days_old,
            is_current=is_current,
            status_message=status_message,
            status_type=status_type
        )
        
    except Exception as e:
        logger.error(f"Failed to determine data status: {e}")
        return DataStatusInfo(
            latest_game_date="Unknown",
            days_old=0,
            is_current=False,
            status_message="Unable to determine data status",
            status_type="error"
        )


# RankingService converted to utility functions in src/utils/ranking_utils.py
# SeasonFilterService converted to utility functions in src/utils/season_utils.py
# League stats utilities available in src/utils/league_stats_utils.py
# NFL metrics constants consolidated in src/utils/nfl_metrics.py