# src/presentation/streamlit/components/tab_manager.py - Tab management component

from copy import deepcopy
from functools import partial
import time

import streamlit as st
import pandas as pd
from ....application.dto import TeamAnalysisResponse
from ....domain.entities import OffensiveStats
from ....domain.metrics import NFLMetrics
from ....domain.toer_calculator import TOERCalculator
from ....utils.season_utils import get_regular_season_weeks
from ..metric_labels import get_metric_label
from ..services.export_service import ExportService
from ..services.chart_generation_service import ChartGenerationService
from .methodology_renderer import MethodologyRenderer


class TabManager:
    """Manages the tab display and content."""
    
    def __init__(self, app_state):
        self._export_service = ExportService()
        self._methodology_renderer = MethodologyRenderer()
        self._tab_fragment_rendered = False

    def render_analysis_tabs(
        self, analysis_response: TeamAnalysisResponse, configuration: dict = None,
        *, cache_nfl_data: bool = True,
    ):
        """Start navigation for a response supplied by a full app run."""
        self._tab_fragment_rendered = False
        self.render_tabs(analysis_response, cache_nfl_data=cache_nfl_data)

    @st.fragment
    def render_tabs(self, analysis_response: TeamAnalysisResponse, *, cache_nfl_data: bool = True):
        """Render only the active tab; tab interactions rerun this fragment.

        The stable tab key preserves navigation when a sidebar change supplies
        a new analysis response. Full app reruns replace the fragment arguments,
        so subsequent tab interactions always use the current team and filters.
        """
        is_tab_interaction = self._tab_fragment_rendered
        self._tab_fragment_rendered = True
        if (
            is_tab_interaction
            and cache_nfl_data
            and analysis_response.source_data_expires_at is not None
            and time.time() >= analysis_response.source_data_expires_at
        ):
            # The initial full run may finish after its source deadline. Show
            # that coherent result once instead of creating an endless rerun.
            # Subsequent tab/preview interactions re-enter the controller so
            # stale source data, calculations, and rankings refresh together.
            st.rerun(scope="app")

        renderers = (
            ("Game Log", self._render_game_log_tab),
            ("TOER Breakdown", self._render_toer_breakdown_tab),
            ("League Comparison", self._render_league_comparison_tab),
            ("Methodology", self._render_methodology_tab),
            ("Export Data", self._render_export_tab),
        )
        tabs = st.tabs(
            [label for label, _ in renderers],
            key="analysis_tabs",
            on_change="rerun",
        )
        for tab, (_, render) in zip(tabs, renderers):
            if tab.open:
                with tab:
                    render(analysis_response)
    
    def _render_game_log_tab(self, analysis_response: TeamAnalysisResponse):
        """Render all game statistics together for the available games."""
        if not analysis_response.game_stats:
            st.markdown('<div class="game-log-heading"><h3>Game log</h3></div>', unsafe_allow_html=True)
            st.info("No game data available.")
            return
        
        games_with_weeks = self._games_with_week_labels(analysis_response)

        # Legacy responses without game metadata retain every statistic.
        game_column = 'Week' if games_with_weeks else 'Game'
        labelled_games = games_with_weeks or list(enumerate(analysis_response.game_stats, 1))
        game_data = []
        for week_display, game_stat in labelled_games:
            game_data.append({
                game_column: week_display,
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
                'TOER': game_stat.offensive_stats.toer,
                'TOER Allowed': game_stat.defensive_stats.toer
            })
        
        display_df = pd.DataFrame(game_data)
        game_count = len(display_df)
        st.markdown(
            '<div class="game-log-heading"><h3>Game log</h3>'
            '<span title="Games with available statistics">'
            f'{game_count} {"game" if game_count == 1 else "games"}</span></div>',
            unsafe_allow_html=True,
        )

        # Compact headings keep all statistics visible on a desktop. Full
        # definitions belong in the column tooltips, not in wider headings.
        metric_columns = [
            ('Yds/Play', 64, '%.2f', 'Offensive yards per play in this game.'),
            ('Turnovers', 48, '%.0f', 'Offensive turnovers in this game.'),
            ('Pass Comp%', 72, '%.2f%%', 'Pass completion percentage in this game.'),
            ('Rush YPC', 62, '%.2f', 'Rushing yards per carry in this game.'),
            ('Sacks', 52, '%.0f', 'Sacks allowed by the offense in this game.'),
            ('3rd Down%', 70, '%.2f%%', 'Third-down conversion percentage in this game.'),
            ('Success%', 72, '%.2f%%', 'Percentage of successful plays in this game under the selected settings. See Methodology for definitions.'),
            ('1st Downs', 52, '%.0f', 'Offensive first downs in this game.'),
            ('Pts/Drive', 66, '%.2f', 'Offensive points scored per drive in this game.'),
            ('RZ TD%', 68, '%.2f%%', 'Percentage of red-zone trips ending in an offensive touchdown in this game.'),
            ('Pen Yards', 54, '%.0f', 'Offensive penalty yards in this game.'),
            ('TOER', 58, '%.2f', 'Total Offensive Efficiency Rating for this game.'),
            ('TOER Allowed', 70, '%.2f', "Opponent's Total Offensive Efficiency Rating against this defense in this game."),
        ]
        column_config = {
            game_column: (
                st.column_config.TextColumn(
                    'Wk', width=45, pinned=True,
                    help='Regular-season week, or P1/P2/… for postseason weeks.',
                ) if game_column == 'Week' else
                st.column_config.NumberColumn('Game', width=45, pinned=True, format='%.0f')
            ),
            'Opponent': st.column_config.TextColumn('Opp', width=55, pinned=True, help='Opponent'),
            'Location': st.column_config.TextColumn('Site', width=60, help='Home, away, or neutral site'),
        }
        compact_labels = {
            'Turnovers': 'TO', 'Pass Comp%': 'Comp%', 'Rush YPC': 'Yds/car',
            '3rd Down%': '3rd%', '1st Downs': '1st', 'Pen Yards': 'Pen yd',
            'TOER Allowed': 'Allowed',
        }
        column_config.update({
            column: st.column_config.NumberColumn(
                compact_labels.get(column, column), width=column_width, format=number_format, help=help_text,
            )
            for column, column_width, number_format, help_text in metric_columns
        })
        
        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            placeholder="-",
            column_config=column_config,
            column_order=[game_column, "Opponent", "Location", "TOER", "TOER Allowed",
                          *[name for name, *_ in metric_columns if name not in ("TOER", "TOER Allowed")]],
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
        
        metrics_to_compare = [(metric.key, get_metric_label(metric.key, season=True)) for metric in NFLMetrics.get_all_metrics()
                             if metric.key in ['avg_yards_per_play', 'turnovers_per_game', 'completion_pct', 
                                             'rush_ypc', 'sacks_per_game', 'third_down_pct', 'success_rate',
                                             'first_downs_per_game', 'points_per_drive', 'redzone_td_pct', 
                                             'penalty_yards_per_game']]
        
        comparison_data = []
        for stat_key, display_name in metrics_to_compare:
            if hasattr(season_stats, stat_key) and stat_key in league_avgs:
                team_val = getattr(season_stats, stat_key)
                league_val = league_avgs[stat_key]
                
                # A zero baseline has no defined percentage difference, even
                # when the team's value is also zero.
                pct_diff = ((team_val - league_val) / league_val) * 100 if league_val != 0 else None
                
                rank_display = "N/A"
                if stat_key in rankings:
                    performance_rank = rankings[stat_key]
                    rank_display = f"{performance_rank.rank}/{performance_rank.total_teams}"
                
                comparison_data.append({
                    'Metric': display_name,
                    f'{analysis_response.team.abbreviation}': f"{team_val:.2f}",
                    'League Avg': f"{league_val:.2f}",
                    'Difference': pct_diff,
                    'Rank': rank_display
                })
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(
                comparison_df,
                width="stretch",
                hide_index=True,
                placeholder="-",
                column_config={
                    'Difference': st.column_config.NumberColumn(
                        'Difference',
                        format='%+.2f%%',
                        help=(
                            'Percentage difference from the league average: '
                            '(team − league average) ÷ league average × 100. '
                            'A dash means the league average is zero, so this percentage is undefined. '
                            'Positive values mean more, which is not always better.'
                        ),
                    ),
                },
                height=len(comparison_df) * 35 + 38,
            )
            figure = ChartGenerationService.create_league_comparison_chart(
                comparison_df, analysis_response.team.abbreviation,
            )
            st.plotly_chart(figure, theme="streamlit", width="stretch")

            # Rankings Overview
            st.markdown("### Rankings Overview")
            
            if rankings:
                col1, col2 = st.columns(2)
                ranked_metrics = sorted(rankings.items(), key=lambda item: item[1].rank)
                
                with col1:
                    st.markdown("#### Highest-ranked metrics")
                    
                    for metric, perf_rank in ranked_metrics[:5]:
                        metric_display = get_metric_label(metric, season=True)
                        st.markdown(f"**{metric_display}**: #{perf_rank.rank}/{perf_rank.total_teams}")
                
                with col2:
                    st.markdown("#### Lowest-ranked metrics")
                    
                    for metric, perf_rank in sorted(rankings.items(), key=lambda item: item[1].rank, reverse=True)[:5]:
                        metric_display = get_metric_label(metric, season=True)
                        st.markdown(f"**{metric_display}**: #{perf_rank.rank}/{perf_rank.total_teams}")
    
    def _render_export_tab(self, analysis_response: TeamAnalysisResponse):
        """Render the data export tab."""
        st.subheader("Export Analysis Data")
        
        st.markdown("Download your team's analysis data in various formats:")
        # Deferred downloads run on a worker thread. Capture independent data
        # now rather than reading mutable session state inside those callbacks.
        snapshot = deepcopy(analysis_response)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**CSV Format**")
            st.markdown("Game-by-game data in spreadsheet format")
            
            st.download_button(
                label="Download CSV",
                data=partial(self._export_service.export_to_csv, snapshot),
                file_name=f"{analysis_response.team.abbreviation}_{analysis_response.season.year}_stats.csv",
                mime="text/csv",
                width="stretch",
                on_click="ignore",
            )
        
        with col2:
            st.markdown("**Excel Format**")
            st.markdown("Game-by-game data in Excel format")
            
            if self._export_service.excel_available:
                st.download_button(
                    label="Download Excel",
                    data=partial(self._export_service.export_to_excel, snapshot),
                    file_name=f"{analysis_response.team.abbreviation}_{analysis_response.season.year}_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                    on_click="ignore",
                )
            else:
                st.button(
                    label="Excel (Not Available)",
                    disabled=True,
                    width="stretch",
                    help="Install openpyxl library to enable Excel export: pip install openpyxl"
                )
        
        with col3:
            st.markdown("**JSON Format**")
            st.markdown("Structured data for developers")
            
            st.download_button(
                label="Download JSON",
                data=partial(self._export_service.export_to_json, snapshot),
                file_name=f"{analysis_response.team.abbreviation}_{analysis_response.season.year}_data.json",
                mime="application/json",
                width="stretch",
                on_click="ignore",
            )
        
        st.divider()
        
        # Data preview
        st.subheader("Data Preview")
        
        preview_options = ["Game Log", "Season Summary", "Rankings"]
        previous_preview = st.session_state.get("analysis_export_preview", "Game Log")
        preview_option = st.selectbox(
            "Select data to preview:",
            preview_options,
            index=preview_options.index(previous_preview),
            key="_analysis_export_preview",
        )
        # Hidden tabs don't render their widgets. Keep the preference in a
        # separate key so Streamlit's widget cleanup doesn't reset it.
        st.session_state["analysis_export_preview"] = preview_option
        
        if preview_option == "Game Log":
            game_data = self._export_service._prepare_game_data(analysis_response)
            if not game_data.empty:
                st.dataframe(game_data.head(10), width="stretch")
                if len(game_data) > 10:
                    st.info(f"Showing first 10 of {len(game_data)} games. Download full data using buttons above.")
        
        elif preview_option == "Season Summary":
            season_data = self._export_service._prepare_season_summary(analysis_response)
            if not season_data.empty:
                st.dataframe(season_data, width="stretch")
        
        elif preview_option == "Rankings" and analysis_response.rankings:
            rankings_data = self._export_service._prepare_rankings_data(analysis_response)
            if not rankings_data.empty:
                st.dataframe(rankings_data[['Metric', 'Rank', 'Total_Teams']], width="stretch")
    
    def _render_toer_breakdown_tab(self, analysis_response: TeamAnalysisResponse):
        """Render the TOER breakdown showing component scores for each game."""
        st.subheader("TOER Component Breakdown")
        
        if not analysis_response.game_stats:
            st.info("No game data available for TOER breakdown.")
            return

        games_with_weeks = self._games_with_week_labels(analysis_response)
        game_column = 'Week' if games_with_weeks else 'Game'
        labelled_games = games_with_weeks or list(enumerate(analysis_response.game_stats, 1))

        for stats_attribute, total_column in (
            ('offensive_stats', 'TOER'),
            ('defensive_stats', 'TOER Allowed'),
        ):
            if total_column == 'TOER Allowed':
                st.subheader("TOER Allowed Component Breakdown")
            rows = []
            for game_label, game_stats in labelled_games:
                stats = getattr(game_stats, stats_attribute)
                rows.append({
                    game_column: game_label,
                    'Opponent': game_stats.opponent.abbreviation,
                    'Location': game_stats.location.value,
                    **self._toer_component_scores(stats),
                    total_column: stats.toer,
                })
            breakdown_df = pd.DataFrame(rows)
            st.dataframe(
                breakdown_df,
                width="stretch",
                hide_index=True,
                placeholder="-",
                column_config={
                    column: st.column_config.NumberColumn(column, format='%.2f')
                    for column in breakdown_df.columns[3:]
                },
                height=len(breakdown_df) * 35 + 38,
            )

    @staticmethod
    def _toer_component_scores(stats: OffensiveStats) -> dict[str, int]:
        """Use the same domain scorers for offense and opponent offense."""
        return {
            'Yds/Play': TOERCalculator.calculate_yards_per_play_score(stats.yards_per_play),
            'Turnovers': TOERCalculator.calculate_turnovers_score(stats.turnovers),
            'Pass Comp%': TOERCalculator.calculate_completion_pct_score(stats.completion_pct),
            'Rush YPC': TOERCalculator.calculate_rush_ypc_score(stats.rush_ypc),
            'Sacks': TOERCalculator.calculate_sacks_score(stats.sacks),
            '3rd Down%': TOERCalculator.calculate_third_down_score(stats.third_down_pct),
            'Success%': TOERCalculator.calculate_success_rate_score(stats.success_rate),
            '1st Downs': TOERCalculator.calculate_first_downs_score(stats.first_downs),
            'Pts/Drive': TOERCalculator.calculate_ppd_score(stats.points_per_drive),
            'RZ TD%': TOERCalculator.calculate_redzone_score(stats.redzone_td_pct),
            'Pen Yards': TOERCalculator.calculate_penalty_yards_adjustment(stats.penalty_yards),
        }

    def _render_methodology_tab(self, analysis_response: TeamAnalysisResponse):
        """Render the methodology documentation tab."""
        self._methodology_renderer.render_methodology_page(analysis_response)

    @staticmethod
    def _games_with_week_labels(analysis_response: TeamAnalysisResponse):
        """Use weeks only when every row has metadata; otherwise use game numbers.

        Falling back as a whole preserves all rows when legacy responses have
        partial metadata instead of silently excluding the unlabelled games.
        """
        if any(game_stat.game is None for game_stat in analysis_response.game_stats):
            return []
        regular_season_weeks = get_regular_season_weeks(analysis_response.season.year)
        games = sorted(
            analysis_response.game_stats,
            key=lambda game_stat: game_stat.game.week,
        )
        return [
            (str(game_stat.game.week) if game_stat.game.week <= regular_season_weeks
             else f"P{game_stat.game.week - regular_season_weeks}", game_stat)
            for game_stat in games
        ]
