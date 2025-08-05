# src/infrastructure/factories.py - Factory functions for dependency creation

import logging
from typing import Optional

from .data.unified_nfl_repository import UnifiedNFLRepository
from .cache.league_stats_cache import LeagueStatsCache
from ..domain.nfl_stats_calculator import NFLStatsCalculator

logger = logging.getLogger(__name__)


def create_calculation_orchestrator():
    """Create calculation orchestrator with all dependencies."""
    from ..domain.orchestration import CalculationOrchestrator
    
    # Create core services
    stats_calculator = NFLStatsCalculator()
    
    # Create data repository (direct NFL API with in-memory caching)
    logger.info("Using in-memory storage strategy (direct NFL API)")
    data_repository = UnifiedNFLRepository()
    
    # Create league cache
    league_cache = LeagueStatsCache(
        nfl_data_repo=data_repository,
        statistics_calculator=stats_calculator
    )
    
    return CalculationOrchestrator(
        statistics_calculator=stats_calculator,
        league_cache=league_cache
    )



def create_core_services():
    """Create core domain services."""
    return {
        'stats_calculator': NFLStatsCalculator()
    }


def get_configured_cache() -> LeagueStatsCache:
    """Get a configured cache instance using NFL API."""
    stats_calculator = NFLStatsCalculator()
    
    # Create data repository (direct NFL API with in-memory caching)
    logger.info("Using in-memory storage strategy (direct NFL API)")
    data_repository = UnifiedNFLRepository()
    
    return LeagueStatsCache(
        nfl_data_repo=data_repository,
        statistics_calculator=stats_calculator
    )