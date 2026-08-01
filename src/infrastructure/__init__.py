"""Infrastructure layer - external adapters and implementations."""

def get_configured_cache():
    """Create the configured cache without eagerly importing the dependency graph."""
    from .factories import get_configured_cache as create_cache

    return create_cache()
