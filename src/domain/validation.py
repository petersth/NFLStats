# src/domain/validation.py - Domain validation rules for NFL data

import re
from datetime import datetime
from typing import Any, Optional
from ..config import NFL_TEAMS, VALID_TEAMS, NFL_DATA_START_YEAR, SEASON_TYPES
from .exceptions import DataValidationError


class NFLValidator:
    """Domain validator for NFL-specific business rules."""
    
    @staticmethod
    def validate_season_year(season_year: Any, field_name: str = "season_year") -> int:
        """Validate and convert season year to integer.
        
        Business rules:
        - Must be within NFL data availability range
        - Cannot be more than one year in the future
        """
        if season_year is None:
            raise DataValidationError(f"{field_name} cannot be None", field_name, season_year)
        
        try:
            year = int(season_year)
        except (ValueError, TypeError):
            raise DataValidationError(f"{field_name} must be a valid integer", field_name, season_year)
        
        current_year = datetime.now().year
        
        if year < NFL_DATA_START_YEAR:
            raise DataValidationError(
                f"{field_name} must be {NFL_DATA_START_YEAR} or later (NFL data availability)",
                field_name, year
            )
        
        if year > current_year + 1:
            raise DataValidationError(
                f"{field_name} cannot be more than one year in the future",
                field_name, year
            )
        
        return year
    
    @staticmethod
    def validate_team_abbreviation(team_abbr: Any, field_name: str = "team_abbreviation") -> str:
        """Validate NFL team abbreviation.
        
        Business rules:
        - Must be valid NFL team abbreviation
        - Format: 2-4 uppercase letters
        """
        if team_abbr is None:
            raise DataValidationError(f"{field_name} cannot be None", field_name, team_abbr)
        
        if not isinstance(team_abbr, str):
            raise DataValidationError(f"{field_name} must be a string", field_name, team_abbr)
        
        # Normalize: uppercase and strip whitespace
        normalized = team_abbr.upper().strip()
        
        # Format validation: 2-4 uppercase letters only
        if not re.match(r'^[A-Z]{2,4}$', normalized):
            raise DataValidationError(f"{field_name} must be 2-4 uppercase letters only", field_name, normalized)
        
        # Check against valid NFL teams
        if normalized not in VALID_TEAMS:
            sorted_teams = sorted(NFL_TEAMS)
            raise DataValidationError(
                f"Invalid team abbreviation: {normalized}. Must be one of: {', '.join(sorted_teams)}",
                field_name, normalized
            )
        
        return normalized
    
    @staticmethod
    def validate_season_type(season_type: Any, field_name: str = "season_type") -> str:
        """Validate season type.
        
        Business rules:
        - Must be one of: ALL, REG, POST
        """
        if season_type is None:
            raise DataValidationError(f"{field_name} cannot be None", field_name, season_type)
        
        if not isinstance(season_type, str):
            raise DataValidationError(f"{field_name} must be a string", field_name, season_type)
        
        normalized = season_type.upper().strip()
        
        if normalized not in SEASON_TYPES:
            raise DataValidationError(
                f"Invalid season type: {normalized}. Must be one of: {', '.join(sorted(SEASON_TYPES))}",
                field_name, normalized
            )
        
        return normalized
    
    @staticmethod
    def validate_configuration(config: Any, field_name: str = "configuration") -> dict:
        """Validate NFL configuration dictionary.
        
        Business rules:
        - Must contain valid boolean flags for QB kneel handling
        - Validates known configuration fields
        """
        if config is None:
            raise DataValidationError(f"{field_name} cannot be None", field_name, config)
        
        if not isinstance(config, dict):
            raise DataValidationError(f"{field_name} must be a dictionary", field_name, config)
        
        # Basic validation for known configuration fields
        validated_config = config.copy()
        
        # Validate boolean fields
        boolean_fields = [
            'include_playoffs', 
            'exclude_kneel_downs', 
            'include_qb_kneels_rushing', 
            'include_qb_kneels_success_rate'
        ]
        
        for field in boolean_fields:
            if field in validated_config:
                if not isinstance(validated_config[field], bool):
                    raise DataValidationError(
                        f"{field} must be a boolean",
                        field, validated_config[field]
                    )
        
        return validated_config


# Generic validation utilities (not NFL-specific)
def validate_positive_integer(value: Any, field_name: str) -> int:
    """Validate that a value is a positive integer.
    
    This is a generic validation utility, not NFL-specific.
    """
    if value is None:
        raise DataValidationError(f"{field_name} cannot be None", field_name, value)
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise DataValidationError(f"{field_name} must be a valid integer", field_name, value)
    
    if int_value <= 0:
        raise DataValidationError(f"{field_name} must be positive", field_name, int_value)
    
    return int_value