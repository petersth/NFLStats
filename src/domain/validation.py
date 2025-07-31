# src/domain/validation.py - Input validation for domain entities and operations

from typing import Any, Optional
from .exceptions import DataValidationError
from ..utils.validation import SharedValidator, ValidationError
from ..config import TOTAL_NFL_TEAMS


class InputValidator(SharedValidator):
    """Domain validation service for input validation across the application."""
    
    @classmethod
    def validate_season_year(cls, season_year: Any, field_name: str = "season_year") -> int:
        """Validate and convert season year to integer."""
        try:
            return super().validate_season_year(season_year, field_name)
        except ValidationError as e:
            raise DataValidationError(str(e), field_name, season_year)
    
    @classmethod
    def validate_team_abbreviation(cls, team_abbr: Any, field_name: str = "team_abbreviation") -> str:
        """Validate NFL team abbreviation."""
        try:
            return super().validate_team_abbreviation(team_abbr, field_name)
        except ValidationError as e:
            raise DataValidationError(str(e), field_name, team_abbr)
    
    @classmethod
    def validate_season_type(cls, season_type: Any, field_name: str = "season_type") -> str:
        """Validate season type."""
        try:
            return super().validate_season_type(season_type, field_name)
        except ValidationError as e:
            raise DataValidationError(str(e), field_name, season_type)
    
    @classmethod
    def validate_positive_integer(cls, value: Any, field_name: str) -> int:
        """Validate that a value is a positive integer."""
        try:
            return super().validate_positive_integer(value, field_name)
        except ValidationError as e:
            raise DataValidationError(str(e), field_name, value)
    
    @classmethod
    def validate_percentage(cls, value: Any, field_name: str, allow_none: bool = False) -> Optional[float]:
        """Validate that a value is a valid percentage (0-100)."""
        if value is None:
            if allow_none:
                return None
            raise DataValidationError(f"{field_name} cannot be None", field_name, value)
        
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise DataValidationError(f"{field_name} must be a valid number", field_name, value)
        
        if float_value < 0 or float_value > 100:
            raise DataValidationError(f"{field_name} must be between 0 and 100", field_name, float_value)
        
        return float_value
    
    @classmethod
    def validate_game_id(cls, game_id: Any, field_name: str = "game_id") -> str:
        """Validate NFL game ID format."""
        if game_id is None:
            raise DataValidationError(f"{field_name} cannot be None", field_name, game_id)
        
        if not isinstance(game_id, str):
            raise DataValidationError(f"{field_name} must be a string", field_name, game_id)
        
        game_id = game_id.strip()
        
        # Basic format validation for NFL game IDs (usually YYYY_XX_TEAM1_TEAM2 or similar)
        if len(game_id) < 10:
            raise DataValidationError(f"{field_name} appears to be too short", field_name, game_id)
        
        # Check for reasonable characters (alphanumeric, underscore, dash)
        if not re.match(r'^[A-Za-z0-9_-]+$', game_id):
            raise DataValidationError(
                f"{field_name} contains invalid characters (only alphanumeric, underscore, dash allowed)", 
                field_name, game_id
            )
        
        return game_id
    
    @classmethod
    def validate_configuration_dict(cls, config: Any, field_name: str = "configuration") -> dict:
        """Validate configuration dictionary."""
        try:
            validated_config = super().validate_configuration_dict(config, field_name)
            
            # Additional domain-specific validation
            if 'include_playoffs' in validated_config:
                if not isinstance(validated_config['include_playoffs'], bool):
                    raise DataValidationError(
                        "include_playoffs must be a boolean", 
                        "include_playoffs", 
                        validated_config['include_playoffs']
                    )
            
            if 'exclude_kneel_downs' in validated_config:
                if not isinstance(validated_config['exclude_kneel_downs'], bool):
                    raise DataValidationError(
                        "exclude_kneel_downs must be a boolean", 
                        "exclude_kneel_downs", 
                        validated_config['exclude_kneel_downs']
                    )
            
            return validated_config
        except ValidationError as e:
            raise DataValidationError(str(e), field_name, config)