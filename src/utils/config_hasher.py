# src/utils/config_hasher.py - Shared configuration hashing utility

import json
import hashlib
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigHasher:
    """Utility for generating consistent configuration hashes."""
    
    @staticmethod
    def get_config_hash(configuration: Dict[str, Any]) -> str:
        """
        Generate a stable hash for configuration dictionaries.
        
        Uses recursive normalization to ensure consistent hashing
        regardless of key/value order.
        """
        try:
            normalized = ConfigHasher._normalize_config(configuration)
            config_string = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
            return hashlib.md5(config_string.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to generate config hash: {e}")
            # Return a consistent fallback hash for error cases
            return hashlib.md5(str(configuration).encode()).hexdigest()
    
    @staticmethod
    def _normalize_config(obj: Any) -> Any:
        """
        Recursively normalize configuration objects for consistent hashing.
        
        - Sorts dictionary keys
        - Handles nested dictionaries and lists
        - Preserves data types
        """
        if isinstance(obj, dict):
            return {k: ConfigHasher._normalize_config(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [ConfigHasher._normalize_config(item) for item in obj]
        else:
            return obj
    
    @staticmethod 
    def get_simple_hash(configuration: Dict[str, Any]) -> str:
        """
        Generate a simple hash without normalization (for performance).
        
        Use this when you know the configuration structure is consistent
        and don't need deep normalization.
        """
        try:
            config_string = json.dumps(configuration, sort_keys=True)
            return hashlib.md5(config_string.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to generate simple config hash: {e}")
            return hashlib.md5(str(configuration).encode()).hexdigest()