# src/presentation/streamlit/controllers/team_analysis_controller.py - Team analysis controller

import logging
from typing import Optional, Dict

from ....domain.entities import Team, Season
from ....domain.orchestration import CalculationOrchestrator
from ....utils import ranking_utils
from ....domain.validation import NFLValidator
from ....domain.exceptions import DataNotFoundError, UseCaseError, DataValidationError
from ....application.dto import TeamAnalysisRequest, TeamAnalysisResponse
from ....domain.services import get_data_status
from ....infrastructure.factories import create_calculation_orchestrator
from ....config.nfl_constants import PROGRESS_MILESTONES

logger = logging.getLogger(__name__)


class TeamAnalysisController:
    """Streamlit controller for team analysis.
    
    Handles team analysis requests from the UI with direct orchestration.
    """
    
    def __init__(self, calculation_orchestrator: CalculationOrchestrator = None):
        """Initialize controller with orchestrator."""
        if calculation_orchestrator:
            self._orchestrator = calculation_orchestrator
        else:
            self._orchestrator = create_calculation_orchestrator()
    
    def analyze_team(self, request: TeamAnalysisRequest, progress_callback = None) -> TeamAnalysisResponse:
        """Execute team analysis with progress tracking."""
        
        # Validate inputs
        self._validate_request(request)
        
        try:
            if progress_callback:
                progress_callback.update(PROGRESS_MILESTONES['validation_start'], "Validating request...")
            
            # Parse validated inputs
            team = Team.from_abbreviation(request.team_abbreviation)
            season = Season(request.season_year)
            
            if progress_callback:
                progress_callback.update(PROGRESS_MILESTONES['orchestration_start'], "Orchestrating data sources...")
            
            # Orchestrator handles all the complexity of data source selection
            analysis = self._orchestrator.calculate_team_analysis(
                team=team,
                season=season,
                season_type_filter=request.season_type_filter,
                configuration=request.configuration,
                progress_callback=progress_callback
            )
            
            if progress_callback:
                progress_callback.update(PROGRESS_MILESTONES['rankings_calculation'], "Calculating rankings...")
            
            rankings = {
                metric: ranking_utils.calculate_performance_rank(
                    rank, analysis.league_team_count
                )
                for metric, rank in analysis.raw_rankings.items()
                if isinstance(rank, int) and rank > 0
            }

            if progress_callback:
                progress_callback.update(PROGRESS_MILESTONES['finalization'], "Finalizing analysis...")
            
            if progress_callback:
                progress_callback.update(1.0, "Analysis complete!")
            
            return TeamAnalysisResponse(
                team=team,
                season=season,
                season_stats=analysis.season_stats,
                game_stats=analysis.game_stats,
                team_record=analysis.team_record,
                rankings=rankings,
                league_averages=analysis.league_averages
            )
            
        except (DataNotFoundError, DataValidationError, UseCaseError):
            raise
        except Exception as e:
            logger.error(f"Team analysis failed for {request.team_abbreviation} {request.season_year}: {e}")
            raise UseCaseError(f"Analysis failed: {str(e)}", "team_analysis", {
                "team": request.team_abbreviation,
                "season": request.season_year
            }) from e
    
    def _validate_request(self, request: TeamAnalysisRequest) -> None:
        """Validate the analysis request."""
        if not request:
            raise DataValidationError("TeamAnalysisRequest cannot be None", "request", request)
        
        NFLValidator.validate_season_year(request.season_year, "season_year")
        NFLValidator.validate_team_abbreviation(request.team_abbreviation, "team_abbreviation")
        
        if request.season_type_filter:
            NFLValidator.validate_season_type(request.season_type_filter, "season_type_filter")
        
        if request.configuration:
            NFLValidator.validate_configuration(request.configuration, "configuration")
    
class LeagueStatsController:
    """Controller for league-wide statistics."""
    
    def __init__(self, calculation_orchestrator: CalculationOrchestrator = None):
        """Initialize controller with orchestrator."""
        if calculation_orchestrator:
            self._orchestrator = calculation_orchestrator
        else:
            self._orchestrator = create_calculation_orchestrator()
    
    def get_league_stats(self, season_year: int, season_type_filter: Optional[str] = None, configuration: Optional[Dict] = None) -> Dict:
        """Get league-wide statistics using orchestration."""
        
        # Validate inputs
        NFLValidator.validate_season_year(season_year, "season_year")
        if season_type_filter:
            NFLValidator.validate_season_type(season_type_filter, "season_type_filter")
        if configuration:
            NFLValidator.validate_configuration(configuration, "configuration")
        
        try:
            # Use the league cache to get or compute league stats
            config_hash = self._orchestrator.league_cache.get_config_hash(configuration or {})
            team_stats_dict, league_averages, timestamp = self._orchestrator.league_cache.get_or_compute_league_stats(
                season_year, season_type_filter, config_hash, configuration or {}
            )
            
            # Return league statistics
            return {
                'team_stats': team_stats_dict,
                'league_averages': league_averages,
                'timestamp': timestamp,
                'total_teams': len(team_stats_dict)
            }
            
        except Exception as e:
            logger.error(f"League stats calculation failed for {season_year}: {e}")
            raise UseCaseError(f"League stats calculation failed: {str(e)}", "league_stats", {
                "season": season_year
            })
