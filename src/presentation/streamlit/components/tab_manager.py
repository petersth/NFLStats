# src/presentation/streamlit/components/tab_manager.py - Tab management component

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ....application.dto import TeamAnalysisResponse
from ....domain.metrics import NFLMetrics
from ....domain.toer_calculator import TOERCalculator
from ....utils.season_utils import get_regular_season_weeks
from ..services.chart_generation_service import ChartGenerationService
from ..services.export_service import ExportService
from .methodology_renderer import MethodologyRenderer
from .progress_manager import ProgressManager


class TabManager:
    """Manages the tab display and content."""
    
    def __init__(self, app_state):
        self._chart_service = ChartGenerationService()
        self._export_service = ExportService()
        self._methodology_renderer = MethodologyRenderer()
        self._app_state = app_state
    
    def render_analysis_tabs(self, analysis_response: TeamAnalysisResponse, configuration: dict = None):
        """Render all tabs with their content and configuration."""
        self.render_tabs(analysis_response)
    
    def render_tabs(self, analysis_response: TeamAnalysisResponse):
        """Render all tabs with their content."""
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Game Log", "TOER Breakdown", "League Comparison", "Methodology", "Export Data"])
        
        with tab1:
            if not self._app_state.is_tab_loaded('game_log'):
                with st.spinner("Loading game-by-game statistics..."):
                    self._app_state.set_tab_loaded('game_log')
            
            self._render_game_log_tab(analysis_response)
        
        with tab2:
            if not self._app_state.is_tab_loaded('toer_breakdown'):
                with st.spinner("Loading TOER breakdown..."):
                    self._app_state.set_tab_loaded('toer_breakdown')
            
            self._render_toer_breakdown_tab(analysis_response)
        
        with tab3:
            if not self._app_state.is_tab_loaded('league'):
                with ProgressManager().track_progress(100, "Preparing league comparison") as pm:
                    pm.update(25, "Loading comparison data...")
                    pm.update(50, "Calculating differences...")
                    pm.update(75, "Generating visualizations...")
                    self._app_state.set_tab_loaded('league')
                    pm.update(100, "Complete!")
            
            self._render_league_comparison_tab(analysis_response)
        
        with tab4:
            if not self._app_state.is_tab_loaded('methodology'):
                with st.spinner("Loading methodology documentation..."):
                    self._app_state.set_tab_loaded('methodology')
            
            self._render_methodology_tab(analysis_response)
        
        with tab5:
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
        
        # Get all weeks that have games (handle None game objects)
        weeks_with_games = {game.game.week for game in analysis_response.game_stats if game.game is not None}
        regular_season_weeks_cutoff = get_regular_season_weeks(analysis_response.season.year)
        regular_weeks = [w for w in weeks_with_games if w <= regular_season_weeks_cutoff]
        
        # If no valid game objects, fall back to simple display
        if not weeks_with_games:
            # Simple fallback - just enumerate games
            game_data = []
            for i, game_stat in enumerate(analysis_response.game_stats, 1):
                game_data.append({
                    'Game': i,
                    'Opponent': game_stat.opponent.abbreviation,
                    'Location': game_stat.location.value,
                    'Yds/Play': game_stat.offensive_stats.yards_per_play,
                    'Turnovers': game_stat.offensive_stats.turnovers,
                    'Pass Comp%': game_stat.offensive_stats.completion_pct,
                    'Rush YPC': game_stat.offensive_stats.rush_ypc,
                    'Sacks': game_stat.offensive_stats.sacks,
                    '3rd Down%': game_stat.offensive_stats.third_down_pct,
                    'Success%': game_stat.offensive_stats.success_rate,
                    '1st Downs': game_stat.offensive_stats.first_downs,
                    'Pts/Drive': game_stat.offensive_stats.points_per_drive,
                    'RZ TD%': game_stat.offensive_stats.redzone_td_pct,
                    'Pen Yards': game_stat.offensive_stats.penalty_yards,
                    'TOER': game_stat.offensive_stats.toer
                })
            display_df = pd.DataFrame(game_data)
            
            # Format numeric columns for display
            format_dict = {
                'Yds/Play': '{:.2f}',
                'Turnovers': '{:.0f}',
                'Pass Comp%': '{:.2f}',
                'Rush YPC': '{:.2f}',
                'Sacks': '{:.0f}',
                '3rd Down%': '{:.2f}',
                'Success%': '{:.2f}',
                '1st Downs': '{:.0f}',
                'Pts/Drive': '{:.2f}',
                'RZ TD%': '{:.2f}',
                'Pen Yards': '{:.0f}',
                'TOER': '{:.2f}'
            }
            
            st.dataframe(
                display_df.style.format(format_dict, na_rep='-'),
                use_container_width=True,
                hide_index=True,
                height=len(display_df) * 35 + 38
            )
            return
        
        regular_season_weeks_cutoff = get_regular_season_weeks(analysis_response.season.year)
        regular_weeks = [w for w in weeks_with_games if w <= regular_season_weeks_cutoff]
        
        # Determine expected regular season weeks based on season year
        expected_weeks = regular_season_weeks_cutoff + 1  # Account for bye week
        
        game_data = []
        
        # Add regular season games and detect missing weeks
        for week in range(1, min(expected_weeks, regular_season_weeks_cutoff + 1)):
            if week in regular_weeks:
                # Find the game for this week
                game_stat = next(g for g in analysis_response.game_stats if g.game.week == week)
                game_data.append({
                    'Week': str(week),
                    'Opponent': game_stat.opponent.abbreviation,
                    'Location': game_stat.location.value,
                    'Yds/Play': game_stat.offensive_stats.yards_per_play,
                    'Turnovers': game_stat.offensive_stats.turnovers,
                    'Pass Comp%': game_stat.offensive_stats.completion_pct,
                    'Rush YPC': game_stat.offensive_stats.rush_ypc,
                    'Sacks': game_stat.offensive_stats.sacks,
                    '3rd Down%': game_stat.offensive_stats.third_down_pct,
                    'Success%': game_stat.offensive_stats.success_rate,
                    '1st Downs': game_stat.offensive_stats.first_downs,
                    'Pts/Drive': game_stat.offensive_stats.points_per_drive,
                    'RZ TD%': game_stat.offensive_stats.redzone_td_pct,
                    'Pen Yards': game_stat.offensive_stats.penalty_yards,
                    'TOER': game_stat.offensive_stats.toer
                })
            else:
                # Week without a game - it's missing data
                # We can't reliably detect bye weeks without additional schedule data
                game_data.append({
                    'Week': str(week),
                    'Opponent': 'NO DATA',
                    'Location': '-',
                    'Yds/Play': None,
                    'Turnovers': None,
                    'Pass Comp%': None,
                    'Rush YPC': None,
                    'Sacks': None,
                    '3rd Down%': None,
                    'Success%': None,
                    '1st Downs': None,
                    'Pts/Drive': None,
                    'RZ TD%': None,
                    'Pen Yards': None,
                    'TOER': None
                })
        
        # Add playoff games
        playoff_games = [g for g in analysis_response.game_stats if g.game.week > regular_season_weeks_cutoff]
        for game_stat in playoff_games:
            playoff_round = game_stat.game.week - regular_season_weeks_cutoff
            week_display = f"P{playoff_round}"
            game_data.append({
                'Week': week_display,
                'Opponent': game_stat.opponent.abbreviation,
                'Location': game_stat.location.value,
                'Yds/Play': game_stat.offensive_stats.yards_per_play,
                'Turnovers': game_stat.offensive_stats.turnovers,
                'Pass Comp%': game_stat.offensive_stats.completion_pct,
                'Rush YPC': game_stat.offensive_stats.rush_ypc,
                'Sacks': game_stat.offensive_stats.sacks,
                '3rd Down%': game_stat.offensive_stats.third_down_pct,
                'Success%': game_stat.offensive_stats.success_rate,
                '1st Downs': game_stat.offensive_stats.first_downs,
                'Pts/Drive': game_stat.offensive_stats.points_per_drive,
                'RZ TD%': game_stat.offensive_stats.redzone_td_pct,
                'Pen Yards': game_stat.offensive_stats.penalty_yards,
                'TOER': game_stat.offensive_stats.toer
            })
        
        display_df = pd.DataFrame(game_data)
        
        # Format numeric columns for display
        format_dict = {
            'Yds/Play': '{:.2f}',
            'Turnovers': '{:.0f}',
            'Pass Comp%': '{:.2f}',
            'Rush YPC': '{:.2f}',
            'Sacks': '{:.0f}',
            '3rd Down%': '{:.2f}',
            'Success%': '{:.2f}',
            '1st Downs': '{:.0f}',
            'Pts/Drive': '{:.2f}',
            'RZ TD%': '{:.2f}',
            'Pen Yards': '{:.0f}',
            'TOER': '{:.2f}'
        }
        
        st.dataframe(
            display_df.style.format(format_dict, na_rep='-'),
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
    
    def _render_toer_breakdown_tab(self, analysis_response: TeamAnalysisResponse):
        """Render the TOER breakdown showing component scores for each game."""
        st.subheader("TOER Component Breakdown")
        
        if not analysis_response.game_stats:
            st.info("No game data available for TOER breakdown.")
            return

        # Build breakdown data
        breakdown_data = []
        
        # Get weeks that have games
        weeks_with_games = [g.game.week for g in analysis_response.game_stats if g.game is not None]
        
        # If no valid game objects, fall back to simple display
        if not weeks_with_games:
            for i, game_stat in enumerate(analysis_response.game_stats, 1):
                # Calculate individual component scores for this game
                ypp_score = TOERCalculator.calculate_yards_per_play_score(game_stat.offensive_stats.yards_per_play)
                turnovers_score = TOERCalculator.calculate_turnovers_score(float(game_stat.offensive_stats.turnovers))
                completion_score = TOERCalculator.calculate_completion_pct_score(game_stat.offensive_stats.completion_pct)
                rush_ypc_score = TOERCalculator.calculate_rush_ypc_score(game_stat.offensive_stats.rush_ypc)
                sacks_score = TOERCalculator.calculate_sacks_score(float(game_stat.offensive_stats.sacks))
                third_down_score = TOERCalculator.calculate_third_down_score(game_stat.offensive_stats.third_down_pct)
                success_rate_score = TOERCalculator.calculate_success_rate_score(game_stat.offensive_stats.success_rate)
                first_downs_score = TOERCalculator.calculate_first_downs_score(float(game_stat.offensive_stats.first_downs))
                ppd_score = TOERCalculator.calculate_ppd_score(game_stat.offensive_stats.points_per_drive)
                redzone_score = TOERCalculator.calculate_redzone_score(game_stat.offensive_stats.redzone_td_pct)
                penalty_score = TOERCalculator.calculate_penalty_yards_adjustment(float(game_stat.offensive_stats.penalty_yards))
                
                breakdown_data.append({
                    'Game': i,
                    'Opponent': game_stat.opponent.abbreviation,
                    'Location': game_stat.location.value,
                    'Yds/Play': ypp_score,
                    'Turnovers': turnovers_score,
                    'Pass Comp%': completion_score,
                    'Rush YPC': rush_ypc_score,
                    'Sacks': sacks_score,
                    '3rd Down%': third_down_score,
                    'Success%': success_rate_score,
                    '1st Downs': first_downs_score,
                    'Pts/Drive': ppd_score,
                    'RZ TD%': redzone_score,
                    'Pen Yards': penalty_score,
                    'TOER': game_stat.offensive_stats.toer
                })
            
            # Create DataFrame and display
            breakdown_df = pd.DataFrame(breakdown_data)
            
            # Format numeric columns for display
            format_dict = {
                'Yds/Play': '{:.2f}',
                'Turnovers': '{:.2f}',
                'Pass Comp%': '{:.2f}',
                'Rush YPC': '{:.2f}',
                'Sacks': '{:.2f}',
                '3rd Down%': '{:.2f}',
                'Success%': '{:.2f}',
                '1st Downs': '{:.2f}',
                'Pts/Drive': '{:.2f}',
                'RZ TD%': '{:.2f}',
                'Pen Yards': '{:.2f}',
                'TOER': '{:.2f}'
            }
            
            st.dataframe(
                breakdown_df.style.format(format_dict, na_rep='-'),
                use_container_width=True,
                hide_index=True,
                height=len(breakdown_df) * 35 + 38
            )
            return
        
        # Build breakdown with regular season and playoff games
        regular_season_weeks_cutoff = get_regular_season_weeks(analysis_response.season.year)
        regular_weeks = [w for w in weeks_with_games if w <= regular_season_weeks_cutoff]
        
        # Determine expected regular season weeks
        expected_weeks = regular_season_weeks_cutoff + 1  # Account for bye week
        
        # Add regular season games and detect missing weeks
        for week in range(1, min(expected_weeks, regular_season_weeks_cutoff + 1)):
            if week in regular_weeks:
                # Find the game for this week
                game_stat = next(g for g in analysis_response.game_stats if g.game.week == week)
                
                # Calculate individual component scores for this game
                ypp_score = TOERCalculator.calculate_yards_per_play_score(game_stat.offensive_stats.yards_per_play)
                turnovers_score = TOERCalculator.calculate_turnovers_score(float(game_stat.offensive_stats.turnovers))
                completion_score = TOERCalculator.calculate_completion_pct_score(game_stat.offensive_stats.completion_pct)
                rush_ypc_score = TOERCalculator.calculate_rush_ypc_score(game_stat.offensive_stats.rush_ypc)
                sacks_score = TOERCalculator.calculate_sacks_score(float(game_stat.offensive_stats.sacks))
                third_down_score = TOERCalculator.calculate_third_down_score(game_stat.offensive_stats.third_down_pct)
                success_rate_score = TOERCalculator.calculate_success_rate_score(game_stat.offensive_stats.success_rate)
                first_downs_score = TOERCalculator.calculate_first_downs_score(float(game_stat.offensive_stats.first_downs))
                ppd_score = TOERCalculator.calculate_ppd_score(game_stat.offensive_stats.points_per_drive)
                redzone_score = TOERCalculator.calculate_redzone_score(game_stat.offensive_stats.redzone_td_pct)
                penalty_score = TOERCalculator.calculate_penalty_yards_adjustment(float(game_stat.offensive_stats.penalty_yards))
                
                breakdown_data.append({
                    'Week': str(week),
                    'Opponent': game_stat.opponent.abbreviation,
                    'Location': game_stat.location.value,
                    'Yds/Play': ypp_score,
                    'Turnovers': turnovers_score,
                    'Pass Comp%': completion_score,
                    'Rush YPC': rush_ypc_score,
                    'Sacks': sacks_score,
                    '3rd Down%': third_down_score,
                    'Success%': success_rate_score,
                    '1st Downs': first_downs_score,
                    'Pts/Drive': ppd_score,
                    'RZ TD%': redzone_score,
                    'Pen Yards': penalty_score,
                    'TOER': game_stat.offensive_stats.toer
                })
            else:
                # Week without a game - it's missing data
                breakdown_data.append({
                    'Week': str(week),
                    'Opponent': 'NO DATA',
                    'Location': '-',
                    'Yds/Play': None,
                    'Turnovers': None,
                    'Pass Comp%': None,
                    'Rush YPC': None,
                    'Sacks': None,
                    '3rd Down%': None,
                    'Success%': None,
                    '1st Downs': None,
                    'Pts/Drive': None,
                    'RZ TD%': None,
                    'Pen Yards': None,
                    'TOER': None
                })
        
        # Add playoff games
        playoff_games = [g for g in analysis_response.game_stats if g.game.week > regular_season_weeks_cutoff]
        for game_stat in playoff_games:
            playoff_round = game_stat.game.week - regular_season_weeks_cutoff
            week_display = f"P{playoff_round}"
            
            # Calculate individual component scores for this game
            ypp_score = TOERCalculator.calculate_yards_per_play_score(game_stat.offensive_stats.yards_per_play)
            turnovers_score = TOERCalculator.calculate_turnovers_score(float(game_stat.offensive_stats.turnovers))
            completion_score = TOERCalculator.calculate_completion_pct_score(game_stat.offensive_stats.completion_pct)
            rush_ypc_score = TOERCalculator.calculate_rush_ypc_score(game_stat.offensive_stats.rush_ypc)
            sacks_score = TOERCalculator.calculate_sacks_score(float(game_stat.offensive_stats.sacks))
            third_down_score = TOERCalculator.calculate_third_down_score(game_stat.offensive_stats.third_down_pct)
            success_rate_score = TOERCalculator.calculate_success_rate_score(game_stat.offensive_stats.success_rate)
            first_downs_score = TOERCalculator.calculate_first_downs_score(float(game_stat.offensive_stats.first_downs))
            ppd_score = TOERCalculator.calculate_ppd_score(game_stat.offensive_stats.points_per_drive)
            redzone_score = TOERCalculator.calculate_redzone_score(game_stat.offensive_stats.redzone_td_pct)
            penalty_score = TOERCalculator.calculate_penalty_yards_adjustment(float(game_stat.offensive_stats.penalty_yards))
            
            breakdown_data.append({
                'Week': week_display,
                'Opponent': game_stat.opponent.abbreviation,
                'Location': game_stat.location.value,
                'Yds/Play': ypp_score,
                'Turnovers': turnovers_score,
                'Pass Comp%': completion_score,
                'Rush YPC': rush_ypc_score,
                'Sacks': sacks_score,
                '3rd Down%': third_down_score,
                'Success%': success_rate_score,
                '1st Downs': first_downs_score,
                'Pts/Drive': ppd_score,
                'RZ TD%': redzone_score,
                'Pen Yards': penalty_score,
                'TOER': game_stat.offensive_stats.toer
            })
        
        # Create DataFrame
        breakdown_df = pd.DataFrame(breakdown_data)
        
        # Format numeric columns for display
        format_dict = {
            'Yds/Play': '{:.2f}',
            'Turnovers': '{:.2f}',
            'Pass Comp%': '{:.2f}',
            'Rush YPC': '{:.2f}',
            'Sacks': '{:.2f}',
            '3rd Down%': '{:.2f}',
            'Success%': '{:.2f}',
            '1st Downs': '{:.2f}',
            'Pts/Drive': '{:.2f}',
            'RZ TD%': '{:.2f}',
            'Pen Yards': '{:.2f}',
            'TOER': '{:.2f}'
        }
        
        st.dataframe(
            breakdown_df.style.format(format_dict, na_rep='-'),
            use_container_width=True,
            hide_index=True,
            height=len(breakdown_df) * 35 + 38
        )
        
        st.subheader("TOER Allowed Component Breakdown")
        
        toer_allowed_data = []
        
        # Map game stats by week for easier lookup
        game_stats_by_week = {}
        for game_stat in analysis_response.game_stats:
            if game_stat.game:
                game_stats_by_week[game_stat.game.week] = game_stat
        
        # Iterate through breakdown_data to include NO DATA entries
        for item in breakdown_data:
            if item['Opponent'] == 'NO DATA':
                # Missing week - add NO DATA entry
                toer_allowed_row = {
                    'Opponent': 'NO DATA',
                    'Location': '-',
                    'Yds/Play': None,
                    'Turnovers': None,
                    'Pass Comp%': None,
                    'Rush YPC': None,
                    'Sacks': None,
                    '3rd Down%': None,
                    'Success%': None,
                    '1st Downs': None,
                    'Pts/Drive': None,
                    'RZ TD%': None,
                    'Pen Yards': None,
                    'TOER Allowed': None
                }
            else:
                # Get the corresponding game_stat
                week_str = item.get('Week', '')
                if week_str.startswith('P'):
                    # Playoff game
                    playoff_round = int(week_str[1:])
                    week = get_regular_season_weeks(analysis_response.season.year) + playoff_round
                else:
                    week = int(week_str)
                
                game_stat = game_stats_by_week.get(week)
                if not game_stat:
                    continue
                
                # Get TOER Allowed value
                toer_allowed = game_stat.defensive_stats.toer
                
                # Get actual opponent offensive stats from game data (now in defensive_stats)
                defensive_stats = game_stat.defensive_stats
                
                # Calculate component scores using actual opponent stats
                ypp_score = TOERCalculator.calculate_yards_per_play_score(defensive_stats.yards_per_play)
                turnovers_score = TOERCalculator.calculate_turnovers_score(float(defensive_stats.turnovers))
                completion_score = TOERCalculator.calculate_completion_pct_score(defensive_stats.completion_pct)
                rush_ypc_score = TOERCalculator.calculate_rush_ypc_score(defensive_stats.rush_ypc)
                sacks_score = TOERCalculator.calculate_sacks_score(float(defensive_stats.sacks))
                third_down_score = TOERCalculator.calculate_third_down_score(defensive_stats.third_down_pct)
                success_rate_score = TOERCalculator.calculate_success_rate_score(defensive_stats.success_rate)
                first_downs_score = TOERCalculator.calculate_first_downs_score(float(defensive_stats.first_downs))
                ppd_score = TOERCalculator.calculate_ppd_score(defensive_stats.points_per_drive)
                redzone_score = TOERCalculator.calculate_redzone_score(defensive_stats.redzone_td_pct)
                penalty_score = TOERCalculator.calculate_penalty_yards_adjustment(float(defensive_stats.penalty_yards))
                
                toer_allowed_row = {
                    'Opponent': game_stat.opponent.abbreviation,
                    'Location': game_stat.location.value,
                    'Yds/Play': ypp_score,
                    'Turnovers': turnovers_score,
                    'Pass Comp%': completion_score,
                    'Rush YPC': rush_ypc_score,
                    'Sacks': sacks_score,
                    '3rd Down%': third_down_score,
                    'Success%': success_rate_score,
                    '1st Downs': first_downs_score,
                    'Pts/Drive': ppd_score,
                    'RZ TD%': redzone_score,
                    'Pen Yards': penalty_score,
                    'TOER Allowed': toer_allowed
                }
            
            # Add week/game identifier (same as original table)
            if 'Week' in item:
                toer_allowed_row = {'Week': item['Week'], **toer_allowed_row}
            elif 'Game' in item:
                toer_allowed_row = {'Game': item['Game'], **toer_allowed_row}
                    
            toer_allowed_data.append(toer_allowed_row)
    
        # Create DataFrame for TOER Allowed
        toer_allowed_df = pd.DataFrame(toer_allowed_data)
        
        # Format numeric columns for display
        format_dict = {
            'Yds/Play': '{:.2f}',
            'Turnovers': '{:.2f}',
            'Pass Comp%': '{:.2f}',
            'Rush YPC': '{:.2f}',
            'Sacks': '{:.2f}',
            '3rd Down%': '{:.2f}',
            'Success%': '{:.2f}',
            '1st Downs': '{:.2f}',
            'Pts/Drive': '{:.2f}',
            'RZ TD%': '{:.2f}',
            'Pen Yards': '{:.2f}',
            'TOER Allowed': '{:.2f}'
        }
        
        st.dataframe(
            toer_allowed_df.style.format(format_dict, na_rep='-'),
            use_container_width=True,
            hide_index=True,
            height=len(toer_allowed_df) * 35 + 38
        )
        
    def _render_methodology_tab(self, analysis_response: TeamAnalysisResponse):
        """Render the methodology documentation tab."""
        self._methodology_renderer.render_methodology_page(analysis_response)