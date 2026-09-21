# src/presentation/streamlit/services/export_service.py - Data export service

import pandas as pd
import json
from typing import Dict, Any, List
from io import BytesIO
from dataclasses import asdict

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
from ....application import TeamAnalysisResponse
from ....domain import GameStats, SeasonStats, NFLMetrics
from ....utils.season_utils import get_regular_season_weeks


class ExportService:
    """Export contract: preserve game identity, selected settings, and both TOERs.

    CSV repeats analysis metadata on every game row. Excel additionally includes
    season totals and rankings. JSON keeps all raw season inputs and each game's
    offensive and opponent-offensive metrics for reproducible comparisons.
    """

    @property
    def excel_available(self) -> bool:
        """Check the optional writer without generating a workbook."""
        return EXCEL_AVAILABLE
    
    def export_to_csv(self, analysis_response: TeamAnalysisResponse) -> bytes:
        """Export analysis data to CSV format."""
        # Create comprehensive DataFrame
        export_data = self._prepare_export_data(analysis_response)
        
        # Convert to CSV
        buffer = BytesIO()
        export_data.to_csv(buffer, index=False)
        return buffer.getvalue()
    
    def export_to_excel(self, analysis_response: TeamAnalysisResponse) -> bytes:
        """Export analysis data to Excel format with multiple sheets."""
        if not EXCEL_AVAILABLE:
            raise ImportError("openpyxl library is required for Excel export. Install with: pip install openpyxl")
            
        buffer = BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Game-by-game data
            game_data = self._prepare_game_data(analysis_response)
            game_data.to_excel(writer, sheet_name='Game_Log', index=False)
            
            # Season summary
            season_data = self._prepare_season_summary(analysis_response)
            season_data.to_excel(writer, sheet_name='Season_Summary', index=False)

            metadata = self._analysis_metadata(analysis_response)
            pd.DataFrame([{
                'Field': key,
                'Value': json.dumps(value, sort_keys=True) if isinstance(value, dict) else value,
            } for key, value in metadata.items()]).to_excel(writer, sheet_name='Analysis_Settings', index=False)
            
            # Rankings if available
            if analysis_response.rankings:
                rankings_data = self._prepare_rankings_data(analysis_response)
                rankings_data.to_excel(writer, sheet_name='Rankings', index=False)
        
        return buffer.getvalue()
    
    def export_to_json(self, analysis_response: TeamAnalysisResponse) -> str:
        """Export analysis data to JSON format."""
        export_dict = {
            'team': {
                'abbreviation': analysis_response.team.abbreviation,
                'name': analysis_response.team_display_name
            },
            'season': {
                'year': analysis_response.season.year
            },
            'analysis': self._analysis_metadata(analysis_response),
            'season_stats': self._season_stats_to_dict(analysis_response.season_stats),
            'game_stats': [self._game_stats_to_dict(game) for game in analysis_response.game_stats],
            'rankings': self._rankings_to_dict(analysis_response.rankings) if analysis_response.rankings else None,
            'league_averages': analysis_response.league_averages
        }
        
        return json.dumps(export_dict, indent=2)
    
    def _prepare_export_data(self, analysis_response: TeamAnalysisResponse) -> pd.DataFrame:
        """Prepare comprehensive export data."""
        if not analysis_response.game_stats:
            return pd.DataFrame()
        
        game_data = []
        season_year = analysis_response.season.year
        regular_season_weeks = get_regular_season_weeks(season_year)
        
        for i, game_stat in enumerate(analysis_response.game_stats, 1):
            # Use actual week number if available, otherwise use game number
            if game_stat.game is not None:
                if game_stat.game.week > regular_season_weeks:
                    # Calculate playoff round based on season year
                    playoff_round = game_stat.game.week - regular_season_weeks
                    week_display = f"P{playoff_round}"
                else:
                    week_display = str(game_stat.game.week)
            else:
                week_display = str(i)  # Fallback to game number
            game_data.append({
                'Team': analysis_response.team_display_name,
                'Team_Code': analysis_response.team.abbreviation,
                'Season': season_year,
                'Season_Type_Filter': analysis_response.season_type_filter,
                'Configuration': json.dumps(analysis_response.configuration, sort_keys=True),
                'Game_ID': game_stat.game.game_id if game_stat.game else None,
                'Game_Date': str(game_stat.game.game_date) if game_stat.game else None,
                'Game_Type': game_stat.game.game_type.value if game_stat.game else None,
                'Week': week_display,
                'Opponent': game_stat.opponent.abbreviation,
                'Location': game_stat.location.value,
                'Yards_Per_Play': game_stat.offensive_stats.yards_per_play,
                'Total_Yards': game_stat.offensive_stats.total_yards,
                'Total_Plays': game_stat.offensive_stats.total_plays,
                'Turnovers': game_stat.offensive_stats.turnovers,
                'Completion_Pct': game_stat.offensive_stats.completion_pct,
                'Rush_YPC': game_stat.offensive_stats.rush_ypc,
                'sacks': game_stat.offensive_stats.sacks,
                'Third_Down_Pct': game_stat.offensive_stats.third_down_pct,
                'Success_Rate': game_stat.offensive_stats.success_rate,
                'First_Downs': game_stat.offensive_stats.first_downs,
                'Points_Per_Drive': game_stat.offensive_stats.points_per_drive,
                'Redzone_TD_Pct': game_stat.offensive_stats.redzone_td_pct,
                'Penalty_Yards': game_stat.offensive_stats.penalty_yards,
                'TOER': game_stat.offensive_stats.toer,
                'TOER_Allowed': game_stat.defensive_stats.toer,
            })
        
        return pd.DataFrame(game_data)
    
    def _prepare_game_data(self, analysis_response: TeamAnalysisResponse) -> pd.DataFrame:
        """Prepare game-by-game data for export.
        
        Transforms game stats into a structured DataFrame suitable for export
        with standardized column names and formatting.
        """
        return self._prepare_export_data(analysis_response)
    
    def _prepare_season_summary(self, analysis_response: TeamAnalysisResponse) -> pd.DataFrame:
        """Prepare season summary data.
        
        Creates a summary DataFrame containing aggregated season statistics
        using centralized metric definitions for consistent naming.
        """
        season_stats = analysis_response.season_stats
        
        # Build summary data using centralized metric definitions
        summary_row = {
            'Team': analysis_response.team_display_name,
            'Season': analysis_response.season.year,
            'Season_Type_Filter': analysis_response.season_type_filter,
            'Configuration': json.dumps(analysis_response.configuration, sort_keys=True),
            'TOER_Allowed': season_stats.toer_allowed,
        }
        
        # Add all metrics dynamically using centralized export names
        for metric in NFLMetrics.get_all_metrics():
            if hasattr(season_stats, metric.key):
                summary_row[metric.export_name] = getattr(season_stats, metric.key)
        
        summary_data = [summary_row]
        
        return pd.DataFrame(summary_data)
    
    def _prepare_rankings_data(self, analysis_response: TeamAnalysisResponse) -> pd.DataFrame:
        """Prepare rankings data for export.
        
        Transforms performance rankings into a structured DataFrame with
        metric names, ranks, and performance descriptions.
        """
        if not analysis_response.rankings:
            return pd.DataFrame()
        
        rankings_data = []
        for metric, performance_rank in analysis_response.rankings.items():
            rankings_data.append({
                'Metric': metric.replace('_', ' ').title(),
                'Rank': performance_rank.rank,
                'Total_Teams': performance_rank.total_teams,
                'Description': performance_rank.description
            })
        
        return pd.DataFrame(rankings_data)
    
    def _season_stats_to_dict(self, season_stats: SeasonStats) -> Dict[str, Any]:
        """Retain aggregates and the raw counts used by methodology formulas."""
        result = asdict(season_stats)
        result.pop('team')
        result.pop('season')
        return result
    
    def _game_stats_to_dict(self, game_stats: GameStats) -> Dict[str, Any]:
        """Convert GameStats to dictionary."""
        game = game_stats.game
        return {
            'game_id': game.game_id if game else None,
            'week': game.week if game else None,
            'game_date': str(game.game_date) if game else None,
            'season_type': game.game_type.value if game else None,
            'team': game_stats.team.abbreviation,
            'opponent': game_stats.opponent.abbreviation,
            'location': game_stats.location.value,
            # Keep the existing flat offensive keys for export consumers.
            **asdict(game_stats.offensive_stats),
            'toer_allowed': game_stats.defensive_stats.toer,
            'defensive_stats': asdict(game_stats.defensive_stats),
        }
    
    def _rankings_to_dict(self, rankings: Dict) -> Dict[str, Any]:
        """Convert rankings to dictionary."""
        if not rankings:
            return {}
        
        rankings_dict = {}
        for metric, performance_rank in rankings.items():
            rankings_dict[metric] = {
                'rank': performance_rank.rank,
                'total_teams': performance_rank.total_teams,
                'description': performance_rank.description
            }
        
        return rankings_dict

    @staticmethod
    def _analysis_metadata(analysis_response: TeamAnalysisResponse) -> Dict[str, Any]:
        return {
            'export_schema_version': 2,
            'team': analysis_response.team.abbreviation,
            'team_name': analysis_response.team_display_name,
            'season': analysis_response.season.year,
            'season_type_filter': analysis_response.season_type_filter,
            'configuration': analysis_response.configuration,
            'turnover_scope': 'offensive possessions',
        }
