import pandas as pd

from src.domain.entities import Team
from src.domain.nfl_stats_calculator import NFLStatsCalculator


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
