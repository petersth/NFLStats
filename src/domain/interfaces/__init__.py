# Domain interfaces - Essential abstractions only

from .database import (
    DatabaseConnectionInterface,
    DatabaseError
)

# Export essential interfaces only
__all__ = [
    'DatabaseConnectionInterface',
    'DatabaseError'
]