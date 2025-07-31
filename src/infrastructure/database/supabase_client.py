# src/infrastructure/database/supabase_client.py

import logging
from typing import Dict, Optional, Any
from datetime import datetime

from ...domain.interfaces.database import DatabaseConnectionInterface
from .supabase_base import SupabaseConnectionBase

logger = logging.getLogger(__name__)


class SupabaseClient(DatabaseConnectionInterface, SupabaseConnectionBase):
    """Supabase client for raw play data storage."""
    
    def __init__(self, url: str = None, key: str = None):
        import os
        
        # Try to get credentials from multiple sources
        self.url = url or self._get_credential('SUPABASE_URL', 'supabase_url')
        self.key = key or self._get_credential('SUPABASE_KEY', 'supabase_key')
        
        # Validate that required credentials are provided
        if not self.url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self.key:
            raise ValueError("SUPABASE_KEY environment variable is required")
        
        # Basic validation of URL format
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError("SUPABASE_URL must be a valid HTTP/HTTPS URL")
        
        # Basic validation of key format (JWT tokens typically start with 'eyJ')
        if not self.key.startswith('eyJ'):
            raise ValueError("SUPABASE_KEY appears to be invalid (should be a JWT token)")
        
        # Initialize base class with credentials
        SupabaseConnectionBase.__init__(self, self.url, self.key)
        
        # Log safely without exposing credentials
        masked_url = f"{self.url.split('/')[0]}//{self.url.split('/')[2]}/*****"
        logger.info(f"Initialized Supabase client for URL: {masked_url}")
    
    def _get_credential(self, env_var: str, streamlit_key: str) -> str:
        """Get credential from environment variables or Streamlit secrets."""
        import os
        
        # First try environment variable
        value = os.getenv(env_var)
        if value:
            return value
        
        # Then try Streamlit secrets
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and streamlit_key in st.secrets:
                return st.secrets[streamlit_key]
        except (ImportError, AttributeError, KeyError):
            pass
        
        return None
    
    def connect(self) -> bool:
        """Connect to Supabase with validation."""
        try:
            # Validate credentials are still present
            if not self.url or not self.key:
                logger.error("Missing Supabase credentials")
                return False
            
            # Test actual connectivity
            if not self.test_connection():
                logger.error("Failed to establish connection to Supabase")
                return False
            
            self._connected = True
            logger.info("Successfully connected to Supabase")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Supabase."""
        self._connected = False
        logger.info("Disconnected from Supabase")
    
    def is_connected(self) -> bool:
        """Check if connected to Supabase."""
        return self._connected
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            import requests
            url = f"{self.url}/rest/v1/"
            headers = {
                'apikey': self.key,
                'Authorization': f'Bearer {self.key}'
            }
            response = requests.get(url, headers=headers, timeout=5)
            return response.status_code < 500
        except Exception:
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information (delegates to base class)."""
        return SupabaseConnectionBase.get_connection_info(self)
