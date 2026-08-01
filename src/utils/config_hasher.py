# src/utils/config_hasher.py - Configuration hashing utility functions

import json
import hashlib
from typing import Dict, Any


def get_config_hash(configuration: Dict[str, Any]) -> str:
    """
    Generate a stable hash for configuration dictionaries.
    
    Uses recursive normalization to ensure consistent hashing
    regardless of key/value order.
    """
    normalized = _normalize_config(configuration)
    config_string = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(config_string.encode()).hexdigest()


def _normalize_config(obj: Any) -> Any:
    """
    Recursively normalize configuration objects for consistent hashing.
    
    - Sorts dictionary keys
    - Handles nested dictionaries and lists
    - Preserves data types
    """
    if isinstance(obj, dict):
        return {k: _normalize_config(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [_normalize_config(item) for item in obj]
    else:
        return obj
