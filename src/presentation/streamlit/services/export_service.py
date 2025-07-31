# src/presentation/streamlit/services/export_service.py - Data export service

import pandas as pd
import json
from typing import Dict, Any, List
from io import BytesIO

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
from ....application import TeamAnalysisResponse
from ....domain import GameStats, SeasonStats, NFLMetrics


class ExportService:
    """Service for exporting analysis data to various formats."""
    
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
                'name': analysis_response.team.name
            },
            'season': {
                'year': analysis_response.season.year
            },
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
        for i, game_stat in enumerate(analysis_response.game_stats, 1):
            game_data.append({
                'Game': i,
                'Opponent': game_stat.opponent.abbreviation,
                'Location': game_stat.location.value,
                'Yards_Per_Play': game_stat.yards_per_play,
                'Total_Yards': game_stat.total_yards,
                'Total_Plays': game_stat.total_plays,
                'Turnovers': game_stat.turnovers,
                'Completion_Pct': game_stat.completion_pct,
                'Rush_YPC': game_stat.rush_ypc,
                'Sacks_Allowed': game_stat.sacks_allowed,
                'Third_Down_Pct': game_stat.third_down_pct,
                'Success_Rate': game_stat.success_rate,
                'First_Downs': game_stat.first_downs,
                'Points_Per_Drive': game_stat.points_per_drive,
                'Redzone_TD_Pct': game_stat.redzone_td_pct,
                'Penalty_Yards': game_stat.penalty_yards
            })
        
        return pd.DataFrame(game_data)
    
    def _prepare_game_data(self, analysis_response: TeamAnalysisResponse) -> pd.DataFrame:
        """Prepare game-by-game data for export."""
        return self._prepare_export_data(analysis_response)
    
    def _prepare_season_summary(self, analysis_response: TeamAnalysisResponse) -> pd.DataFrame:
        """Prepare season summary data."""
        season_stats = analysis_response.season_stats
        
        # Build summary data using centralized metric definitions
        summary_row = {
            'Team': analysis_response.team.name,
            'Season': analysis_response.season.year,
        }
        
        # Add all metrics dynamically using centralized export names
        for metric in NFLMetrics.get_all_metrics():
            if hasattr(season_stats, metric.key):
                summary_row[metric.export_name] = getattr(season_stats, metric.key)
        
        summary_data = [summary_row]
        
        return pd.DataFrame(summary_data)
    
    def _prepare_rankings_data(self, analysis_response: TeamAnalysisResponse) -> pd.DataFrame:
        """Prepare rankings data for export."""
        if not analysis_response.rankings:
            return pd.DataFrame()
        
        rankings_data = []
        for metric, performance_rank in analysis_response.rankings.items():
            rankings_data.append({
                'Metric': metric.replace('_', ' ').title(),
                'Rank': performance_rank.rank,
                'Description': performance_rank.description
            })
        
        return pd.DataFrame(rankings_data)
    
    def _season_stats_to_dict(self, season_stats: SeasonStats) -> Dict[str, Any]:
        """Convert SeasonStats to dictionary."""
        return {
            'games_played': season_stats.games_played,
            'avg_yards_per_play': season_stats.avg_yards_per_play,
            'total_yards': season_stats.total_yards,
            'total_plays': season_stats.total_plays,
            'turnovers_per_game': season_stats.turnovers_per_game,
            'completion_pct': season_stats.completion_pct,
            'rush_ypc': season_stats.rush_ypc,
            'sacks_per_game': season_stats.sacks_per_game,
            'third_down_pct': season_stats.third_down_pct,
            'success_rate': season_stats.success_rate,
            'first_downs_per_game': season_stats.first_downs_per_game,
            'points_per_drive': season_stats.points_per_drive,
            'redzone_td_pct': season_stats.redzone_td_pct,
            'penalty_yards_per_game': season_stats.penalty_yards_per_game
        }
    
    def _game_stats_to_dict(self, game_stats: GameStats) -> Dict[str, Any]:
        """Convert GameStats to dictionary."""
        return {
            'opponent': game_stats.opponent.abbreviation,
            'location': game_stats.location.value,
            'yards_per_play': game_stats.yards_per_play,
            'total_yards': game_stats.total_yards,
            'total_plays': game_stats.total_plays,
            'turnovers': game_stats.turnovers,
            'completion_pct': game_stats.completion_pct,
            'rush_ypc': game_stats.rush_ypc,
            'sacks_allowed': game_stats.sacks_allowed,
            'third_down_pct': game_stats.third_down_pct,
            'success_rate': game_stats.success_rate,
            'first_downs': game_stats.first_downs,
            'points_per_drive': game_stats.points_per_drive,
            'redzone_td_pct': game_stats.redzone_td_pct,
            'penalty_yards': game_stats.penalty_yards
        }
    
    def _rankings_to_dict(self, rankings: Dict) -> Dict[str, Any]:
        """Convert rankings to dictionary."""
        if not rankings:
            return {}
        
        rankings_dict = {}
        for metric, performance_rank in rankings.items():
            rankings_dict[metric] = {
                'rank': performance_rank.rank,
                'description': performance_rank.description
            }
        
        return rankings_dict