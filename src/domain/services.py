# src/domain/services.py - Core business logic services

from typing import Dict, Optional, List
from .entities import PerformanceRank, Season
from ..config import TOTAL_NFL_TEAMS


# RankingService converted to utility function in src/utils/ranking_utils.py


class SeasonService:
    """Service for season-related business logic."""
    
    def __init__(self):
        from ..config.nfl_constants import NFL_SEASON_START_MONTH, NFL_DATA_START_YEAR
        self.NFL_SEASON_START_MONTH = NFL_SEASON_START_MONTH
        self.NFL_DATA_START_YEAR = NFL_DATA_START_YEAR
    
    def get_current_nfl_season_info(self) -> Dict:
        """Get comprehensive current NFL season information."""
        from datetime import datetime
        
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        if current_month >= self.NFL_SEASON_START_MONTH:  # September or later
            current_season = current_year
            season_status = "in_progress"
        elif current_month <= 2:  # January-February (playoffs/Super Bowl)
            current_season = current_year - 1
            season_status = "playoffs" if current_month == 1 else "completed"
        else:  # March-August (offseason)
            current_season = current_year - 1
            season_status = "completed"

        expected_games = 17

        if season_status == "completed":
            data_complete = True
        elif season_status == "playoffs":
            data_complete = True
        else:  # in_progress
            data_complete = False
        
        return {
            'current_season': current_season,
            'season_status': season_status,
            'expected_games': expected_games,
            'data_complete': data_complete,
            'available_seasons': list(range(current_season, self.NFL_DATA_START_YEAR - 1, -1))
        }
    
    def get_season_context_message(self, season: Season, actual_games: Optional[int] = None) -> Dict[str, str]:
        """Get contextual message about the selected season."""
        season_info = self.get_current_nfl_season_info()
        
        if season.year == season_info['current_season']:
            if season_info['season_status'] == 'in_progress':
                if actual_games and actual_games < season_info['expected_games']:
                    return {
                        'message': f"{season.year} season in progress • {actual_games}/{season_info['expected_games']} games played",
                        'type': 'info'
                    }
                else:
                    return {'message': f"{season.year} season in progress", 'type': 'info'}
            elif season_info['season_status'] == 'playoffs':
                return {'message': f"{season.year} season: Playoffs in progress", 'type': 'info'}
            else:
                return {'message': f"{season.year} season: Complete", 'type': 'success'}
        elif season.year > season_info['current_season']:
            return {'message': f"{season.year} season hasn't started yet", 'type': 'warning'}
        else:
            return {'message': f"{season.year} season: Historical data", 'type': 'success'}


class ConfigurationService:
    """Service for managing statistics configuration."""
    
    def __init__(self):
        self.configurations = {
            'nfl_official': {
                'name': 'NFL Official',
                'description': 'Includes QB kneels (official NFL methodology)',
                'include_qb_kneels_rushing': True,
                'include_qb_kneels_success_rate': True
            },
            'analytics_clean': {
                'name': 'Analytics (Clean)',
                'description': 'Excludes QB kneels for pure efficiency metrics',
                'include_qb_kneels_rushing': False,
                'include_qb_kneels_success_rate': False
            },
            'custom': {
                'name': 'Custom',
                'description': 'User-defined QB kneel settings',
                'include_qb_kneels_rushing': True,
                'include_qb_kneels_success_rate': True
            }
        }
    
    def get_configuration(self, config_name: str) -> Dict:
        """Get configuration by name."""
        if config_name not in self.configurations:
            raise ValueError(f"Unknown configuration: {config_name}")
        return self.configurations[config_name].copy()
    
    def get_available_configurations(self) -> List[str]:
        """Get list of available configuration names."""
        return list(self.configurations.keys())
    
    def apply_configuration_to_data(self, data: 'pd.DataFrame', config: Dict) -> 'pd.DataFrame':
        """Apply configuration filtering to data."""
        import pandas as pd
        import logging
        
        logger = logging.getLogger(__name__)
        
        if len(data) == 0:
            return data
        
        # Safety check for None config
        if config is None:
            logger.warning("Configuration is None, using default settings")
            config = {}
        
        filtered_data = data.copy()
        
        # Apply QB kneel filtering based on configuration
        if 'play_type' in filtered_data.columns:
            qb_kneel_mask = filtered_data['play_type'] == 'qb_kneel'
            qb_kneels_exist = qb_kneel_mask.any()
            
            if qb_kneels_exist:
                include_rushing = config.get('include_qb_kneels_rushing', True)
                include_success_rate = config.get('include_qb_kneels_success_rate', True)
                
                # Apply filtering logic
                if not include_rushing and not include_success_rate:
                    filtered_data = filtered_data[~qb_kneel_mask]
                    logger.info(f"Removed {qb_kneel_mask.sum()} QB kneel plays from analysis")
                elif not include_rushing and include_success_rate:
                    # Filter QB kneels from rushing metrics but keep for success rate
                    # This requires context-aware filtering in the statistics calculator
                    # For now, we'll mark these plays for context-aware handling
                    filtered_data.loc[qb_kneel_mask, '_qb_kneel_context'] = 'exclude_rushing'
                    logger.info(f"Marked {qb_kneel_mask.sum()} QB kneel plays to exclude from rushing metrics only")
                elif include_rushing and not include_success_rate:
                    # Filter QB kneels from success rate but keep for rushing
                    filtered_data.loc[qb_kneel_mask, '_qb_kneel_context'] = 'exclude_success_rate'
                    logger.info(f"Marked {qb_kneel_mask.sum()} QB kneel plays to exclude from success rate only")
                # If both are True, keep all QB kneels (no filtering needed)
        
        return filtered_data


# SeasonFilterService converted to utility function in src/utils/season_filters.py