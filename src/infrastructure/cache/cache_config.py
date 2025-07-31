# src/infrastructure/cache/cache_config.py

from dataclasses import dataclass
from typing import Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)




class DataSource(Enum):
    """Data source selection."""
    DATABASE = "database"              # Use database (materialized views)
    NFL_LIBRARY = "nfl_library"        # Use NFL library to fetch data




@dataclass
class CacheConfig:
    """Explicit cache configuration replacing hidden factory patterns."""
    
    # Core configuration
    data_source: DataSource = DataSource.DATABASE  # Use database by default
    
    def __post_init__(self):
        """Log cache setup."""
        logger.info(f"Cache configured: {self.get_description()}")
    
    def get_description(self) -> str:
        """Get human-readable description of cache configuration."""
        return f"DataSource={self.data_source.value}"
    
    def should_use_database(self) -> bool:
        """Determine if this config should use database."""
        return self.data_source == DataSource.DATABASE
    
    def should_use_nfl_library(self) -> bool:
        """Determine if this config should use NFL library."""
        return self.data_source == DataSource.NFL_LIBRARY
    
