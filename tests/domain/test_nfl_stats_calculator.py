import pandas as pd
import pytest

from src.domain.entities import Team
from src.domain.nfl_stats_calculator import NFLStatsCalculator


@pytest.mark.parametrize("conversion", [
    {"play_type": "extra_point", "yardline_100": 15,
     "two_point_attempt": 0, "extra_point_result": "good"},
    {"play_type": "pass", "yardline_100": 2,
     "two_point_attempt": 1, "two_point_conv_result": "success"},
    {"play_type": "run", "yardline_100": 2,
     "two_point_attempt": 1, "two_point_conv_result": "failure"},
])
@pytest.mark.parametrize("touchdown_distance", [27, 10])
def test_conversions_do_not_create_redzone_trips(conversion, touchdown_distance):
    data = pd.DataFrame([
        {
            "game_id": "game-1", "drive": 1,
            "yardline_100": touchdown_distance, "play_type": "pass",
            "touchdown": 1, "td_team": "DET", "two_point_attempt": 0,
        },
        {
            "game_id": "game-1", "drive": 1,
            "touchdown": 0, "td_team": None, **conversion,
        },
    ])

    stats = NFLStatsCalculator()._calculate_scoring_and_redzone_stats(data, "DET")

    expected_trips = int(touchdown_distance <= 20)
    assert stats["redzone_trips"] == expected_trips
    assert stats["redzone_touchdowns"] == expected_trips
    assert stats["redzone_field_goals"] == 0
    assert stats["redzone_failed"] == 0
    assert stats["redzone_td_pct"] == (100.0 if expected_trips else 0.0)
    assert stats["touchdowns"] == 1
    assert stats["points"] == 6 + (
        1 if conversion.get("extra_point_result") == "good" else
        2 if conversion.get("two_point_conv_result") == "success" else 0
    )


def test_calculate_game_stats_builds_nested_game_stats():
    data = pd.DataFrame([{
        "season": 2025,
        "season_type": "REG",
        "week": 1,
        "game_id": "2025_01_GB_DET",
        "game_date": "2025-09-07",
        "home_team": "DET",
        "away_team": "GB",
        "posteam": "DET",
        "defteam": "GB",
        "yardline_100": 60,
        "down": 1,
        "ydstogo": 10,
        "drive": 1,
        "play_type": "pass",
        "yards_gained": 6,
        "rush_attempt": 0,
        "pass_attempt": 1,
        "complete_pass": 1,
        "sack": 0,
        "two_point_attempt": 0,
        "touchdown": 0,
        "field_goal_result": None,
        "extra_point_result": None,
        "two_point_conv_result": None,
        "td_team": None,
        "posteam_score_post": 0,
        "defteam_score_post": 0,
        "interception": 0,
        "fumble_lost": 0,
        "first_down": 0,
        "first_down_rush": 0,
        "first_down_pass": 0,
        "first_down_penalty": 0,
        "penalty_team": None,
        "penalty_yards": 0,
        "success": 1,
    }])

    games = NFLStatsCalculator().calculate_game_stats(
        data,
        Team.from_abbreviation("DET"),
    )

    assert len(games) == 1
    assert games[0].game.game_id == "2025_01_GB_DET"
    assert games[0].offensive_stats.total_yards == 6
    assert games[0].defensive_stats.total_yards == 0


def test_game_processor_uses_canonical_touchdown_attribution():
    data = pd.DataFrame([{
        "season": 2025,
        "season_type": "REG",
        "week": 1,
        "game_id": "2025_01_GB_DET",
        "game_date": "2025-09-07",
        "home_team": "DET",
        "away_team": "GB",
        "posteam": "DET",
        "defteam": "GB",
        "yardline_100": 60,
        "down": 1,
        "ydstogo": 10,
        "drive": 1,
        "play_type": "pass",
        "yards_gained": 0,
        "rush_attempt": 0,
        "pass_attempt": 1,
        "complete_pass": 0,
        "sack": 0,
        "two_point_attempt": 0,
        "touchdown": 1,
        "field_goal_result": None,
        "extra_point_result": None,
        "two_point_conv_result": None,
        "td_team": "GB",
        "posteam_score_post": 0,
        "defteam_score_post": 6,
        "interception": 1,
        "fumble_lost": 0,
        "first_down": 0,
        "first_down_rush": 0,
        "first_down_pass": 0,
        "first_down_penalty": 0,
        "penalty_team": None,
        "penalty_yards": 0,
        "success": 0,
    }])
    calculator = NFLStatsCalculator()

    direct = calculator.calculate_offensive_stats(data, "DET")
    processed = calculator.process_all_games(data)["DET"][0].home_team_offensive_stats

    assert direct.points_per_drive == 0.0
    assert processed == direct


