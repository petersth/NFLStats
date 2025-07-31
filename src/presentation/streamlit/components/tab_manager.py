# src/presentation/streamlit/components/tab_manager.py - Tab management component

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ....application.dto import TeamAnalysisResponse
from ....domain.metrics import NFLMetrics
from ..services.chart_generation_service import ChartGenerationService
from ..services.export_service import ExportService
from .methodology_renderer import MethodologyRenderer
from .progress_manager import ProgressManager
# Note: ApplicationStateInterface removed - using concrete classes


class TabManager:
    """Manages the tab display and content."""
    
    def __init__(self, app_state):
        self._chart_service = ChartGenerationService()
        self._export_service = ExportService()
        self._methodology_renderer = MethodologyRenderer()
        self._app_state = app_state
    
    def render_analysis_tabs(self, analysis_response: TeamAnalysisResponse, configuration: dict = None):
        """Render all tabs with their content and configuration."""
        # Delegate to the main render_tabs method (configuration not currently used)
        self.render_tabs(analysis_response)
    
    def render_tabs(self, analysis_response: TeamAnalysisResponse):
        """Render all tabs with their content."""
        tab1, tab2, tab3, tab4 = st.tabs(["Game Log", "League Comparison", "Methodology", "Export Data"])
        
        with tab1:
            if not self._app_state.is_tab_loaded('game_log'):
                with st.spinner("Loading game-by-game statistics..."):
                    self._app_state.set_tab_loaded('game_log')
            
            self._render_game_log_tab(analysis_response)
        
        with tab2:
            if not self._app_state.is_tab_loaded('league'):
                with ProgressManager().track_progress(100, "Preparing league comparison") as pm:
                    pm.update(25, "Loading comparison data...")
                    pm.update(50, "Calculating differences...")
                    pm.update(75, "Generating visualizations...")
                    self._app_state.set_tab_loaded('league')
                    pm.update(100, "Complete!")
            
            self._render_league_comparison_tab(analysis_response)
        
        with tab3:
            if not self._app_state.is_tab_loaded('methodology'):
                with st.spinner("Loading methodology documentation..."):
                    self._app_state.set_tab_loaded('methodology')
            
            self._render_methodology_tab(analysis_response)
        
        with tab4:
            if not self._app_state.is_tab_loaded('export'):
                with st.spinner("Preparing export options..."):
                    self._app_state.set_tab_loaded('export')
            
            self._render_export_tab(analysis_response)
    
    def _render_game_log_tab(self, analysis_response: TeamAnalysisResponse):
        """Render the game-by-game statistics tab."""
        st.subheader("Game-by-Game Statistics")
        
        if not analysis_response.game_stats:
            st.info("No game data available.")
            return
        
        game_data = []
        for i, game_stat in enumerate(analysis_response.game_stats, 1):
            game_data.append({
                'Game': i,
                'Opponent': game_stat.opponent.abbreviation,
                'Location': game_stat.location.value,
                'Yds/Play': f"{game_stat.yards_per_play:.2f}",
                'Turnovers': game_stat.turnovers,
                'Pass Comp%': f"{game_stat.completion_pct:.2f}",
                'Rush YPC': f"{game_stat.rush_ypc:.2f}",
                'Sacks': game_stat.sacks_allowed,
                '3rd Down%': f"{game_stat.third_down_pct:.2f}",
                'Success%': f"{game_stat.success_rate:.2f}",
                '1st Downs': game_stat.first_downs,
                'Pts/Drive': f"{game_stat.points_per_drive:.2f}",
                'RZ TD%': f"{game_stat.redzone_td_pct:.2f}",
                'Pen Yards': game_stat.penalty_yards
            })
        
        display_df = pd.DataFrame(game_data)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=len(display_df) * 35 + 38
        )
    
    
    def _render_league_comparison_tab(self, analysis_response: TeamAnalysisResponse):
        """Render the league comparison tab."""
        st.subheader("League Comparison")
        
        if not analysis_response.league_averages:
            st.info("League comparison data not available.")
            return
        
        # Your Team vs League Average Table
        st.markdown("### Your Team vs League Average")
        
        season_stats = analysis_response.season_stats
        league_avgs = analysis_response.league_averages
        rankings = analysis_response.rankings or {}
        
        # Use centralized metrics definitions
        metrics_to_compare = [(metric.key, metric.short_name) for metric in NFLMetrics.get_all_metrics() 
                             if metric.key in ['avg_yards_per_play', 'turnovers_per_game', 'completion_pct', 
                                             'rush_ypc', 'sacks_per_game', 'third_down_pct', 'success_rate',
                                             'first_downs_per_game', 'points_per_drive', 'redzone_td_pct', 
                                             'penalty_yards_per_game']]
        
        comparison_data = []
        for stat_key, display_name in metrics_to_compare:
            if hasattr(season_stats, stat_key) and stat_key in league_avgs:
                team_val = getattr(season_stats, stat_key)
                league_val = league_avgs[stat_key]
                
                # Calculate percentage difference
                if league_val != 0:
                    pct_diff = ((team_val - league_val) / league_val) * 100
                else:
                    pct_diff = 0
                
                rank_display = "N/A"
                if stat_key in rankings:
                    rank = rankings[stat_key].rank
                    rank_display = f"{rank}/32"
                
                comparison_data.append({
                    'Metric': display_name,
                    f'{analysis_response.team.abbreviation}': f"{team_val:.2f}",
                    'League Avg': f"{league_val:.2f}",
                    'Difference': f"{pct_diff:+.2f}%",
                    'Rank': rank_display
                })
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True,
                height=len(comparison_df) * 35 + 38
            )
            
            # Create league comparison chart
            team_values = [float(val) for val in comparison_df[f'{analysis_response.team.abbreviation}']]
            league_values = [float(val) for val in comparison_df['League Avg']]
            
            fig = go.Figure()
            
            # Determine theme
            use_dark_theme = st.get_option('theme.base') == 'dark'
            plot_template = "plotly_dark" if use_dark_theme else "plotly_white"
            primary_color = st.get_option('theme.primaryColor') or '#1f77b4'
            
            # Add team bars
            fig.add_trace(go.Bar(
                name='Your Team',
                x=comparison_df['Metric'],
                y=team_values,
                marker_color=primary_color,
                text=[f"{val}" for val in comparison_df[f'{analysis_response.team.abbreviation}']],
                textposition='outside'
            ))
            
            # Add league average bars
            fig.add_trace(go.Bar(
                name='League Average',
                x=comparison_df['Metric'],
                y=league_values,
                marker_color='lightgray' if not use_dark_theme else 'gray',
                text=[f"{val}" for val in comparison_df['League Avg']],
                textposition='outside'
            ))
            
            fig.update_layout(
                template=plot_template,
                title=dict(
                    text='Team Performance vs League Average',
                    x=0.5,
                    xanchor='center',
                    font=dict(size=18)
                ),
                xaxis=dict(
                    title='Metrics',
                    tickangle=-45
                ),
                yaxis_title='Values',
                barmode='group',
                height=500,
                margin=dict(l=60, r=60, t=80, b=80)  # Extra bottom margin for angled labels
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Rankings Overview
            st.markdown("### Rankings Overview")
            
            if rankings:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Strongest Areas")
                    
                    # Get top 5 rankings (lowest rank numbers = best performance)
                    ranked_metrics = [(metric, perf_rank.rank) for metric, perf_rank in rankings.items()]
                    top_5_strengths = sorted(ranked_metrics, key=lambda x: x[1])[:5]
                    
                    for metric, rank in top_5_strengths:
                        perf_rank = rankings[metric]
                        metric_display = metric.replace('_', ' ').title()
                        
                        if rank == 1:
                            st.success(f"**{metric_display}**: #{rank} (Best in NFL)")
                        elif perf_rank.description in ['Elite', 'Excellent']:
                            st.success(f"**{metric_display}**: #{rank} ({perf_rank.description})")
                        elif perf_rank.description == 'Good':
                            st.info(f"**{metric_display}**: #{rank} ({perf_rank.description})")
                        else:
                            st.warning(f"**{metric_display}**: #{rank} ({perf_rank.description})")
                
                with col2:
                    st.markdown("#### Areas for Improvement")
                    
                    # Get bottom 5 rankings (highest rank numbers = worst performance)
                    bottom_5_weaknesses = sorted(ranked_metrics, key=lambda x: x[1], reverse=True)[:5]
                    
                    for metric, rank in bottom_5_weaknesses:
                        perf_rank = rankings[metric]
                        metric_display = metric.replace('_', ' ').title()
                        
                        if rank == 32:
                            st.error(f"**{metric_display}**: #{rank} (Worst in NFL)")
                        elif perf_rank.description == 'Poor':
                            st.error(f"**{metric_display}**: #{rank} ({perf_rank.description})")
                        elif perf_rank.description == 'Below Average':
                            st.warning(f"**{metric_display}**: #{rank} ({perf_rank.description})")
                        else:
                            st.info(f"**{metric_display}**: #{rank} ({perf_rank.description})")
    
    def _render_export_tab(self, analysis_response: TeamAnalysisResponse):
        """Render the data export tab."""
        st.subheader("Export Analysis Data")
        
        st.markdown("Download your team's analysis data in various formats:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**CSV Format**")
            st.markdown("Game-by-game data in spreadsheet format")
            
            csv_data = self._export_service.export_to_csv(analysis_response)
            st.download_button(
                label="📊 Download CSV",
                data=csv_data,
                file_name=f"{analysis_response.team.abbreviation}_{analysis_response.season.year}_stats.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            st.markdown("**Excel Format**")
            st.markdown("Game-by-game data in Excel format")
            
            try:
                excel_data = self._export_service.export_to_excel(analysis_response)
                st.download_button(
                    label="📈 Download Excel",
                    data=excel_data,
                    file_name=f"{analysis_response.team.abbreviation}_{analysis_response.season.year}_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except ImportError as e:
                st.button(
                    label="📈 Excel (Not Available)",
                    disabled=True,
                    use_container_width=True,
                    help="Install openpyxl library to enable Excel export: pip install openpyxl"
                )
        
        with col3:
            st.markdown("**JSON Format**")
            st.markdown("Structured data for developers")
            
            json_data = self._export_service.export_to_json(analysis_response)
            st.download_button(
                label="🔧 Download JSON",
                data=json_data,
                file_name=f"{analysis_response.team.abbreviation}_{analysis_response.season.year}_data.json",
                mime="application/json",
                use_container_width=True
            )
        
        st.divider()
        
        # Data preview
        st.subheader("Data Preview")
        
        preview_option = st.selectbox(
            "Select data to preview:",
            ["Game Log", "Season Summary", "Rankings"]
        )
        
        if preview_option == "Game Log":
            game_data = self._export_service._prepare_game_data(analysis_response)
            if not game_data.empty:
                st.dataframe(game_data.head(10), use_container_width=True)
                if len(game_data) > 10:
                    st.info(f"Showing first 10 of {len(game_data)} games. Download full data using buttons above.")
        
        elif preview_option == "Season Summary":
            season_data = self._export_service._prepare_season_summary(analysis_response)
            if not season_data.empty:
                st.dataframe(season_data, use_container_width=True)
        
        elif preview_option == "Rankings" and analysis_response.rankings:
            rankings_data = self._export_service._prepare_rankings_data(analysis_response)
            if not rankings_data.empty:
                st.dataframe(rankings_data, use_container_width=True)
    
    def _render_methodology_tab(self, analysis_response: TeamAnalysisResponse):
        """Render the methodology documentation tab."""
        self._methodology_renderer.render_methodology_page(analysis_response)