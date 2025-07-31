# src/presentation/streamlit/components/metrics_renderer.py - Metrics display component

import streamlit as st
import html
from typing import Optional, Dict, List
from ....application import TeamAnalysisResponse
from ....domain import Team, Season, SeasonStats, PerformanceRank, TeamRecord, NFLMetrics
from ....utils import ranking_utils


class MetricsRenderer:
    """Renders season metrics with performance indicators."""
    
    def __init__(self):
        # No longer needs ranking service - uses utility function directly
        pass
    
    def render_team_header(self, team: Team, season: Season, season_type_filter: str = "ALL", team_record: Optional[TeamRecord] = None, game_stats: Optional[List] = None):
        """Render team header with branding and record information."""
        # Get season type display text
        season_type_text = {
            "ALL": "",
            "REG": " (Regular Season)", 
            "POST": " (Playoffs)"
        }.get(season_type_filter, "")
        
        primary_color = team.colors[0] if team.colors else "#013369"
        secondary_color = team.colors[1] if len(team.colors) > 1 else primary_color
        
        # Record display - always show full season record regardless of filter
        record_text = ""
        if team_record:
            # Build record content first to avoid empty paragraphs
            record_content = ""
            
            # Always show regular season record if it exists
            if team_record.regular_season_wins + team_record.regular_season_losses > 0:
                record_content += f"{team_record.regular_season_wins}-{team_record.regular_season_losses} Regular Season"
            
            # Always show playoff record if they made playoffs
            if team_record.playoff_wins + team_record.playoff_losses > 0:
                if record_content:
                    record_content += f" • {team_record.playoff_wins}-{team_record.playoff_losses} Playoffs"
                else:
                    record_content += f"{team_record.playoff_wins}-{team_record.playoff_losses} Playoffs"
            
            # Only create paragraph if we have content
            if record_content:
                safe_record_content = html.escape(record_content)
                record_text = f"<p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 0.9em;'>{safe_record_content}</p>"
        elif game_stats and len(game_stats) > 0:
            # Fallback to games analyzed
            games_count = len(game_stats)
            safe_games_text = html.escape(f"{games_count} games analyzed")
            record_text = f"<p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 0.9em;'>{safe_games_text}</p>"
        
        # Sanitize all user-controlled content
        safe_logo = html.escape(str(team.logo))
        safe_name = html.escape(str(team.name))
        safe_season_text = html.escape(str(season_type_text))
        
        header_html = f"""
        <div style="background: linear-gradient(135deg, {primary_color}, {secondary_color}); 
                    padding: 15px; 
                    border-radius: 12px; 
                    margin-bottom: 20px; 
                    color: white; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="display: flex; align-items: center; gap: 15px;">
                <div style="font-size: 2em;">{safe_logo}</div>
                <div>
                    <h2 style="margin: 0; font-size: 1.5em;">{safe_name} {season.year}{safe_season_text}</h2>
                    {record_text}
                </div>
            </div>
        </div>
        """
        
        st.markdown(header_html, unsafe_allow_html=True)
    
    def render_team_info_sidebar(self, team: Team, team_record: Optional[TeamRecord] = None):
        """Render team information sidebar."""
        if team_record:
            st.subheader("Team Record")
            
            # Regular season record
            if team_record.regular_season_wins + team_record.regular_season_losses > 0:
                reg_pct = team_record.regular_season_wins / (team_record.regular_season_wins + team_record.regular_season_losses)
                st.metric(
                    "Regular Season", 
                    f"{team_record.regular_season_wins}-{team_record.regular_season_losses}",
                    f"{reg_pct:.1%}"
                )
            
            # Playoff record if applicable
            if team_record.playoff_wins + team_record.playoff_losses > 0:
                playoff_pct = team_record.playoff_wins / (team_record.playoff_wins + team_record.playoff_losses)
                st.metric(
                    "Playoffs", 
                    f"{team_record.playoff_wins}-{team_record.playoff_losses}",
                    f"{playoff_pct:.1%}"
                )
    
    def render_season_metrics(self, analysis_response: TeamAnalysisResponse):
        """Render the main season metrics display."""
        season_stats = analysis_response.season_stats
        rankings = analysis_response.rankings or {}
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Define metric layout using centralized definitions
        metric_layout = [
            # Column 1
            [
                ('games_played', lambda: st.metric(NFLMetrics.GAMES_PLAYED.short_name, season_stats.games_played)),
                ('avg_yards_per_play', lambda: self._render_metric_with_rank(
                    NFLMetrics.AVG_YARDS_PER_PLAY.short_name,
                    f"{season_stats.avg_yards_per_play:.2f}",
                    rankings.get('avg_yards_per_play')
                )),
                ('rush_ypc', lambda: self._render_metric_with_rank(
                    NFLMetrics.RUSH_YPC.short_name,
                    f"{season_stats.rush_ypc:.2f}",
                    rankings.get('rush_ypc')
                ))
            ],
            # Column 2  
            [
                ('points_per_drive', lambda: self._render_metric_with_rank(
                    NFLMetrics.POINTS_PER_DRIVE.short_name,
                    f"{season_stats.points_per_drive:.2f}",
                    rankings.get('points_per_drive')
                )),
                ('success_rate', lambda: self._render_metric_with_rank(
                    NFLMetrics.SUCCESS_RATE.short_name,
                    f"{season_stats.success_rate:.2f}%",
                    rankings.get('success_rate')
                )),
                ('third_down_pct', lambda: self._render_metric_with_rank(
                    NFLMetrics.THIRD_DOWN_PCT.short_name,
                    f"{season_stats.third_down_pct:.2f}%",
                    rankings.get('third_down_pct')
                ))
            ],
            # Column 3
            [
                ('completion_pct', lambda: self._render_metric_with_rank(
                    NFLMetrics.COMPLETION_PCT.short_name,
                    f"{season_stats.completion_pct:.2f}%",
                    rankings.get('completion_pct')
                )),
                ('redzone_td_pct', lambda: self._render_metric_with_rank(
                    NFLMetrics.REDZONE_TD_PCT.short_name,
                    f"{season_stats.redzone_td_pct:.2f}%",
                    rankings.get('redzone_td_pct')
                )),
                ('first_downs_per_game', lambda: self._render_metric_with_rank(
                    NFLMetrics.FIRST_DOWNS_PER_GAME.short_name,
                    f"{season_stats.first_downs_per_game:.2f}",
                    rankings.get('first_downs_per_game')
                ))
            ],
            # Column 4
            [
                ('turnovers_per_game', lambda: self._render_metric_with_rank(
                    NFLMetrics.TURNOVERS_PER_GAME.short_name,
                    f"{season_stats.turnovers_per_game:.2f}",
                    rankings.get('turnovers_per_game')
                )),
                ('sacks_per_game', lambda: self._render_metric_with_rank(
                    NFLMetrics.SACKS_PER_GAME.short_name,
                    f"{season_stats.sacks_per_game:.2f}",
                    rankings.get('sacks_per_game')
                )),
                ('penalty_yards_per_game', lambda: self._render_metric_with_rank(
                    NFLMetrics.PENALTY_YARDS_PER_GAME.short_name,
                    f"{season_stats.penalty_yards_per_game:.2f}",
                    rankings.get('penalty_yards_per_game')
                ))
            ]
        ]
        
        # Render each column
        columns = [col1, col2, col3, col4]
        for col_idx, column_metrics in enumerate(metric_layout):
            with columns[col_idx]:
                for metric_key, render_func in column_metrics:
                    render_func()
    
    def _render_metric_with_rank(self, label: str, value: str, performance_rank: Optional = None):
        """Render a metric with optional performance ranking."""
        if performance_rank:
            # Determine color based on performance
            good_descriptions = ['Best in NFL', 'Elite', 'Excellent', 'Above Average']
            bad_descriptions = ['Below Average', 'Poor', 'Worst in NFL']
            
            if performance_rank.description in good_descriptions:
                color = '#28a745'  # Green
            elif performance_rank.description in bad_descriptions:
                color = '#dc3545'  # Red
            else:
                color = '#6c757d'  # Gray
            
            # Create custom metric display with ranking - sanitize all content
            safe_label = html.escape(str(label))
            safe_value = html.escape(str(value))
            safe_description = html.escape(str(performance_rank.description))
            safe_rank = html.escape(str(performance_rank.rank))
            
            st.markdown(f"""
            <div style="margin-bottom: 1rem;">
                <div style="font-size: 0.8em; color: #666; margin-bottom: 0.2rem;">{safe_label}</div>
                <div style="font-size: 1.5em; font-weight: bold; line-height: 1;">{safe_value}</div>
                <div style="font-size: 0.75em; color: {color}; margin-top: 0.2rem;">
                    #{safe_rank} - {safe_description}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Fallback to standard Streamlit metric when no ranking available
            st.metric(label, value)