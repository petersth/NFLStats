# src/infrastructure/frameworks/streamlit_utils.py - Streamlit framework utilities


import streamlit as st
import logging
from typing import Any, Dict, Optional, Callable, TypeVar, Tuple
from datetime import timedelta, datetime
from functools import wraps


logger = logging.getLogger(__name__)
T = TypeVar('T')


class StreamlitAdapter:
    """Consolidated Streamlit adapter providing all framework-specific functionality."""
    
    def __init__(self):
        # Initialize all functionality in one place
        self.cache = StreamlitCacheAdapter()
        self.session_cache = StreamlitSessionCacheAdapter()
        self.state = StreamlitStateAdapter() 
        self.notifications = StreamlitNotificationAdapter()
        self.app_state = StreamlitApplicationStateAdapter(self.state)
        
        # Initialize application state
        self.app_state.init()
    
    def create_progress_adapter(self, progress_bar=None, status_text=None) -> 'StreamlitProgressAdapter':
        """Create a progress adapter instance."""
        return StreamlitProgressAdapter(progress_bar, status_text)
    


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


class StreamlitSessionCacheAdapter:
    """Adapter for Streamlit's built-in caching mechanisms."""
    
    def cached_data(self, key: str, ttl: Optional[timedelta] = None, 
                   show_spinner: bool = True) -> Callable:
        def decorator(func: Callable) -> Callable:
            ttl_seconds = int(ttl.total_seconds()) if ttl else None
            
            cached_func = st.cache_data(
                ttl=ttl_seconds,
                show_spinner=show_spinner,
                hash_funcs=None
            )(func)
            
            return cached_func
        return decorator
    
    def invalidate_cache(self, key: str) -> None:
        logger.warning("Streamlit cache doesn't support selective invalidation by key")
        st.cache_data.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        return {
            'type': 'streamlit_cache_data',
            'selective_invalidation': False,
            'introspection_available': False
        }


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
    PREVIOUS_CONFIG = "previous_config"
    TABS_LOADED = "tabs_loaded"
    
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
            self.PREVIOUS_CONFIG: None,
            self.TABS_LOADED: {
                'game_log': False,
                'trends': False, 
                'league': False,
                'export': False,
                'methodology': False
            }
        }
        
        for key, default_value in defaults.items():
            if not self.state.exists(key):
                self.state.set(key, default_value)
    
    def reset_analysis(self) -> None:
        self.state.set(self.ANALYSIS_COMPLETE, False)
        self.state.set(self.CURRENT_ANALYSIS, None)
        self.state.set(self.TABS_LOADED, {
            'game_log': False,
            'trends': False,
            'league': False, 
            'export': False,
            'methodology': False
        })
    
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
    
    def set_analyzed_selections(self, team: str, season: int, season_type: str) -> None:
        self.state.set(self.ANALYZED_TEAM, team)
        self.state.set(self.ANALYZED_SEASON, season)
        self.state.set(self.ANALYZED_SEASON_TYPE, season_type)
    
    def get_analyzed_selections(self) -> Tuple[str, int, str]:
        return (
            self.state.get(self.ANALYZED_TEAM),
            self.state.get(self.ANALYZED_SEASON),
            self.state.get(self.ANALYZED_SEASON_TYPE)
        )
    
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
        """Generate a stable hash for configuration comparison."""
        from ...utils.config_hasher import get_config_hash
        return get_config_hash(config)
    
    def should_analyze(self, analyze_button: bool, config_changed: bool, 
                      team: str, season: int, season_type: str) -> bool:
        current_team, current_season, current_season_type = self.get_current_selections()
        
        return (
            analyze_button or 
            config_changed or
            (not self.is_analysis_complete() and
             current_team == team and
             current_season == season and  
             current_season_type == season_type)
        )
    
    def get_tabs_loaded(self) -> Dict[str, bool]:
        return self.state.get(self.TABS_LOADED, {})
    
    def set_tab_loaded(self, tab_name: str) -> None:
        tabs_loaded = self.get_tabs_loaded()
        tabs_loaded[tab_name] = True
        self.state.set(self.TABS_LOADED, tabs_loaded)
    
    def is_tab_loaded(self, tab_name: str) -> bool:
        return self.get_tabs_loaded().get(tab_name, False)
    
    def get_debug_info(self) -> Dict[str, Any]:
        return {
            'analysis_complete': self.is_analysis_complete(),
            'current_selections': self.get_current_selections(),
            'tabs_loaded': self.get_tabs_loaded(),
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


class StreamlitProgressAdapter:
    """Streamlit progress tracking implementation."""
    
    def __init__(self, progress_bar=None, status_text=None):
        self.progress_bar = progress_bar or st.progress(0)
        self.status_text = status_text or st.empty()
        self.current_progress = 0.0
    
    def update(self, progress: float, message: str) -> None:
        self.current_progress = max(0.0, min(1.0, progress))
        self.progress_bar.progress(self.current_progress)
        self.status_text.text(message)
    
    def stage(self, stage_name: str) -> 'StreamlitProgressStage':
        return StreamlitProgressStage(self, stage_name)


class StreamlitProgressStage:
    """Streamlit progress stage implementation."""
    
    def __init__(self, parent: StreamlitProgressAdapter, stage_name: str):
        self.parent = parent
        self.stage_name = stage_name
        self.stage_start_progress = parent.current_progress
    
    def update(self, progress: float, message: str) -> None:
        stage_message = f"{self.stage_name}: {message}"
        self.parent.update(progress, stage_message)
    
    def __enter__(self) -> 'StreamlitProgressStage':
        self.update(0.0, "Starting...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.update(1.0, "Complete")
        else:
            self.update(1.0, "Failed")


