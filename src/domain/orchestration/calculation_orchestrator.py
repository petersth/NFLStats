# src/domain/orchestration/calculation_orchestrator.py - Clean orchestration of data sources

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd

from ..entities import Team, Season, SeasonStats, GameStats, TeamRecord
from ..exceptions import DataNotFoundError
from ...utils.configuration_utils import apply_configuration_to_data

logger = logging.getLogger(__name__)


class CalculationOrchestrator:
    """Orchestrates NFL team analysis using fresh data from NFL API with in-memory caching.
    
    Simplified single-strategy approach:
    - Downloads fresh data from NFL API
    - Caches in memory for session performance 
    - Uses consistent calculation logic throughout
    """
    
    def __init__(
        self,
        statistics_calculator,  # NFLStatsCalculator - concrete class
        league_cache,  # LeagueStatsCache - concrete class
    ):
        self._statistics_calculator = statistics_calculator
        self._league_cache = league_cache
    
    @property
    def league_cache(self):
        """Provide access to league cache for rankings calculation."""
        return self._league_cache
    
    @property
    def statistics_calculator(self):
        """Provide access to statistics calculator."""
        return self._statistics_calculator
    
    def calculate_team_analysis(
        self, 
        team: Team, 
        season: Season,
        season_type_filter: Optional[str] = None,
        configuration: Optional[Dict] = None,
        progress_callback = None
    ) -> Tuple[SeasonStats, List[GameStats], Optional[TeamRecord]]:
        """Calculate complete team analysis using fresh NFL data with caching.
        
        Returns:
            Tuple of (season_stats, game_stats, team_record)
        """
        logger.info(f"Calculating analysis for {team.abbreviation} {season.year} using fresh NFL data")
        
        if progress_callback:
            progress_callback.update(0.1, "Loading fresh NFL data...")
        
        return self._calculate_from_fresh_nfl(team, season, season_type_filter, configuration, progress_callback)
    
    
    def _calculate_from_fresh_nfl(
        self, 
        team: Team, 
        season: Season,
        season_type_filter: Optional[str],
        configuration: Optional[Dict],
        progress_callback = None
    ) -> Tuple[SeasonStats, List[GameStats], Optional[TeamRecord]]:
        """Calculate using fresh NFL data (with optional session caching)."""
        
        try:
            if progress_callback:
                progress_callback.update(0.3, "Loading from NFL API...")
            
            # Use league cache which has InMemoryStrategy repository
            config_hash = self._league_cache.get_config_hash(configuration or {})
            team_stats_dict, _, _ = self._league_cache.get_or_compute_league_stats(
                season.year, season_type_filter, config_hash,
                None, self._statistics_calculator, configuration or {}, progress_callback
            )
            
            if team.abbreviation not in team_stats_dict:
                # Check if this is specifically a playoff selection issue
                if season_type_filter == 'POST':
                    from ...config.nfl_constants import TEAM_DATA
                    team_name = TEAM_DATA.get(team.abbreviation, {}).get('name', team.abbreviation)
                    raise DataNotFoundError(
                        f"{team_name} did not make the playoffs in {season.year}. "
                        f"Try selecting 'Regular Season' or 'All Games' instead."
                    )
                else:
                    logger.warning(f"Team {team.abbreviation} not found in fresh NFL data")
                    return self._create_empty_results(team, season)
            
            season_stats = team_stats_dict[team.abbreviation]
            
            if progress_callback:
                progress_callback.update(0.8, "Computing game stats from fresh data...")
            
            # Get game stats from the cached raw data (avoids re-fetching from NFL API)
            # Always get ALL games for team record calculation
            all_games_data = self._league_cache.get_cached_play_data(season.year, 'ALL', configuration or {})
            if all_games_data is not None:
                complete_team_data = all_games_data[all_games_data['posteam'] == team.abbreviation].copy()
                
                # Calculate team record using complete data (always show full season record)
                team_record = self._statistics_calculator.calculate_team_record(complete_team_data, team.abbreviation)
                
                # Apply filters for stats calculations
                filtered_team_data = complete_team_data.copy()
                if season_type_filter and season_type_filter != 'ALL':
                    filtered_team_data = filtered_team_data[filtered_team_data['season_type'] == season_type_filter]
                if configuration:
                    filtered_team_data = apply_configuration_to_data(filtered_team_data, configuration)
                
                game_stats = self._statistics_calculator.calculate_game_stats(filtered_team_data, team)
                
                return season_stats, game_stats, team_record
            else:
                logger.warning("No play data available for game stats from league cache repository")
                return season_stats, [], None
                
        except DataNotFoundError:
            # Re-raise DataNotFoundError so UI can handle it properly
            raise
        except Exception as e:
            logger.error(f"Fresh NFL calculation failed: {e}")
            return self._create_empty_results(team, season)
    
    def _create_empty_results(self, team: Team, season: Season) -> Tuple[SeasonStats, List[GameStats], Optional[TeamRecord]]:
        """Create empty results for error cases."""
        from ..entities import SeasonStats
        
        empty_season_stats = SeasonStats(
            team=team,
            season=season,
            games_played=0,
            avg_yards_per_play=0.0,
            total_yards=0,
            total_plays=0,
            turnovers_per_game=0.0,
            completion_pct=0.0,
            rush_ypc=0.0,
            sacks_per_game=0.0,
            third_down_pct=0.0,
            success_rate=0.0,
            first_downs_per_game=0.0,
            points_per_drive=0.0,
            redzone_td_pct=0.0,
            penalty_yards_per_game=0.0,
            toer=0.0
        )
        
        return empty_season_stats, [], None