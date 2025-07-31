# src/utils/validation.py - Shared validation utilities

from typing import Any, Set
import re
from datetime import datetime
from ..config import NFL_TEAMS, VALID_TEAMS, NFL_DATA_START_YEAR, SEASON_TYPES


class ValidationError(ValueError):
    """Base validation error."""
    pass


class TeamValidationMixin:
    """Mixin providing team validation functionality."""
    
    @staticmethod
    def validate_team_abbreviation(team_abbr: Any, field_name: str = "team_abbreviation") -> str:
        """Validate NFL team abbreviation with comprehensive checks."""
        if team_abbr is None:
            raise ValidationError(f"{field_name} cannot be None")
        
        if not isinstance(team_abbr, str):
            raise ValidationError(f"{field_name} must be a string")
        
        # Normalize: uppercase and strip whitespace
        normalized = team_abbr.upper().strip()
        
        # Format validation: 2-4 uppercase letters only
        if not re.match(r'^[A-Z]{2,4}$', normalized):
            raise ValidationError(f"{field_name} must be 2-4 uppercase letters only")
        
        # Check against valid NFL teams
        if normalized not in VALID_TEAMS:
            sorted_teams = sorted(NFL_TEAMS)
            raise ValidationError(
                f"Invalid team abbreviation: {normalized}. Must be one of: {', '.join(sorted_teams)}"
            )
        
        return normalized
    
    @staticmethod
    def is_valid_team(team_abbr: str) -> bool:
        """Check if team abbreviation is valid without raising exceptions."""
        try:
            TeamValidationMixin.validate_team_abbreviation(team_abbr)
            return True
        except ValidationError:
            return False


class SeasonValidationMixin:
    """Mixin providing season validation functionality."""
    
    @staticmethod
    def validate_season_year(season_year: Any, field_name: str = "season_year") -> int:
        """Validate season year with comprehensive checks."""
        if season_year is None:
            raise ValidationError(f"{field_name} cannot be None")
        
        try:
            year = int(season_year)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid integer")
        
        current_year = datetime.now().year
        
        if year < NFL_DATA_START_YEAR:
            raise ValidationError(
                f"{field_name} must be >= {NFL_DATA_START_YEAR} (NFL data start year)"
            )
        
        if year > current_year + 1:  # Allow next year for pre-season
            raise ValidationError(
                f"{field_name} cannot be more than one year in the future"
            )
        
        return year
    
    @staticmethod
    def validate_season_type(season_type: Any, field_name: str = "season_type") -> str:
        """Validate season type."""
        if season_type is None:
            raise ValidationError(f"{field_name} cannot be None")
        
        if not isinstance(season_type, str):
            raise ValidationError(f"{field_name} must be a string")
        
        # Normalize: uppercase and strip whitespace
        normalized = season_type.upper().strip()
        
        valid_types = set(SEASON_TYPES.keys()) | {'ALL'}  # Include 'ALL' for filtering
        
        if normalized not in valid_types:
            sorted_types = sorted(valid_types)
            raise ValidationError(
                f"Invalid season type: {normalized}. Must be one of: {', '.join(sorted_types)}"
            )
        
        return normalized


class CommonValidationMixin:
    """Mixin providing common validation functionality."""
    
    @staticmethod
    def validate_positive_integer(value: Any, field_name: str) -> int:
        """Validate that a value is a positive integer."""
        if value is None:
            raise ValidationError(f"{field_name} cannot be None")
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid integer")
        
        if int_value <= 0:
            raise ValidationError(f"{field_name} must be positive")
        
        return int_value
    
    @staticmethod
    def validate_configuration_dict(config: Any, field_name: str = "configuration") -> dict:
        """Validate configuration dictionary structure."""
        if not isinstance(config, dict):
            raise ValidationError(f"{field_name} must be a dictionary")
        
        # Validate configuration keys and values
        for key, value in config.items():
            if not isinstance(key, str):
                raise ValidationError("Configuration keys must be strings")
            
            # Basic sanitization of key names
            if not re.match(r'^[a-zA-Z0-9_]+$', key):
                raise ValidationError(
                    f"Configuration key '{key}' contains invalid characters. "
                    "Only alphanumeric and underscore allowed."
                )
            
            # Validate value types
            if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                raise ValidationError(
                    f"Configuration value for '{key}' must be a basic data type "
                    "(str, int, float, bool, list, dict, or None)"
                )
        
        return config


class SharedValidator(TeamValidationMixin, SeasonValidationMixin, CommonValidationMixin):
    """Combined validator with all validation mixins."""
    pass
