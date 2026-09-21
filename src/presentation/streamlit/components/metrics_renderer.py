# src/presentation/streamlit/components/metrics_renderer.py - Metrics display component

import streamlit as st
import html
from typing import Optional, List
from ....application import TeamAnalysisResponse
from ....domain import Team, Season, SeasonStats, PerformanceRank, TeamRecord, NFLMetrics
from ....utils.season_utils import get_regular_season_games
from ....utils.team_code_mapper import get_team_display_name
from ..metric_labels import get_metric_label
from .team_branding import get_team_logo_data_uri, get_team_mark_abbreviation


class MetricsRenderer:
    """Renders season metrics with numeric league rankings."""
    
    def __init__(self):
        pass
    
    def render_team_header(self, team: Team, season: Season, season_type_filter: str = "ALL", 
                          team_record: Optional[TeamRecord] = None, game_stats: Optional[List] = None,
                          season_stats: Optional['SeasonStats'] = None):
        """Render an integrated page header with season context and ratings."""
        season_type_text = {
            "ALL": "All games",
            "REG": "Regular season",
            "POST": "Playoffs",
        }.get(season_type_filter, "All games")
        metadata = [str(season.year), season_type_text]

        # Keep the full season record even when the statistics are filtered.
        # Explicit record labels distinguish it from the selected game scope.
        if team_record:
            record_items = []
            ties = getattr(team_record, 'regular_season_ties', 0)
            total_reg_games = team_record.regular_season_wins + team_record.regular_season_losses + ties
            total_playoff_games = team_record.playoff_wins + team_record.playoff_losses
            label_regular_record = season_type_filter != "REG" or total_playoff_games > 0
            if total_reg_games > 0:
                regular_record = f"{team_record.regular_season_wins}-{team_record.regular_season_losses}"
                if ties:
                    regular_record += f"-{ties}"
                if label_regular_record:
                    regular_record += " regular season"
                record_items.append(regular_record)
                expected_games = get_regular_season_games(season.year)
                if total_reg_games < expected_games:
                    games_label = "regular-season games" if label_regular_record else "games"
                    record_items.append(f"{total_reg_games} of {expected_games} {games_label}")
            if total_playoff_games > 0:
                record_items.append(f"{team_record.playoff_wins}-{team_record.playoff_losses} playoffs")
            metadata.extend(record_items or ["Season has not started"])
        elif game_stats:
            games_count = len(game_stats)
            metadata.append(f"{games_count} {'game' if games_count == 1 else 'games'} analyzed")
        else:
            metadata.append("No data available")

        safe_name = html.escape(get_team_display_name(team.abbreviation, season.year))
        metadata_html = ''.join(f'<span>{html.escape(item)}</span>' for item in metadata)

        # Bundled marks need no runtime image requests. The adjacent heading
        # identifies the team for screen readers, so the mark is decorative.
        logo_uri = get_team_logo_data_uri(team.abbreviation, season.year)
        if logo_uri:
            team_mark = f'<img src="{html.escape(logo_uri, quote=True)}" alt="" width="48" height="48">'
        else:
            abbreviation = html.escape(get_team_mark_abbreviation(team.abbreviation, season.year))
            team_mark = f'<span class="season-team-monogram">{abbreviation}</span>'
        
        # Use the same typography for both ratings without qualitative colors.
        toer_display = ""
        if season_stats is not None:
            ratings = (
                ("Offense", "TOER", season_stats.toer,
                 "Total Offensive Efficiency Rating; higher is better"),
                ("Defense", "TOER allowed", season_stats.toer_allowed,
                 "Opponent Total Offensive Efficiency Rating; lower is better"),
            )
            rating_items = []
            for side, label, value, description in ratings:
                rating_items.append(
                    f'<div class="season-rating" title="{html.escape(description)}">'
                    f'<div class="season-rating-label">{side} · {label}</div>'
                    f'<div class="season-rating-value">{value:.1f}</div>'
                    '</div>'
                )
            toer_display = '<div class="season-team-ratings">' + ''.join(rating_items) + '</div>'

        header_html = f"""
        <div class="season-header">
        <header class="season-team-header">
            <div class="season-team-identity">
                <div class="season-team-logo" aria-hidden="true">{team_mark}</div>
                <div class="season-team-name">
                    <h2>{safe_name}</h2>
                    <div class="season-team-metadata">{metadata_html}</div>
                </div>
            </div>
            {toer_display}
        </header>
        </div>
        """
        
        st.markdown(header_html, unsafe_allow_html=True)
    
    def render_team_info_sidebar(self, team: Team, team_record: Optional[TeamRecord] = None):
        """Render team information sidebar."""
        if team_record:
            st.subheader("Team Record")
            
            # Regular season record
            total_reg_games = team_record.regular_season_wins + team_record.regular_season_losses + getattr(team_record, 'regular_season_ties', 0)
            if total_reg_games > 0:
                # Win percentage: ties count as 0.5 wins
                ties = getattr(team_record, 'regular_season_ties', 0)
                reg_pct = (team_record.regular_season_wins + 0.5 * ties) / total_reg_games
                
                if ties > 0:
                    record_str = f"{team_record.regular_season_wins}-{team_record.regular_season_losses}-{ties}"
                else:
                    record_str = f"{team_record.regular_season_wins}-{team_record.regular_season_losses}"
                
                st.metric(
                    "Regular Season", 
                    record_str,
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
        """Group related season metrics with equal visual weight."""
        season_stats = analysis_response.season_stats
        rankings = analysis_response.rankings or {}
        metric_groups = (
            ("Efficiency", (
                NFLMetrics.POINTS_PER_DRIVE,
                NFLMetrics.AVG_YARDS_PER_PLAY,
                NFLMetrics.SUCCESS_RATE,
            )),
            ("Passing & rushing", (
                NFLMetrics.COMPLETION_PCT,
                NFLMetrics.RUSH_YPC,
            )),
            ("Conversions", (
                NFLMetrics.THIRD_DOWN_PCT,
                NFLMetrics.REDZONE_TD_PCT,
                NFLMetrics.FIRST_DOWNS_PER_GAME,
            )),
            ("Negative plays", (
                NFLMetrics.TURNOVERS_PER_GAME,
                NFLMetrics.SACKS_PER_GAME,
                NFLMetrics.PENALTY_YARDS_PER_GAME,
            )),
        )

        groups_html = []
        for title, metrics in metric_groups:
            metrics_html = []
            for metric in metrics:
                label = get_metric_label(metric.key, season=True)
                value = f"{getattr(season_stats, metric.key):.2f}"
                if metric.unit == "%":
                    value += "%"
                metrics_html.append(self._metric_with_rank_html(label, value, rankings.get(metric.key)))
            groups_html.append(
                '<section class="season-metric-group">'
                f'<h3>{html.escape(title)}</h3>'
                + ''.join(metrics_html) + '</section>'
            )

        st.markdown(
            '<div class="season-overview" role="region" aria-label="Season statistics">'
            '<div class="season-overview-heading">Season overview</div>'
            f'<div class="season-metrics">{"".join(groups_html)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    @staticmethod
    def _metric_with_rank_html(
        label: str, value: str, performance_rank: Optional[PerformanceRank] = None
    ) -> str:
        """Format a metric consistently, with or without a league ranking."""
        rank_html = ""
        if performance_rank is not None:
            safe_rank = html.escape(str(performance_rank.rank))
            safe_total = html.escape(str(performance_rank.total_teams))
            rank_html = (
                f'<span class="season-metric-rank" '
                f'aria-label="Rank {safe_rank} of {safe_total} teams">'
                f'#{safe_rank}/{safe_total}</span>'
            )
        return (
            '<div class="season-metric">'
            f'<div class="season-metric-label">{html.escape(str(label))}</div>'
            '<div class="season-metric-reading">'
            f'<span class="season-metric-value">{html.escape(str(value))}</span>'
            f'{rank_html}</div></div>'
        )
