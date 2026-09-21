"""Offensive and defensive rating context must come from their own values."""

from types import SimpleNamespace

import pytest

from src.utils.league_stats_utils import calculate_league_averages, extract_stats_for_averaging
from src.utils.nfl_metrics import AVERAGING_METRICS
from src.utils.ranking_utils import calculate_all_rankings, calculate_team_rankings


def test_toer_allowed_ranks_lowest_first_and_preserves_competition_ties():
    teams = {
        'DET': SimpleNamespace(toer=80, toer_allowed=20),
        'GB': SimpleNamespace(toer=60, toer_allowed=35),
        'CHI': SimpleNamespace(toer=70, toer_allowed=20),
        'MIN': SimpleNamespace(toer=90, toer_allowed=80),
    }
    rankings = calculate_all_rankings(teams)
    assert {team: ranks['toer_allowed'] for team, ranks in rankings.items()} == {
        'DET': 1, 'GB': 3, 'CHI': 1, 'MIN': 4,
    }
    assert {team: ranks['toer'] for team, ranks in rankings.items()} == {
        'DET': 2, 'GB': 4, 'CHI': 3, 'MIN': 1,
    }
    for team in teams:
        assert calculate_team_rankings(team, teams) == rankings[team]


def test_allowed_average_uses_allowed_values_from_the_selected_teams():
    rows = []
    for offense, allowed in [(80, 20), (60, 35), (70, 20), (90, 80)]:
        stats = dict.fromkeys(AVERAGING_METRICS, 0.0)
        stats.update(toer=offense, toer_allowed=allowed, games_played=2)
        rows.append(extract_stats_for_averaging(SimpleNamespace(**stats)))

    averages = calculate_league_averages(rows)
    assert averages['toer'] == pytest.approx(75)
    assert averages['toer_allowed'] == pytest.approx(38.75)
    assert calculate_league_averages(rows[:2])['toer_allowed'] == pytest.approx(27.5)


def test_rating_averages_weight_games_when_teams_have_unequal_schedules():
    # A vs B: TOER 80–20. A vs C: TOER 40–60.
    # Four offensive performances average 50, on either side of the ball.
    rows = [
        {'games_played': 2, 'toer': 60, 'toer_allowed': 40, 'points_per_drive': 3},
        {'games_played': 1, 'toer': 20, 'toer_allowed': 80, 'points_per_drive': 1},
        {'games_played': 1, 'toer': 60, 'toer_allowed': 40, 'points_per_drive': 2},
    ]
    averages = calculate_league_averages(rows)
    assert averages['toer'] == pytest.approx(50)
    assert averages['toer_allowed'] == pytest.approx(50)
    assert averages['points_per_drive'] == pytest.approx(2)

    # A selected subset still uses its own allowed scores, not a copied TOER.
    subset = calculate_league_averages(rows[:2])
    assert subset['toer'] == pytest.approx(140 / 3)
    assert subset['toer_allowed'] == pytest.approx(160 / 3)


def test_rating_averages_exclude_unplayed_teams_and_handle_empty_seasons():
    unplayed = {'games_played': 0, 'toer': 0, 'toer_allowed': 0}
    played = {'games_played': 1, 'toer': 70, 'toer_allowed': 30}
    averages = calculate_league_averages([unplayed, played])
    assert averages['toer'] == 70
    assert averages['toer_allowed'] == 30
    empty = calculate_league_averages([unplayed])
    assert empty['toer'] == empty['toer_allowed'] == 0
    assert calculate_league_averages([]) == {}
