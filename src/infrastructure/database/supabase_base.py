# src/infrastructure/database/supabase_base.py - Base class for Supabase connections

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class SupabaseConnectionBase:
    """Base class for Supabase database connections."""
    
    def __init__(self, url: str = None, key: str = None):
        """Initialize with Supabase URL and API key."""
        self.url = url
        self.key = key
        self._connected = bool(url and key)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get standardized connection info for Supabase API calls."""
        return {
            'url': self.url,
            'headers': {
                'apikey': self.key,
                'Authorization': f'Bearer {self.key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
        }
    
    def test_connection(self) -> bool:
        """Test if connection parameters are available."""
        return self._connected and bool(self.url and self.key)