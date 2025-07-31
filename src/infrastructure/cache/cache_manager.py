# src/infrastructure/cache/cache_manager.py - Caching infrastructure

from typing import Any, Optional, Callable
import streamlit as st


class StreamlitCacheManager:
    """Cache manager using Streamlit's built-in caching."""
    
    def get_or_compute(self, key: str, compute_func: Callable, *args, **kwargs) -> Any:
        """Get cached value or compute and cache it."""
        cached_func = st.cache_data(show_spinner=False)(compute_func)
        return cached_func(*args, **kwargs)
    
    def clear_cache(self, key: Optional[str] = None) -> None:
        """Clear cache (Streamlit handles this automatically)."""
        if key:
            # This would require a more sophisticated implementation
            pass
        else:
            st.cache_data.clear()