# src/domain/orchestration/calculation_orchestrator.py - Clean orchestration of data sources

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..entities import Team, Season, SeasonStats, GameStats, TeamRecord
from ..exceptions import DataNotFoundError
from ...utils.configuration_utils import apply_configuration_to_data

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrchestratedTeamAnalysis:
    """Complete calculation output, including its already-loaded league context."""

    season_stats: SeasonStats
    game_stats: List[GameStats]
    team_record: Optional[TeamRecord]
    raw_rankings: Dict[str, int]
    league_averages: Dict[str, float]
    league_team_count: int


class CalculationOrchestrator:
    """Orchestrates NFL team analysis using fresh nflverse data with in-memory caching.
    
    Simplified single-strategy approach:
    - Downloads fresh data from nflverse
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
    ) -> OrchestratedTeamAnalysis:
        """Calculate complete team analysis using fresh NFL data with caching.
        
        Returns:
            Complete team analysis with league comparison context.
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
    ) -> OrchestratedTeamAnalysis:
        """Calculate using fresh NFL data (with optional session caching)."""
        
        if progress_callback:
            progress_callback.update(0.3, "Loading from nflverse...")

        configuration = configuration or {}
        config_hash = self._league_cache.get_config_hash(configuration)
        snapshot = self._league_cache.get_or_compute_analysis_snapshot(
            season.year,
            season_type_filter,
            config_hash,
            configuration,
            progress_callback,
        )
        team_stats_dict = snapshot.team_stats

        if team.abbreviation not in team_stats_dict:
            from ...config.nfl_constants import TEAM_DATA

            team_name = TEAM_DATA.get(team.abbreviation, {}).get('name', team.abbreviation)
            if season_type_filter == 'POST':
                message = (
                    f"{team_name} did not make the playoffs in {season.year}. "
                    "Try selecting 'Regular Season' or 'All Games' instead."
                )
            else:
                message = f"No {season.year} data was found for {team_name}."
            raise DataNotFoundError(message, season.year, season_type_filter)

        season_stats = team_stats_dict[team.abbreviation]
        cache_key = self._league_cache.get_cache_key(
            season.year, season_type_filter, config_hash
        )
        raw_rankings = self._league_cache.get_team_rankings(
            team.abbreviation, team_stats_dict, cache_key
        )
        if progress_callback:
            progress_callback.update(0.8, "Preparing game statistics...")

        # Records and game metadata must describe the same source as the cached
        # aggregates, even if the repository has since expired or refreshed.
        all_games_data = snapshot.complete_pbp_data
        complete_team_data = all_games_data[
            all_games_data['posteam'] == team.abbreviation
        ].copy()
        team_record = self._statistics_calculator.calculate_team_record(
            complete_team_data, team.abbreviation
        )

        analysis_data = all_games_data
        if season_type_filter and season_type_filter != 'ALL':
            analysis_data = analysis_data[
                analysis_data['season_type'] == season_type_filter
            ].copy()
        if configuration:
            analysis_data = apply_configuration_to_data(analysis_data, configuration)

        game_stats = self._statistics_calculator.calculate_game_stats_with_toer_allowed(
            analysis_data,
            team,
            game_results=snapshot.game_results,
        )
        return OrchestratedTeamAnalysis(
            season_stats=season_stats,
            game_stats=game_stats,
            team_record=team_record,
            raw_rankings=raw_rankings,
            league_averages=snapshot.league_averages,
            league_team_count=len(team_stats_dict),
        )
