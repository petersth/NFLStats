# src/presentation/streamlit/controllers/team_analysis_controller.py - Team analysis controller

import logging
from typing import Optional, Dict
from datetime import datetime
import pandas as pd

from ....domain.entities import Team, Season
from ....domain.orchestration import CalculationOrchestrator
from ....utils import ranking_utils
from ....domain.validation import NFLValidator
from ....domain.exceptions import UseCaseError, DataValidationError, CacheError
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
            # Update progress
            if progress_callback:
                progress_callback.update(PROGRESS_MILESTONES['validation_start'], "Validating request...")
            
            # Parse validated inputs
            team = Team.from_abbreviation(request.team_abbreviation)
            season = Season(request.season_year)
            
            if progress_callback:
                progress_callback.update(PROGRESS_MILESTONES['orchestration_start'], "Orchestrating data sources...")
            
            # Orchestrator handles all the complexity of data source selection
            season_stats, game_stats, team_record = self._orchestrator.calculate_team_analysis(
                team=team,
                season=season,
                season_type_filter=request.season_type_filter,
                configuration=request.configuration,
                progress_callback=progress_callback
            )
            
            if progress_callback:
                progress_callback.update(PROGRESS_MILESTONES['rankings_calculation'], "Calculating rankings...")
            
            # Calculate rankings (if we have league data)
            rankings = self._calculate_rankings(team, season, request.season_type_filter, request.configuration)
            
            if progress_callback:
                progress_callback.update(PROGRESS_MILESTONES['finalization'], "Finalizing analysis...")
            
            # Calculate league averages (if available)
            league_averages = self._calculate_league_averages(season, request.season_type_filter, request.configuration)
            
            if progress_callback:
                progress_callback.update(1.0, "Analysis complete!")
            
            return TeamAnalysisResponse(
                team=team,
                season=season,
                season_stats=season_stats,
                game_stats=game_stats,
                team_record=team_record,
                rankings=rankings,
                league_averages=league_averages
            )
            
        except Exception as e:
            logger.error(f"Team analysis failed for {request.team_abbreviation} {request.season_year}: {e}")
            raise UseCaseError(f"Analysis failed: {str(e)}", "team_analysis", {
                "team": request.team_abbreviation,
                "season": request.season_year
            })
    
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
    
    def _calculate_rankings(self, team: Team, season: Season, season_type_filter: Optional[str], configuration: Optional[Dict]) -> Optional[Dict]:
        """Calculate team rankings if league data is available."""
        try:
            # Get league-wide stats from cache for ranking calculation
            config_hash = self._orchestrator.league_cache.get_config_hash(configuration or {})
            team_stats_dict, _, _ = self._orchestrator.league_cache.get_or_compute_league_stats(
                season.year, season_type_filter, config_hash,
                None, self._orchestrator.statistics_calculator, configuration or {}
            )
            
            if team_stats_dict and team.abbreviation in team_stats_dict:
                # Use the cache's get_team_rankings method which uses pre-computed rankings
                raw_rankings = self._orchestrator.league_cache.get_team_rankings(team.abbreviation, team_stats_dict)
                
                # Convert integer ranks to PerformanceRank objects
                rankings = {}
                total_teams = len(team_stats_dict)
                for metric, rank in raw_rankings.items():
                    if isinstance(rank, int) and rank > 0:
                        rankings[metric] = ranking_utils.calculate_performance_rank(rank, total_teams)
                return rankings
            else:
                if not team_stats_dict:
                    logger.warning("No team_stats_dict available for rankings calculation")
                elif team.abbreviation not in team_stats_dict:
                    logger.warning(f"Team {team.abbreviation} not found in team_stats_dict")
                else:
                    logger.warning("Unknown issue with rankings calculation")
                return None
            
        except Exception as e:
            logger.warning(f"Could not calculate rankings: {e}")
            return None
    
    def _calculate_league_averages(self, season: Season, season_type_filter: Optional[str], configuration: Optional[Dict]) -> Optional[Dict]:
        """Calculate league averages if available."""
        try:
            # Use the same league cache that's used for rankings
            config_hash = self._orchestrator.league_cache.get_config_hash(configuration or {})
            team_stats_dict, league_averages, _ = self._orchestrator.league_cache.get_or_compute_league_stats(
                season.year, season_type_filter, config_hash,
                None, self._orchestrator.statistics_calculator, configuration or {}
            )
            
            # Return the league averages if available
            if league_averages:
                return league_averages
            else:
                logger.warning("League averages not available from cache")
                return None
            
        except Exception as e:
            logger.warning(f"Could not calculate league averages: {e}")
            return None


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
                season_year, season_type_filter, config_hash,
                None, self._orchestrator.statistics_calculator, configuration or {}
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


