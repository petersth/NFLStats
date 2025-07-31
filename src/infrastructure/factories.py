# src/infrastructure/factories.py - Factory functions for dependency creation

import logging
from typing import Optional

from .database.supabase_client import SupabaseClient
from .database.query_executor import SupabaseQueryExecutor
from .database.repositories.aggregated_stats_repository import AggregatedStatsRepository
from .data.unified_nfl_repository import UnifiedNFLRepository, DatabaseStrategy, InMemoryStrategy
from .cache.league_stats_cache import LeagueStatsCache
from .cache.cache_config import CacheConfig
from ..domain.nfl_stats_calculator import NFLStatsCalculator
from ..domain.services import ConfigurationService, SeasonService

logger = logging.getLogger(__name__)


def create_calculation_orchestrator(config: Optional[CacheConfig] = None):
    """Create calculation orchestrator with all dependencies."""
    from ..domain.orchestration import CalculationOrchestrator
    
    # Create core services
    stats_calculator = NFLStatsCalculator()
    config_service = ConfigurationService()
    
    # Create data repository with fallback
    data_repository = create_data_repository(config_service)
    
    # Create league cache
    league_cache = create_league_cache(config, stats_calculator, config_service, data_repository)
    
    return CalculationOrchestrator(
        data_repository=data_repository,
        statistics_calculator=stats_calculator,
        league_cache=league_cache,
        configuration_service=config_service
    )


def create_data_repository(config_service: ConfigurationService):
    """Create unified data repository with appropriate storage strategy."""
    try:
        # Try to create database-backed strategy first
        connection = create_database_connection()
        query_executor = SupabaseQueryExecutor(connection)
        
        # Try to get aggregated repository for optimization
        aggregated_repo = None
        try:
            aggregated_repo = AggregatedStatsRepository(query_executor)
            logger.info("Aggregated repository available for performance optimization")
        except Exception as agg_error:
            logger.warning(f"Aggregated repository not available: {agg_error}")
        
        # Create database strategy
        storage_strategy = DatabaseStrategy(query_executor, aggregated_repo)
        logger.info("Using database-backed storage strategy")
        
    except Exception as e:
        # If database setup fails, fall back to in-memory strategy
        logger.warning(f"Database setup failed, using in-memory strategy: {e}")
        storage_strategy = InMemoryStrategy()
        logger.info("Using in-memory storage strategy (direct NFL API)")
    
    # Return unified repository with selected strategy
    return UnifiedNFLRepository(config_service, storage_strategy)


def create_database_connection():
    """Create database connection."""
    try:
        client = SupabaseClient()
        client.connect()
        return client
    except ValueError as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Please ensure SUPABASE_URL and SUPABASE_KEY environment variables are set")
        raise


def create_league_cache(config: Optional[CacheConfig], stats_calculator: NFLStatsCalculator, 
                       config_service: ConfigurationService, data_repository) -> LeagueStatsCache:
    """Create league stats cache with explicit dependencies."""
    if config is None:
        config = CacheConfig()
    
    # Simple choice: database or NFL library
    use_database = config.should_use_database()
    
    # Create appropriate repository based on use_database flag
    if use_database:
        # Use the provided repository (which has DatabaseStrategy)
        nfl_data_repo = data_repository
        # Try to get aggregated repo
        aggregated_repo = None
        try:
            connection = create_database_connection()
            aggregated_repo = AggregatedStatsRepository(SupabaseQueryExecutor(connection))
        except Exception as e:
            logger.warning(f"Aggregated repository not available for cache: {e}")
    else:
        # Create a new repository with InMemoryStrategy for fresh data
        logger.info("Creating UnifiedNFLRepository with InMemoryStrategy for fresh data mode")
        nfl_data_repo = UnifiedNFLRepository(config_service, InMemoryStrategy())
        aggregated_repo = None
    
    return LeagueStatsCache(
        aggregated_repo=aggregated_repo,
        nfl_data_repo=nfl_data_repo,
        statistics_calculator=stats_calculator,
        config_service=config_service,
        use_database=use_database
    )


def create_core_services():
    """Create core domain services."""
    return {
        'config_service': ConfigurationService(),
        'season_service': SeasonService(),
        'stats_calculator': NFLStatsCalculator()
    }


# Convenience function for getting a configured cache with specific settings
def get_configured_cache(config: Optional[CacheConfig] = None) -> LeagueStatsCache:
    """Get a configured cache instance with specific config."""
    stats_calculator = NFLStatsCalculator()
    config_service = ConfigurationService()
    data_repository = create_data_repository(config_service)
    return create_league_cache(config, stats_calculator, config_service, data_repository)