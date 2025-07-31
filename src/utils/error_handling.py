# src/utils/error_handling.py - Standardized error handling utilities

import logging
import functools
from typing import Any, Callable, Optional, Type, Union
from ..domain.exceptions import UseCaseError, CacheError, DataAccessError

logger = logging.getLogger(__name__)


def handle_service_errors(
    operation: str,
    error_type: Type[Exception] = UseCaseError,
    default_return: Any = None,
    log_level: str = "error"
):
    """
    Decorator for standardized service-level error handling.
    
    Args:
        operation: Description of the operation for error messages
        error_type: Exception type to raise on errors
        default_return: Default value to return on error (if not raising)
        log_level: Logging level ('error', 'warning', 'info')
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"Failed to {operation}: {str(e)}"
                
                # Log at specified level
                if log_level == "error":
                    logger.error(error_msg)
                elif log_level == "warning":
                    logger.warning(error_msg)
                elif log_level == "info":
                    logger.info(error_msg)
                
                # Raise appropriate error type or return default
                if default_return is not None:
                    return default_return
                else:
                    raise error_type(error_msg, operation, getattr(e, '__dict__', {}))
        
        return wrapper
    return decorator


def handle_cache_errors(operation: str, default_return: Any = None):
    """Specialized decorator for cache operations."""
    return handle_service_errors(
        operation=operation,
        error_type=CacheError,
        default_return=default_return,
        log_level="error"
    )


def handle_data_access_errors(operation: str, default_return: Any = None):
    """Specialized decorator for data access operations."""
    return handle_service_errors(
        operation=operation,
        error_type=DataAccessError,
        default_return=default_return,
        log_level="error"
    )


def safe_execute(
    func: Callable,
    operation: str,
    default_return: Any = None,
    log_errors: bool = True
) -> Any:
    """
    Safely execute a function with standardized error handling.
    
    Useful for inline error handling without decorators.
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(f"Failed to {operation}: {str(e)}")
        return default_return


class ErrorContext:
    """Context manager for standardized error handling."""
    
    def __init__(
        self,
        operation: str,
        error_type: Type[Exception] = Exception,
        default_return: Any = None,
        suppress_errors: bool = False
    ):
        self.operation = operation
        self.error_type = error_type
        self.default_return = default_return
        self.suppress_errors = suppress_errors
        self.exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.exception = exc_val
            error_msg = f"Failed to {self.operation}: {str(exc_val)}"
            logger.error(error_msg)
            
            if self.suppress_errors:
                return True  # Suppress the exception
            elif self.default_return is not None:
                return True  # Suppress and return default
            else:
                # Re-raise as specified error type
                if exc_type != self.error_type:
                    raise self.error_type(error_msg, self.operation, {}) from exc_val
        
        return False