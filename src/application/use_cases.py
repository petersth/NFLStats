# src/application/use_cases.py - Application use cases

import logging
from typing import Optional, Dict
from datetime import datetime
import pandas as pd

from ..domain.entities import Team, Season
from ..domain.orchestration import CalculationOrchestrator
from ..utils import ranking_utils
from ..domain.validation import InputValidator
from ..domain.exceptions import UseCaseError, DataValidationError
from .dto import TeamAnalysisRequest, TeamAnalysisResponse, DataStatusInfo

logger = logging.getLogger(__name__)

class GetDataStatusUseCase:
    """Use case for determining data freshness and status."""
    
    def __init__(self, season_service=None):
        """Initialize with optional season service for future extensibility."""
        self._season_service = season_service
    
    def execute(self, latest_game_date: pd.Timestamp, season: Season) -> DataStatusInfo:
        """Execute data status check."""
        # Note: season parameter reserved for future enhancements
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
            if days_old <= 1:
                status_type = "success"
                status_message = "Data is current (within 24 hours)"
                is_current = True
            elif days_old <= 7:
                status_type = "info" 
                status_message = f"Data is {days_old} days old"
                is_current = True
            elif days_old <= 14:
                status_type = "warning"
                status_message = f"Data is {days_old} days old - may need refresh"
                is_current = False
            else:
                status_type = "warning"
                status_message = f"Data is {days_old} days old - refresh recommended"
                is_current = False
            
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