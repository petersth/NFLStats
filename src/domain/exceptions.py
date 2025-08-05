# src/domain/exceptions.py - Domain exceptions for standardized error handling

class NFLStatsException(Exception):
    """Base exception for NFL Statistics application."""
    pass


class CacheError(NFLStatsException):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str, cache_key: str = None, operation: str = None, cause: Exception = None):
        self.cache_key = cache_key
        self.operation = operation
        self.cause = cause
        super().__init__(message)


class DataAccessError(NFLStatsException):
    """Raised when data access operations fail."""
    
    def __init__(self, message: str, season_year: int = None, season_type: str = None):
        self.season_year = season_year
        self.season_type = season_type
        super().__init__(message)


class DataNotFoundError(DataAccessError):
    """Raised when requested data is not found.
    
    This is a specific type of DataAccessError for when data doesn't exist,
    as opposed to general access failures.
    """
    pass


class DataValidationError(NFLStatsException):
    """Raised when data validation fails.
    
    Used for input validation errors, not data access errors.
    """
    
    def __init__(self, message: str, field_name: str = None, field_value=None):
        self.field_name = field_name
        self.field_value = field_value
        super().__init__(message)


class UseCaseError(NFLStatsException):
    """Raised when use case execution fails.
    
    High-level exception for business logic failures.
    """
    
    def __init__(self, message: str, operation: str = None, context: dict = None):
        self.operation = operation
        self.context = context or {}
        super().__init__(message)