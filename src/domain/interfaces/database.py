# src/domain/interfaces/database.py - Essential database interfaces

from abc import ABC, abstractmethod
from typing import Any, Dict


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class DatabaseConnectionInterface(ABC):
    """Abstract interface for database connections."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish database connection."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test database connectivity."""
        pass
    
    @abstractmethod
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection status information."""
        pass