def test_scoring_aggregation_preserves_drive_and_redzone_results():
    data = pd.DataFrame([
        {
            "game_id": "game-1", "drive": 1, "yardline_100": 10,
            "touchdown": 1, "td_team": "DET", "extra_point_result": None,
            "two_point_conv_result": None, "field_goal_result": None,
        },
        {
            "game_id": "game-1", "drive": 1, "yardline_100": None,
            "touchdown": 0, "td_team": None, "extra_point_result": "good",
            "two_point_conv_result": None, "field_goal_result": None,
        },
        {
            "game_id": "game-1", "drive": 2, "yardline_100": 15,
            "touchdown": 0, "td_team": None, "extra_point_result": None,
            "two_point_conv_result": None, "field_goal_result": "made",
        },
        {
            "game_id": "game-2", "drive": 1, "yardline_100": 5,
            "touchdown": 1, "td_team": "DET", "extra_point_result": None,
            "two_point_conv_result": None, "field_goal_result": None,
        },
        {
            "game_id": "game-2", "drive": 1, "yardline_100": None,
            "touchdown": 0, "td_team": None, "extra_point_result": None,
            "two_point_conv_result": "success", "field_goal_result": None,
        },
        {
            "game_id": "game-3", "drive": 1, "yardline_100": 4,
            "touchdown": 1, "td_team": "GB", "extra_point_result": None,
            "two_point_conv_result": None, "field_goal_result": None,
        },
    ])

    stats = NFLStatsCalculator()._calculate_scoring_and_redzone_stats(data, "DET")

    assert stats == {
        "drives": 4,
        "touchdowns": 2,
        "extra_points": 1,
        "two_point_conversions": 1,
        "field_goals": 1,
        "points": 18,
        "points_per_drive": 4.5,
        "redzone_trips": 4,
        "redzone_touchdowns": 2,
        "redzone_field_goals": 1,
        "redzone_failed": 1,
        "redzone_td_pct": 50.0,
    }


def test_offensive_stats_filters_offensive_plays_once(monkeypatch):
    data = pd.DataFrame([{
        "game_id": "game-1", "drive": 1, "yardline_100": 60,
        "down": 1, "ydstogo": 10, "yards_gained": 6,
        "rush_attempt": 0, "pass_attempt": 1, "complete_pass": 1,
        "sack": 0, "two_point_attempt": 0, "touchdown": 0,
        "field_goal_result": None, "extra_point_result": None,
        "two_point_conv_result": None, "td_team": None,
        "interception": 0, "fumble_lost": 0, "first_down": 0,
        "first_down_rush": 0, "first_down_pass": 0,
        "first_down_penalty": 0, "posteam": "DET",
        "penalty_team": None, "penalty_yards": 0,
    }])
    calculator = NFLStatsCalculator()
    original = calculator._play_filter.get_offensive_plays
    calls = 0

    def counting_filter(frame):
        nonlocal calls
        calls += 1
        return original(frame)

    monkeypatch.setattr(calculator._play_filter, "get_offensive_plays", counting_filter)

    calculator.calculate_offensive_stats(data, "DET")

    assert calls == 1


@pytest.mark.parametrize('outcome,expected', [
    ({'touchdown': 1, 'td_team': 'DET'}, (1, 0, 0)),
    ({'play_type': 'field_goal', 'field_goal_result': 'made'}, (0, 1, 0)),
    ({'touchdown': 1, 'td_team': 'BUF'}, (0, 0, 1)),
    ({'play_type': 'field_goal', 'field_goal_result': 'missed'}, (0, 0, 1)),
])
def test_redzone_outcome_follows_entire_drive(outcome, expected):
    base = dict(game_id='game-1', drive=1, touchdown=0, td_team=None,
                play_type='pass', two_point_attempt=0, field_goal_result=None)
    data = pd.DataFrame([
        {**base, 'yardline_100': 10},
        {**base, 'yardline_100': 25, **outcome},
        # A matching drive number in another game must not affect this trip.
        {**base, 'game_id': 'game-2', 'yardline_100': 40,
         'touchdown': 1, 'td_team': 'DET'},
    ])
    stats = NFLStatsCalculator()._calculate_redzone_only(data, 'DET')
    assert stats['redzone_trips'] == 1
    assert (stats['redzone_touchdowns'], stats['redzone_field_goals'],
            stats['redzone_failed']) == expected
    assert stats['redzone_td_pct'] == expected[0] * 100.0


