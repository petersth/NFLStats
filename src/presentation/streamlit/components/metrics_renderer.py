# src/presentation/streamlit/components/metrics_renderer.py - Metrics display component

import streamlit as st
import html
from math import isfinite
from typing import Optional, List
from ....application import TeamAnalysisResponse
from ....domain import Team, Season, SeasonStats, PerformanceRank, TeamRecord, NFLMetrics
from ....utils.team_code_mapper import get_team_display_name
from .metric_details import metric_details_html
from ..metric_labels import get_metric_label
from .team_branding import get_team_logo_data_uri, get_team_mark_abbreviation, get_team_banner_colors


class MetricsRenderer:
    """Renders season metrics with numeric league rankings."""
    
    def __init__(self):
        pass
    
    def render_team_header(self, team: Team, season: Season, season_type_filter: str = "ALL", 
                          team_record: Optional[TeamRecord] = None, game_stats: Optional[List] = None,
                          season_stats: Optional['SeasonStats'] = None,
                          toer_rank: Optional[PerformanceRank] = None,
                          league_toer: Optional[float] = None,
                          toer_allowed_rank: Optional[PerformanceRank] = None,
                          league_toer_allowed: Optional[float] = None):
        """Present offensive and allowed TOER with matching score layouts."""
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
            if total_playoff_games > 0:
                record_items.append(f"{team_record.playoff_wins}-{team_record.playoff_losses} playoffs")
            metadata.extend(record_items or ["Season has not started"])
        elif game_stats and season_stats is None:
            games_count = len(game_stats)
            metadata.append(f"{games_count} {'game' if games_count == 1 else 'games'} analyzed")
        elif season_stats is None:
            metadata.append("No data available")

        safe_name = html.escape(get_team_display_name(team.abbreviation, season.year))
        metadata_html = ''.join(f'<span>{html.escape(item)}</span>' for item in metadata)

        # Bundled marks need no runtime image requests. The adjacent heading
        # identifies the team for screen readers, so the mark is decorative.
        logo_uri = get_team_logo_data_uri(team.abbreviation, season.year)
        if logo_uri:
            team_mark = f'<img src="{html.escape(logo_uri, quote=True)}" alt="" width="72" height="72">'
        else:
            abbreviation = html.escape(get_team_mark_abbreviation(team.abbreviation, season.year))
            team_mark = f'<span class="season-team-monogram">{abbreviation}</span>'
        
        toer_display = ""
        sample_html = ""
        if season_stats is not None:
            games_count = season_stats.games_played
            sample = f'{games_count} {"game" if games_count == 1 else "games"}'
            sample_html = f'<span class="season-sample">{sample}</span>'
            ratings = (
                ('TOER', season_stats.toer, toer_rank, league_toer, 'primary', 'h1',
                 'Offensive TOER', 'Total Offensive Efficiency Rating', 'Higher', '↑'),
                ('TOER allowed', season_stats.toer_allowed, toer_allowed_rank, league_toer_allowed,
                 'secondary', 'h2', 'Defensive TOER allowed', 'Opponent offensive efficiency', 'Lower', '↓'),
            )
            rating_items = []
            for label, value, rank, average, style, heading, accessible_name, description, direction, arrow in ratings:
                rank_text = f'{rank.rank} of {rank.total_teams}' if rank is not None else '—'
                average_text = f'{average:.1f}' if average is not None and isfinite(average) else '—'
                rating_items.append(
                    f'<section class="season-rating season-rating-{style}" aria-label="{accessible_name}">'
                    f'<{heading} title="{description}; {direction.lower()} is better">{label} '
                    f'<span class="season-rating-direction" aria-label="{direction} is better">{arrow}</span></{heading}>'
                    f'<div class="season-rating-value">{value:.1f}</div>'
                    '<div class="season-rating-context">'
                    f'<span title="League rank">Rank <strong>{rank_text}</strong></span>'
                    f'<span title="League average">Avg <strong>{average_text}</strong></span></div></section>'
                )
            toer_display = '<div class="season-team-ratings">' + ''.join(rating_items) + '</div>'

        palette = get_team_banner_colors(team.abbreviation, season.year)
        banner_style = ";".join(f"--team-{key}:{value}" for key, value in palette.items())
        header_html = f"""
        <div class="season-header">
        <header class="season-team-header" style="{banner_style}">
            <div class="season-team-topline">
            <div class="season-team-identity">
                <div class="season-team-logo" aria-hidden="true">{team_mark}</div>
                <div class="season-team-name">
                    <h2>{safe_name}</h2>
                    <div class="season-team-metadata">{metadata_html}{sample_html}</div>
                </div>
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
        """Render eleven equally sized, individually explorable metric cards."""
        season_stats = analysis_response.season_stats
        rankings = analysis_response.rankings or {}
        league_averages = analysis_response.league_averages or {}
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

        groups = []
        for title, metrics in metric_groups:
            cards = []
            for metric in metrics:
                label = get_metric_label(metric.key, season=True)
                value = f"{getattr(season_stats, metric.key):.2f}"
                if metric.unit == "%":
                    value += "%"
                average = league_averages.get(metric.key)
                average_display = (
                    f'{average:.2f}{"%" if metric.unit == "%" else ""}'
                    if average is not None and isfinite(average) else None
                )
                cards.append(self._metric_with_rank_html(
                    label, value, rankings.get(metric.key),
                    league_average=average_display, higher_is_better=metric.higher_is_better,
                    detail_html=metric_details_html(metric, analysis_response),
                ))
            groups.append(
                f'<section class="season-metric-group" aria-label="{html.escape(title)}">'
                f'<h3>{html.escape(title)}</h3>{"".join(cards)}</section>'
            )

        st.markdown(
            '<div class="season-overview" role="region" aria-label="Season statistics">'
            '<div class="season-overview-heading"><h2>Offensive metrics</h2>'
            '<div class="season-overview-legend" aria-label="League rank color key">'
            '<span><i class="rank-key is-strong"></i>Top quarter</span>'
            '<span><i class="rank-key is-neutral"></i>Middle half</span>'
            '<span><i class="rank-key is-weak"></i>Bottom quarter</span></div></div>'
            f'<div class="season-metrics">{"".join(groups)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    @staticmethod
    def _metric_with_rank_html(
        label: str, value: str, performance_rank: Optional[PerformanceRank] = None,
        *, league_average: Optional[str] = None, higher_is_better: bool = True,
        detail_html: str = "",
    ) -> str:
        """Format a metric consistently, with or without a league ranking."""
        tone = 'is-neutral'
        rank_html = '<span class="season-metric-rank">Rank unavailable</span>'
        rail_html = (
            '<div class="season-rank-rail is-unavailable" aria-hidden="true">'
            '<div class="season-rank-track is-unavailable"></div></div>'
        )
        if performance_rank is not None:
            rank = performance_rank.rank
            suffix = "th" if 11 <= rank % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
            safe_rank = html.escape(str(rank))
            safe_total = html.escape(str(performance_rank.total_teams))
            rank_html = (
                f'<span class="season-metric-rank" title="{safe_rank}{suffix} of {safe_total}" '
                f'aria-label="Rank {safe_rank} of {safe_total} teams">'
                f'<strong>{safe_rank}<small>{suffix}</small></strong>'
                f'<span>of {safe_total}</span></span>'
            )
            total = performance_rank.total_teams
            if total > 1:
                tone = 'is-strong' if rank / total <= 0.25 else 'is-weak' if rank / total > 0.75 else 'is-neutral'
            if total >= 1:
                # Each grid cell is one rank. The marker belongs to that cell,
                # so neither its position nor the fill can land between ranks.
                segments = ''.join(
                    f'<span class="season-rank-segment'
                    f'{" is-filled" if slot_rank >= rank else ""}'
                    f'{" is-current" if slot_rank == rank else ""}" '
                    f'data-rank="{slot_rank}" title="Rank {slot_rank} of {total}"></span>'
                    for slot_rank in range(total, 0, -1)
                )
                rail_html = (
                    '<div class="season-rank-rail" aria-hidden="true">'
                    f'<span class="season-rank-endpoint">{total}</span>'
                    f'<div class="season-rank-track" style="--rank-count:{total}">'
                    f'{segments}</div><span class="season-rank-endpoint">1</span></div>'
                )
        average_html = (
            f'League avg <strong>{html.escape(league_average)}</strong>'
            if league_average is not None else 'League avg unavailable'
        )
        direction = 'Higher is better' if higher_is_better else 'Lower is better'
        safe_value = html.escape(str(value))
        if safe_value.endswith('%'):
            safe_value = safe_value[:-1] + '<span class="season-metric-unit">%</span>'
        opening = f'<details class="season-metric {tone}"><summary>' if detail_html else f'<div class="season-metric {tone}">'
        closing = (
            f'</summary><div class="season-metric-detail">{detail_html}</div></details>'
            if detail_html else '</div>'
        )
        disclosure = (
            '<svg class="metric-chevron" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            '<path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" stroke-width="1.75" '
            'stroke-linecap="round" stroke-linejoin="round" /></svg>'
        ) if detail_html else ''
        return (
            opening
            + f'<div class="season-metric-label">{html.escape(str(label))}{disclosure}</div>'
            '<div class="season-metric-reading">'
            f'<span class="season-metric-value">{safe_value}</span>'
            f'{rank_html}</div>'
            f'<div class="season-metric-context"><span>{average_html}</span>'
            f'<span title="{direction}" aria-label="{direction}">{"↑" if higher_is_better else "↓"} better</span>'
            f'</div>{rail_html}{closing}'
        )
