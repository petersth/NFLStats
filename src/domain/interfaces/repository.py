# src/domain/interfaces/repository.py - Repository interfaces for the domain layer

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict
import pandas as pd


class DataRepositoryInterface(ABC):
    """Enhanced repository interface with data source capabilities."""
    
    @abstractmethod
    def get_play_by_play_data(self, season: int) -> Tuple[Optional[pd.DataFrame], Optional[pd.Timestamp]]:
        pass
    
    @abstractmethod
    def get_team_data(self, pbp_data: pd.DataFrame, team_abbreviation: str, 
                     configuration: Optional[Dict] = None) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_league_aggregates(self, season: int, season_type: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get pre-calculated league aggregates for performance optimization."""
        pass
    
    # Data source capability methods
    @abstractmethod
    def requires_calculation(self) -> bool:
        """Whether this repository provides data that needs statistical calculation.
        
        Returns:
            True if data needs calculation (raw play-by-play)
            False if data is pre-calculated (aggregates)
        """
        pass
    
    @abstractmethod
    def get_data_source_name(self) -> str:
        """Human-readable name of the data source for logging/debugging."""
        pass
    
    @abstractmethod
    def supports_aggregated_data(self) -> bool:
        """Whether this repository can provide pre-aggregated statistical data."""
        pass