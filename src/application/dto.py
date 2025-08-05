# src/application/dto.py - Data Transfer Objects with comprehensive validation

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
from ..domain.entities import Team, Season, GameStats, SeasonStats, PerformanceRank, TeamRecord
from ..domain.validation import NFLValidator


class ExportFormat(Enum):
    """Supported export formats for analysis data."""
    CSV = "csv"
    EXCEL = "excel" 
    JSON = "json"


@dataclass
class TeamAnalysisRequest:
    """Request for team analysis with comprehensive input validation."""
    team_abbreviation: str
    season_year: int
    season_type_filter: str
    configuration: Dict[str, Any]
    cache_nfl_data: bool = True
    
    def __post_init__(self):
        """Validate input data after initialization."""
        self._validate_team_abbreviation()
        self._validate_season_year()
        self._validate_season_type_filter()
        self._validate_configuration()
        self._validate_playoff_eligibility()
    
    def _validate_team_abbreviation(self):
        """Validate team abbreviation format and content."""
        self.team_abbreviation = NFLValidator.validate_team_abbreviation(
            self.team_abbreviation, "team_abbreviation"
        )
    
    def _validate_season_year(self):
        """Validate season year is within reasonable bounds."""
        self.season_year = NFLValidator.validate_season_year(
            self.season_year, "season_year"
        )
    
    def _validate_season_type_filter(self):
        """Validate season type filter."""
        self.season_type_filter = NFLValidator.validate_season_type(
            self.season_type_filter, "season_type_filter"
        )
    
    def _validate_configuration(self):
        """Validate configuration dictionary structure."""
        self.configuration = NFLValidator.validate_configuration(
            self.configuration, "configuration"
        )
    
    def _validate_playoff_eligibility(self):
        """Validate that playoff requests are for teams that made playoffs."""
        # TODO: Add playoff eligibility validation
        # For now, playoff validation happens at the data access layer
        pass


@dataclass
class TeamAnalysisResponse:
    """Response containing team analysis results."""
    team: Team
    season: Season
    season_stats: SeasonStats
    game_stats: List[GameStats]
    team_record: Optional[TeamRecord] = None
    rankings: Optional[Dict[str, PerformanceRank]] = None
    league_averages: Optional[Dict[str, float]] = None


@dataclass
class DataStatusInfo:
    """Information about data freshness and status with validation."""
    latest_game_date: str
    days_old: int
    is_current: bool
    status_message: str
    status_type: str  # 'success', 'warning', 'info', 'error'
    
    def __post_init__(self):
        """Validate data status information."""
        self._validate_status_type()
        self._validate_days_old()
        self._validate_strings()
    
    def _validate_status_type(self):
        """Validate status type is one of the allowed values."""
        valid_types = {'success', 'warning', 'info', 'error'}
        if self.status_type not in valid_types:
            raise ValueError(f"Status type must be one of: {', '.join(sorted(valid_types))}")
    
    def _validate_days_old(self):
        """Validate days_old is a reasonable value."""
        if not isinstance(self.days_old, int):
            raise ValueError("days_old must be an integer")
        
        if self.days_old < 0:
            raise ValueError("days_old cannot be negative")

    def _validate_strings(self):
        """Validate string fields are properly formatted."""
        if not isinstance(self.latest_game_date, str):
            raise ValueError("latest_game_date must be a string")
        
        if not isinstance(self.status_message, str):
            raise ValueError("status_message must be a string")
        
        # Basic length validation to prevent extremely long messages
        if len(self.status_message) > 1500:
            raise ValueError("status_message cannot exceed 1500 characters")


@dataclass
class SeasonContextInfo:
    """Context information about a season with validation."""
    season: Season
    message: str
    message_type: str
    games_expected: int
    games_actual: Optional[int] = None
    
    def __post_init__(self):
        """Validate season context information."""
        self._validate_message_type()
        self._validate_games_counts()
        self._validate_message()
    
    def _validate_message_type(self):
        """Validate message type is allowed."""
        valid_types = {'success', 'warning', 'info', 'error'}
        if self.message_type not in valid_types:
            raise ValueError(f"Message type must be one of: {', '.join(sorted(valid_types))}")
    
    def _validate_games_counts(self):
        """Validate game count values."""
        if not isinstance(self.games_expected, int) or self.games_expected < 0:
            raise ValueError("games_expected must be a non-negative integer")
        
        if self.games_actual is not None:
            if not isinstance(self.games_actual, int) or self.games_actual < 0:
                raise ValueError("games_actual must be a non-negative integer or None")
    
    def _validate_message(self):
        """Validate message content."""
        if not isinstance(self.message, str):
            raise ValueError("message must be a string")
        
        if len(self.message) > 1500:
            raise ValueError("message cannot exceed 1500 characters")