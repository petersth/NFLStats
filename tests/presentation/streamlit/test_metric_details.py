"""Input explanations must use game scores, including rounding and deductions."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from src.domain.entities import OffensiveStats, Team
from src.domain.metrics import NFLMetrics
from src.presentation.streamlit.components.metric_details import metric_details_html


def response_with_values(field, values):
    return SimpleNamespace(
        game_stats=[
            SimpleNamespace(
                game=None, opponent=Team.from_abbreviation('DET'),
                offensive_stats=replace(OffensiveStats.empty(), **{field: value}),
            )
            for value in values
        ],
        configuration={},
    )


@pytest.mark.parametrize('metric,field,values,points,average', [
    (NFLMetrics.AVG_YARDS_PER_PLAY, 'yards_per_play', [5.4949, 5.4951], [8, 9], '+8.50'),
    (NFLMetrics.POINTS_PER_DRIVE, 'points_per_drive', [1.79, 2.4], [0, 10], '+5.00'),
    (NFLMetrics.SUCCESS_RATE, 'success_rate', [39, 47], [0, 10], '+5.00'),
    (NFLMetrics.COMPLETION_PCT, 'completion_pct', [62, 67.5], [0, 10], '+5.00'),
    (NFLMetrics.RUSH_YPC, 'rush_ypc', [4.19, 4.7], [0, 10], '+5.00'),
    (NFLMetrics.THIRD_DOWN_PCT, 'third_down_pct', [32, 43], [0, 10], '+5.00'),
    (NFLMetrics.REDZONE_TD_PCT, 'redzone_td_pct', [56, 63], [0, 10], '+5.00'),
    (NFLMetrics.FIRST_DOWNS_PER_GAME, 'first_downs', [16, 22], [0, 10], '+5.00'),
    (NFLMetrics.TURNOVERS_PER_GAME, 'turnovers', [0, 3], [10, -3], '+3.50'),
    (NFLMetrics.SACKS_PER_GAME, 'sacks', [4, 5], [-1, -3], '-2.00'),
    (NFLMetrics.PENALTY_YARDS_PER_GAME, 'penalty_yards', [0, 90], [5, -9], '-2.00'),
])
def test_details_average_actual_game_scores(metric, field, values, points, average):
    # No season_stats attribute: applying thresholds to an aggregate is incorrect.
    rendered = metric_details_html(metric, response_with_values(field, values))
    assert f'<strong>{average}<small> pts / game</small></strong>' in rendered
    for index, (value, score) in enumerate(zip(values, points), 1):
        unit = '%' if metric.unit == '%' else ''
        assert (
            f'<tr><td>G{index}</td><td>DET</td><td>{value:.2f}{unit}</td>'
            f'<td class="metric-game-points">{score:+d}</td></tr>'
        ) in rendered
    assert 'before each game’s total is limited to 0–100' in rendered


@pytest.mark.parametrize('values', [[], [0, float('nan')], [0, 1.5]])
def test_missing_or_invalid_game_values_never_produce_a_partial_average(values):
    rendered = metric_details_html(
        NFLMetrics.TURNOVERS_PER_GAME, response_with_values('turnovers', values),
    )
    assert '<strong>—<small> pts / game</small></strong>' in rendered
    assert 'complete set of valid game values' in rendered
    assert '<polyline' not in rendered
    if values:
        assert '<td>G1</td>' in rendered and '<td>G2</td>' in rendered


def test_penalty_adjustment_preserves_positive_and_negative_scoring_range():
    rendered = metric_details_html(
        NFLMetrics.PENALTY_YARDS_PER_GAME, response_with_values('penalty_yards', [0]),
    )
    assert '<strong>+5.00<small> pts / game</small></strong>' in rendered
    assert '-10 to +5' in rendered
    assert 'Use the first matching rule.' in rendered
    assert '1 selected game,' in rendered


def test_details_explain_settings_used_for_selected_analysis():
    response = response_with_values('success_rate', [45])
    response.configuration = {
        'include_qb_kneels_success_rate': False,
        'include_spikes_success_rate': True,
    }
    rendered = metric_details_html(NFLMetrics.SUCCESS_RATE, response)
    assert 'Excludes QB kneels. Includes QB spikes.' in rendered
