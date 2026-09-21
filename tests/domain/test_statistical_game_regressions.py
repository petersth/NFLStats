"""Offline regressions from public nflverse play-by-play release files.

Source: https://github.com/nflverse/nflverse-data/releases/tag/pbp (2026-09-20).
The offensive_drive_context fixture contains four complete team-game possession
extracts and three penalty-only drive sequences. Its drive expectations follow
the recorded play/down context, not an independent official drive-total audit.
"""
from pathlib import Path

import pandas as pd
import pytest

from src.domain.nfl_stats_calculator import NFLStatsCalculator
from src.utils.configuration_utils import apply_configuration_to_data

FIXTURES = Path(__file__).parents[1] / 'fixtures'


def game_rows(filename, game_id, team):
    data = pd.read_csv(FIXTURES / filename)
    return data[(data.game_id == game_id) & (data.posteam == team)].copy()


@pytest.mark.parametrize('game,team,conversions,attempts,first_downs', [
    ('2024_01_LA_DET', 'DET', 6, 13, 21),
    ('2024_01_ARI_BUF', 'ARI', 7, 13, 18),
    ('2024_01_WAS_TB', 'WAS', 2, 8, 22),
])
def test_official_down_awards_with_penalties(game, team, conversions, attempts, first_downs):
    data = game_rows('official_down_penalties.csv', game, team)
    stats = NFLStatsCalculator()._calculate_down_stats(data, team)
    assert stats['third_down_conversions'] == conversions
    assert stats['third_down_attempts'] == attempts
    assert stats['third_down_pct'] == pytest.approx(100 * conversions / attempts)
    assert stats['third_down_rush_conversions'] + stats['third_down_pass_conversions'] == conversions
    assert stats['first_downs_total'] == first_downs
    assert sum(stats[f'first_downs_{kind}'] for kind in ['rush', 'pass', 'penalty']) == first_downs


@pytest.mark.parametrize('game,team,touchdowns,trips', [
    ('2024_01_GB_PHI', 'GB', 1, 4),
    ('2025_03_DET_BAL', 'BAL', 2, 4),
    ('2026_02_NO_BAL', 'NO', 1, 2),
])
def test_conversion_penalties_do_not_establish_redzone_possession(game, team, touchdowns, trips):
    data = game_rows('redzone_conversion_context.csv', game, team)
    stats = NFLStatsCalculator()._calculate_redzone_only(data, team)
    assert stats['redzone_touchdowns'] == touchdowns
    assert stats['redzone_trips'] == trips
    assert stats['redzone_td_pct'] == pytest.approx(100 * touchdowns / trips)


def test_offensive_penalty_can_establish_redzone_trip_before_scoring_outside_it():
    # A false start while possessing the opponent's 19 moves the next snap out
    # of the red zone. This is different from a conversion penalty with no down.
    data = pd.DataFrame([
        dict(game_id='game', drive=1, yardline_100=19, down=1, play_type='no_play', touchdown=0, td_team=None),
        dict(game_id='game', drive=1, yardline_100=24, down=1, play_type='pass', touchdown=1, td_team='DET'),
    ])
    stats = NFLStatsCalculator()._calculate_redzone_only(data, 'DET')
    assert stats['redzone_trips'] == 1
    assert stats['redzone_touchdowns'] == 1


@pytest.mark.parametrize('game,team,interceptions,fumbles', [
    ('2024_01_NE_CIN', 'NE', 0, 0),  # The opposing punt returner loses it.
    ('2024_11_HOU_DAL', 'DAL', 0, 1),  # Two fumbles, only the second lost.
    ('2024_09_HOU_NYJ', 'NYJ', 0, 1),  # Through the end zone, no recovery row.
    ('2024_15_CIN_TEN', 'TEN', 0, 2),  # Two separate plays; one defender re-fumbles.
    ('2025_14_PHI_LAC', 'PHI', 1, 1),  # INT, return fumble, offensive recovery/loss.
    ('2025_17_SEA_CAR', 'SEA', 0, 1),  # Three fumbles in one play, one SEA loss.
])
def test_fumbles_are_charged_to_the_team_that_lost_possession(game, team, interceptions, fumbles):
    data = game_rows('turnover_attribution.csv', game, team)
    assert NFLStatsCalculator()._calculate_turnover_stats(data, team) == {
        'interceptions': interceptions,
        'fumbles_lost': fumbles,
        'total_turnovers': interceptions + fumbles,
    }


def test_official_third_down_flags_still_respect_independent_kneel_settings():
    data = pd.DataFrame([dict(
        play_type='qb_kneel', down=3, rush_attempt=1, pass_attempt=0,
        two_point_attempt=0, third_down_converted=0, third_down_failed=1,
    )])
    calculator = NFLStatsCalculator()
    for include_success, expected in [(True, 1), (False, 0)]:
        configured = apply_configuration_to_data(data, {
            'include_qb_kneels_rushing': True,
            'include_qb_kneels_success_rate': include_success,
        })
        assert calculator._calculate_down_stats(configured, 'DET')['third_down_attempts'] == expected


@pytest.mark.parametrize('game,team,points,drives,toer', [
    ('2024_04_NO_ATL', 'NO', 24, 9, 76),
    ('2024_18_WAS_DAL', 'DAL', 19, 10, 40),
    ('2025_02_TB_HOU', 'HOU', 19, 10, 36),
    ('2007_03_IND_HOU', 'HOU', 17, 9, None),
])
def test_kickoff_administrative_rows_do_not_create_offensive_drives(game, team, points, drives, toer):
    # The modern games finish with a kickoff and END GAME row, without an
    # offensive snap. The historical game opens with a kickoff penalty followed
    # by a return TD and PAT; none of those plays belong in offensive efficiency.
    data = game_rows('offensive_drive_context.csv', game, team)
    calculator = NFLStatsCalculator()
    scoring = calculator._calculate_scoring_and_redzone_stats(data, team)
    assert scoring['points'] == points
    assert scoring['drives'] == drives
    assert scoring['points_per_drive'] == pytest.approx(points / drives)
    if toer is not None:
        assert calculator.calculate_offensive_stats(data, team).toer == toer


@pytest.mark.parametrize('game,team', [
    ('2024_01_DEN_SEA', 'SEA'),  # Holding in the end zone: safety.
    ('2025_06_DEN_NYJ', 'DEN'),  # Holding in the end zone: safety.
    ('2025_04_CAR_NE', 'CAR'),  # Accepted penalty as the half ends.
])
def test_penalty_only_offensive_possessions_remain_drives(game, team):
    data = game_rows('offensive_drive_context.csv', game, team)
    assert data['play_type'].eq('no_play').all()
    stats = NFLStatsCalculator()._calculate_scoring_and_redzone_stats(data, team)
    assert stats['drives'] == 1
    assert stats['points'] == 0
    assert stats['points_per_drive'] == 0
