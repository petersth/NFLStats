# src/infrastructure/frameworks/streamlit_utils.py - Streamlit framework utilities


import streamlit as st
from typing import Any, Dict, Optional, Callable, TypeVar, Tuple
from datetime import timedelta, datetime


T = TypeVar('T')


class StreamlitAdapter:
    """Consolidated Streamlit adapter providing all framework-specific functionality."""
    
    def __init__(self):
        # Initialize all functionality in one place
        self.cache = StreamlitCacheAdapter()
        self.state = StreamlitStateAdapter() 
        self.notifications = StreamlitNotificationAdapter()
        self.app_state = StreamlitApplicationStateAdapter(self.state)
        
        # Initialize application state
        self.app_state.init()


class StreamlitCacheAdapter:
    """Streamlit session state based cache implementation."""
    
    def __init__(self, prefix: str = "cache_"):
        self.prefix = prefix
    
    def _get_key(self, key: str) -> str:
        return f"{self.prefix}{key}"
    
    def get(self, key: str) -> Optional[T]:
        cache_key = self._get_key(key)
        if cache_key in st.session_state:
            cache_entry = st.session_state[cache_key]
            
            # Check TTL if present
            if isinstance(cache_entry, dict) and 'expires_at' in cache_entry:
                if datetime.now() > cache_entry['expires_at']:
                    self.delete(key)
                    return None
                return cache_entry['value']
            
            return cache_entry
        return None
    
    def set(self, key: str, value: T, ttl: Optional[timedelta] = None) -> None:
        cache_key = self._get_key(key)
        
        if ttl:
            cache_entry = {
                'value': value,
                'expires_at': datetime.now() + ttl,
                'created_at': datetime.now()
            }
            st.session_state[cache_key] = cache_entry
        else:
            st.session_state[cache_key] = value
    
    def delete(self, key: str) -> None:
        cache_key = self._get_key(key)
        if cache_key in st.session_state:
            del st.session_state[cache_key]
    
    def clear(self, pattern: Optional[str] = None) -> None:
        if pattern:
            pattern_key = self._get_key(pattern)
            keys_to_remove = [key for key in st.session_state.keys() 
                            if key.startswith(self.prefix) and pattern in key]
        else:
            keys_to_remove = [key for key in st.session_state.keys() 
                            if key.startswith(self.prefix)]
        
        for key in keys_to_remove:
            del st.session_state[key]
    
    def exists(self, key: str) -> bool:
        return self.get(key) is not None
    
    def get_or_compute(self, key: str, compute_fn: Callable[[], T], 
                      ttl: Optional[timedelta] = None) -> T:
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value
        
        computed_value = compute_fn()
        self.set(key, computed_value, ttl)
        return computed_value


class StreamlitStateAdapter:
    """Streamlit session state implementation."""
    
    def get(self, key: str, default: Any = None) -> Any:
        return st.session_state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        st.session_state[key] = value
    
    def delete(self, key: str) -> None:
        if key in st.session_state:
            del st.session_state[key]
    
    def exists(self, key: str) -> bool:
        return key in st.session_state
    
    def clear(self) -> None:
        keys_to_remove = [key for key in st.session_state.keys() 
                         if not key.startswith('_')]
        for key in keys_to_remove:
            del st.session_state[key]
    
    def get_all_keys(self) -> list[str]:
        return [key for key in st.session_state.keys() 
                if not key.startswith('_')]