@pytest.mark.parametrize('play_type', ['pass', 'run'])
@pytest.mark.parametrize('scoring_team,expected', [('BUF', 0), ('DET', 1)])
def test_third_down_touchdown_requires_offense_to_score(play_type, scoring_team, expected):
    data = pd.DataFrame([dict(
        down=3, rush_attempt=int(play_type == 'run'),
        pass_attempt=int(play_type == 'pass'), two_point_attempt=0,
        first_down=0, touchdown=1, td_team=scoring_team,
    )])
    stats = NFLStatsCalculator()._calculate_down_stats(data, 'DET')
    assert stats['third_down_attempts'] == 1
    assert stats['third_down_conversions'] == expected
    assert stats['third_down_pct'] == expected * 100.0
    breakdown = 'rush' if play_type == 'run' else 'pass'
    assert stats[f'third_down_{breakdown}_conversions'] == expected


@pytest.mark.parametrize('play_type', ['kickoff', 'punt', 'field_goal'])
@pytest.mark.parametrize('conversion', [
    dict(play_type='extra_point', extra_point_result='good', yardline_100=15),
    dict(play_type='run', two_point_attempt=1, two_point_conv_result='success', yardline_100=2),
])
def test_special_teams_scores_and_conversions_do_not_count_as_offense(play_type, conversion):
    base = dict(game_id='game-1', drive=1, touchdown=0, td_team=None,
                play_type='pass', two_point_attempt=0, field_goal_result=None,
                extra_point_result=None, two_point_conv_result=None)
    data = pd.DataFrame([
        {**base, 'play_type': play_type, 'yardline_100': 65,
         'touchdown': 1, 'td_team': 'DET'},
        {**base, **conversion},
        # Preserve a genuine offensive drive and its PAT.
        {**base, 'drive': 2, 'yardline_100': 10, 'touchdown': 1, 'td_team': 'DET'},
        {**base, 'drive': 2, 'play_type': 'extra_point',
         'yardline_100': 15, 'extra_point_result': 'good'},
    ])
    stats = NFLStatsCalculator()._calculate_scoring_and_redzone_stats(data, 'DET')
    assert stats['touchdowns'] == 1
    assert stats['extra_points'] == 1
    assert stats['two_point_conversions'] == 0
    assert stats['points'] == 7
    assert stats['drives'] == 1
    assert stats['points_per_drive'] == 7.0
    assert stats['redzone_trips'] == 1
    assert stats['redzone_touchdowns'] == 1


def test_punt_return_against_offense_still_counts_its_drive():
    data = pd.DataFrame([dict(
        game_id='game-1', drive=1, yardline_100=60, play_type='punt',
        touchdown=1, td_team='BUF', two_point_attempt=0,
    )])
    stats = NFLStatsCalculator()._calculate_scoring_and_redzone_stats(data, 'DET')
    assert stats['drives'] == 1
    assert stats['touchdowns'] == 0
    assert stats['points'] == 0


@pytest.mark.parametrize('play_type,down', [
    ('qb_kneel', 1),
    ('qb_spike', 1),
    ('punt', 4),
    ('field_goal', 4),
    ('run', 4),  # Fake punt/field-goal rush.
    ('pass', 4),  # Fake punt/field-goal pass.
    ('no_play', 4),  # Offensive penalty, including a kicking formation.
    (None, 4),  # Historical declined penalties sometimes lack play_type.
])
def test_offensive_events_still_establish_drives(play_type, down):
    data = pd.DataFrame([dict(
        game_id='game-1', drive=1, yardline_100=60, down=down,
        play_type=play_type, touchdown=0, td_team=None, two_point_attempt=0,
    )])
    stats = NFLStatsCalculator()._calculate_scoring_and_redzone_stats(data, 'DET')
    assert stats['drives'] == 1


