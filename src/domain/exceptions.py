# src/domain/exceptions.py - Domain exceptions for standardized error handling

class NFLStatsException(Exception):
    """Base exception for NFL Statistics application."""
    pass


class StatisticsCalculationError(NFLStatsException):
    """Raised when statistics calculation fails."""
    
    def __init__(self, message: str, team_abbr: str = None, season_year: int = None):
        self.team_abbr = team_abbr
        self.season_year = season_year
        super().__init__(message)


class CacheError(NFLStatsException):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str, cache_key: str = None, operation: str = None):
        self.cache_key = cache_key
        self.operation = operation
        super().__init__(message)


class DataAccessError(NFLStatsException):
    """Raised when data access operations fail."""
    
    def __init__(self, message: str, season_year: int = None, season_type: str = None):
        self.season_year = season_year
        self.season_type = season_type
        super().__init__(message)


class DataNotFoundError(DataAccessError):
    """Raised when requested data is not found."""
    pass


class ConfigurationError(NFLStatsException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_key: str = None):
        self.config_key = config_key
        super().__init__(message)




class DatabaseConnectionError(DataAccessError):
    """Raised when database connection fails."""
    pass


class DatabaseIntegrityError(DataAccessError):
    """Raised when database integrity checks fail."""
    pass


class DataValidationError(DataAccessError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field_name: str = None, field_value=None):
        self.field_name = field_name
        self.field_value = field_value
        super().__init__(message)


class BatchInsertError(DataAccessError):
    """Raised when batch insert operations fail."""
    
    def __init__(self, message: str, batch_number: int = None, total_batches: int = None):
        self.batch_number = batch_number
        self.total_batches = total_batches
        super().__init__(message)


class UseCaseError(NFLStatsException):
    """Raised when use case execution fails."""
    
    def __init__(self, message: str, operation: str = None, context: dict = None):
        self.operation = operation
        self.context = context or {}
        super().__init__(message)


class CalculationError(NFLStatsException):
    """Raised when statistical calculations fail."""
    
    def __init__(self, message: str, metric_name: str = None, team_abbr: str = None):
        self.metric_name = metric_name
        self.team_abbr = team_abbr
        super().__init__(message)


class CacheOperationError(CacheError):
    """Raised when cache operations fail with specific context."""
    
    def __init__(self, message: str, cache_key: str = None, operation: str = None, cause: Exception = None):
        self.cause = cause
        super().__init__(message, cache_key, operation)