class StreamlitApplicationStateAdapter:
    """Streamlit-specific application state management."""
    
    # State key constants
    ANALYSIS_COMPLETE = "analysis_complete"
    CURRENT_ANALYSIS = "current_analysis" 
    CURRENT_TEAM = "current_team"
    CURRENT_SEASON = "current_season"
    CURRENT_SEASON_TYPE = "current_season_type"
    ANALYZED_TEAM = "analyzed_team"
    ANALYZED_SEASON = "analyzed_season"
    ANALYZED_SEASON_TYPE = "analyzed_season_type"
    ANALYZED_CACHE_NFL_DATA = "analyzed_cache_nfl_data"
    PREVIOUS_CONFIG = "previous_config"
    
    def __init__(self, state_manager):
        self.state = state_manager
    
    def init(self) -> None:
        defaults = {
            self.ANALYSIS_COMPLETE: False,
            self.CURRENT_ANALYSIS: None,
            self.CURRENT_TEAM: None,
            self.CURRENT_SEASON: None,
            self.CURRENT_SEASON_TYPE: None,
            self.ANALYZED_TEAM: None,
            self.ANALYZED_SEASON: None,
            self.ANALYZED_SEASON_TYPE: None,
            self.ANALYZED_CACHE_NFL_DATA: None,
            self.PREVIOUS_CONFIG: None,
        }
        
        for key, default_value in defaults.items():
            if not self.state.exists(key):
                self.state.set(key, default_value)
    
    def reset_analysis(self) -> None:
        self.state.set(self.ANALYSIS_COMPLETE, False)
        self.state.set(self.CURRENT_ANALYSIS, None)
    
    def is_analysis_complete(self) -> bool:
        return self.state.get(self.ANALYSIS_COMPLETE, False)
    
    def get_current_analysis(self) -> Any:
        return self.state.get(self.CURRENT_ANALYSIS)
    
    def set_analysis_complete(self, analysis_response: Any) -> None:
        self.state.set(self.CURRENT_ANALYSIS, analysis_response)
        self.state.set(self.ANALYSIS_COMPLETE, True)
    
    def set_current_selections(self, team: str, season: int, season_type: str) -> None:
        self.state.set(self.CURRENT_TEAM, team)
        self.state.set(self.CURRENT_SEASON, season)
        self.state.set(self.CURRENT_SEASON_TYPE, season_type)
    
    def get_current_selections(self) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        return (
            self.state.get(self.CURRENT_TEAM),
            self.state.get(self.CURRENT_SEASON),
            self.state.get(self.CURRENT_SEASON_TYPE)
        )
    
    def set_analyzed_selections(
        self,
        team: str,
        season: int,
        season_type: str,
        cache_nfl_data: Optional[bool] = None,
    ) -> None:
        self.state.set(self.ANALYZED_TEAM, team)
        self.state.set(self.ANALYZED_SEASON, season)
        self.state.set(self.ANALYZED_SEASON_TYPE, season_type)
        self.state.set(self.ANALYZED_CACHE_NFL_DATA, cache_nfl_data)
    
    def get_analyzed_selections(self) -> Tuple[str, int, str]:
        return (
            self.state.get(self.ANALYZED_TEAM),
            self.state.get(self.ANALYZED_SEASON),
            self.state.get(self.ANALYZED_SEASON_TYPE)
        )

    def get_analyzed_cache_mode(self) -> Optional[bool]:
        """Return the cache mode used for the displayed analysis."""
        return self.state.get(self.ANALYZED_CACHE_NFL_DATA)
    
    def check_config_changed(self, current_config: Dict) -> bool:
        previous_config = self.state.get(self.PREVIOUS_CONFIG)
        
        # First time or no previous config - not a change
        if previous_config is None:
            self.state.set(self.PREVIOUS_CONFIG, current_config.copy())
            return False
        
        # No analysis completed yet - not a change
        if not self.is_analysis_complete():
            self.state.set(self.PREVIOUS_CONFIG, current_config.copy())
            return False
        
        # Use stable hash-based comparison instead of direct dict comparison
        # This prevents false positives from dict ordering or object reference changes
        prev_hash = self._get_config_hash(previous_config)
        curr_hash = self._get_config_hash(current_config)
        config_changed = prev_hash != curr_hash

        self.state.set(self.PREVIOUS_CONFIG, current_config.copy())
        return config_changed
    
    def _get_config_hash(self, config: Dict) -> str:
        """Generate a stable hash for configuration comparison.
        
        Creates a deterministic hash that remains consistent across sessions
        by normalizing nested dictionaries, sorting keys, and handling data types
        consistently to enable reliable configuration change detection.
        """
        from ...utils.config_hasher import get_config_hash
        return get_config_hash(config)
    
    def get_debug_info(self) -> Dict[str, Any]:
        return {
            'analysis_complete': self.is_analysis_complete(),
            'current_selections': self.get_current_selections(),
            'has_analysis_data': self.get_current_analysis() is not None,
            'total_session_keys': len(self.state.get_all_keys())
        }


class StreamlitNotificationAdapter:
    """Streamlit notification implementation."""
    
    def success(self, message: str) -> None:
        st.success(message)
    
    def error(self, message: str) -> None:
        st.error(message)
    
    def warning(self, message: str) -> None:
        st.warning(message)
    
    def info(self, message: str) -> None:
        st.info(message)