@pytest.mark.parametrize('play_type,down,two_point_attempt', [
    (None, None, 0),  # END GAME/END QUARTER administrative row.
    ('no_play', None, 0),  # Kickoff/try penalty or timeout.
    ('kickoff', None, 0),
    ('extra_point', None, 0),
    ('run', None, 1),
    ('pass', None, 1),
])
def test_nonoffensive_rows_do_not_establish_drives(play_type, down, two_point_attempt):
    data = pd.DataFrame([dict(
        game_id='game-1', drive=1, yardline_100=60, down=down,
        play_type=play_type, touchdown=0, td_team=None,
        two_point_attempt=two_point_attempt,
    )])
    stats = NFLStatsCalculator()._calculate_scoring_and_redzone_stats(data, 'DET')
    assert stats['drives'] == 0


@pytest.mark.parametrize('play_type,metric_flag', [
    ('qb_kneel', 'include_qb_kneels_rushing'),
    ('qb_spike', 'include_spikes_completion'),
])
@pytest.mark.parametrize('include_metric', [False, True])
@pytest.mark.parametrize('include_success', [False, True])
def test_success_settings_are_independent(play_type, metric_flag, include_metric, include_success):
    from src.utils.configuration_utils import apply_configuration_to_data

    base = dict(
        game_id='game-1', drive=1, yardline_100=50, down=1, ydstogo=10,
        yards_gained=5, play_type='run', rush_attempt=1, pass_attempt=0,
        complete_pass=0, sack=0, two_point_attempt=0, touchdown=0, td_team=None,
        first_down=0, field_goal_result=None,
    )
    special = dict(base, play_type=play_type, yards_gained=-1 if play_type == 'qb_kneel' else 0,
                   rush_attempt=int(play_type == 'qb_kneel'), pass_attempt=int(play_type == 'qb_spike'))
    success_flag = 'include_qb_kneels_success_rate' if play_type == 'qb_kneel' else 'include_spikes_success_rate'
    data = apply_configuration_to_data(pd.DataFrame([base, special]), {
        metric_flag: include_metric, success_flag: include_success,
    })
    stats = NFLStatsCalculator()._calculate_all_stats(data, 'DET')
    assert stats['first_down_total'] == 1 + int(include_success)
    assert stats['first_down_successful'] == 1
    assert stats['success_rate'] == (50.0 if include_success else 100.0)
    if play_type == 'qb_kneel':
        assert stats['rush_attempts'] == 1 + int(include_metric)
    else:
        assert stats['pass_attempts'] == int(include_metric)


def test_success_breakdown_includes_fourth_down_and_eligible_denominator():
    calculator = NFLStatsCalculator()
    data = pd.DataFrame([
        dict(down=1, ydstogo=10, yards_gained=5),
        dict(down=4, ydstogo=2, yards_gained=2),
        dict(down=4, ydstogo=2, yards_gained=0),
    ])
    values = calculator._calculate_success_stats_optimized(data)
    assert values['fourth_down_successful'] == 1
    assert values['fourth_down_total'] == 2
    assert values['success_rate'] == pytest.approx(200 / 3)
    empty = calculator._calculate_success_stats_optimized(data.iloc[:0])
    assert empty['fourth_down_total'] == 0
    assert empty['fourth_down_successful'] == 0


@pytest.mark.parametrize('conversion', [
    dict(two_point_attempt=1, play_type='pass'),
    dict(two_point_attempt=1, play_type='run'),
    dict(two_point_attempt=0, play_type='extra_point'),
])
def test_conversion_turnovers_do_not_change_regular_turnover_totals(conversion):
    data = pd.DataFrame([
        dict(two_point_attempt=0, play_type='pass', interception=1, fumble_lost=0),
        dict(two_point_attempt=0, play_type='run', interception=0, fumble_lost=1),
        dict(**conversion, interception=1, fumble_lost=0),
        dict(**conversion, interception=0, fumble_lost=1),
    ])
    assert NFLStatsCalculator()._calculate_turnover_stats(data) == {
        'interceptions': 1, 'fumbles_lost': 1, 'total_turnovers': 2,
    }
