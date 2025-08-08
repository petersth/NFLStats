# src/infrastructure/cache/simple_cache.py - Simple cache implementation

import time
import logging
from typing import TypeVar, Optional, Dict, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)
T = TypeVar('T')


@dataclass
class CacheEntry:
    """Represents a cached value with metadata."""
    value: Any
    created_at: float
    access_count: int = 0
    last_accessed: float = 0.0
    ttl: Optional[float] = None
    
    def __post_init__(self):
        if self.last_accessed == 0.0:
            self.last_accessed = self.created_at
    
    def is_expired(self, default_ttl: Optional[float] = None) -> bool:
        """Check if entry is expired based on TTL."""
        ttl = self.ttl if self.ttl is not None else default_ttl
        if ttl is None:
            return False
        return (time.time() - self.created_at) > ttl


class SimpleCache:
    """Simple cache with TTL support and LRU eviction."""
    
    def __init__(self, default_ttl: Optional[float] = None, max_size: Optional[int] = None):
        """
        Initialize simple cache.
        
        Args:
            default_ttl: Default time-to-live in seconds for cache entries
            max_size: Maximum number of entries (None for unlimited)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        logger.debug(f"Initialized cache (TTL: {default_ttl}s, max_size: {max_size})")
    
    def get(self, key: str, validator: Optional[Callable[[T], bool]] = None) -> Optional[T]:
        """
        Get value from cache with optional validation.
        
        Args:
            key: Cache key
            validator: Optional function to validate cached value
            
        Returns:
            Cached value if valid, None otherwise
        """
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        
        # Check TTL
        if entry.is_expired(self._default_ttl):
            del self._cache[key]
            self._misses += 1
            self._evictions += 1
            return None
        
        # Validate if validator provided
        if validator and not validator(entry.value):
            del self._cache[key]
            self._misses += 1
            self._evictions += 1
            return None
        
        # Update access statistics
        entry.access_count += 1
        entry.last_accessed = time.time()
        self._hits += 1
        
        return entry.value
    
    def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Custom TTL for this entry (overrides default)
        """
        # Check size limit and evict if necessary
        if self._max_size and len(self._cache) >= self._max_size and key not in self._cache:
            self._evict_lru()
        
        current_time = time.time()
        self._cache[key] = CacheEntry(
            value=value,
            created_at=current_time,
            last_accessed=current_time,
            ttl=ttl
        )
    
    def get_or_compute(self, key: str, compute_func: Callable[[], T], 
                       validator: Optional[Callable[[T], bool]] = None,
                       ttl: Optional[float] = None) -> T:
        """
        Get value from cache or compute it if not present.
        
        Args:
            key: Cache key
            compute_func: Function to compute value if not cached
            validator: Optional validator for cached value
            ttl: Custom TTL for computed value
            
        Returns:
            Cached or computed value
        """
        # Check cache first
        cached_value = self.get(key, validator)
        if cached_value is not None:
            return cached_value
        
        # Compute and cache
        try:
            computed_value = compute_func()
            self.set(key, computed_value, ttl)
            return computed_value
        except Exception as e:
            logger.error(f"Failed to compute value for key '{key}': {e}")
            raise
    
    def clear(self, key_pattern: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            key_pattern: If provided, only clear keys containing this pattern
            
        Returns:
            Number of entries cleared
        """
        if key_pattern is None:
            count = len(self._cache)
            self._cache.clear()
            self._evictions += count
            return count
        else:
            keys_to_remove = [k for k in self._cache.keys() if key_pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
            self._evictions += len(keys_to_remove)
            return len(keys_to_remove)
    
    def invalidate(self, key: str) -> bool:
        """
        Remove specific key from cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was present and removed
        """
        if key in self._cache:
            del self._cache[key]
            self._evictions += 1
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'evictions': self._evictions,
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests
        }
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]
        self._evictions += 1


# No more aliases needed - use SimpleCache directly