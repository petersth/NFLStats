"""An analysis must stay internally consistent across independent cache lifetimes.

The source frames are synthetic completed games with the full production schema.
Only the nflverse loader and clock are replaced; repository optimization, caches,
league aggregation, rankings, records, and game calculations all run normally.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import polars as pl
import pytest

from src.domain.entities import Season, Team
from src.domain.nfl_stats_calculator import NFLStatsCalculator
from src.domain.orchestration.calculation_orchestrator import CalculationOrchestrator
from src.infrastructure.cache.league_stats_cache import LeagueStatsCache
from src.infrastructure.data.unified_nfl_repository import UnifiedNFLRepository


def _season_source(year, weeks):
    rows = []
    for week in weeks:
        # The second game adds a Detroit loss and changes both teams' metrics.
        gains = {"DET": 20 if week == 1 else 2, "GB": 4 if week == 1 else 15}
        winner = "DET" if week == 1 else "GB"
        for drive, team in enumerate(("DET", "GB"), start=1):
            opponent = "GB" if team == "DET" else "DET"
            row = dict.fromkeys(UnifiedNFLRepository.CALCULATION_REQUIRED_COLUMNS, 0)
            row.update(dict.fromkeys((
                "field_goal_result", "extra_point_result", "two_point_conv_result",
                "td_team", "penalty_team", "fumbled_1_team", "fumbled_2_team",
                "fumble_recovery_1_team", "fumble_recovery_2_team",
            )))
            row.update({
                "season": year, "season_type": "REG", "week": week,
                "game_id": f"{year}_{week:02d}_GB_DET",
                "game_date": f"{year}-09-{week * 7:02d}",
                "home_team": "DET", "away_team": "GB", "posteam": team,
                "defteam": opponent, "play_type": "pass", "drive": drive,
                "down": 3, "ydstogo": 5, "yardline_100": gains[team] if team == winner else 50,
                "yards_gained": gains[team], "pass_attempt": 1, "complete_pass": 1,
                "first_down": int(team == winner), "first_down_pass": int(team == winner),
                "success": int(team == winner),
                "third_down_converted": int(team == winner),
                "third_down_failed": int(team != winner),
                "touchdown": int(team == winner), "td_team": team if team == winner else None,
                "home_score": 6 if winner == "DET" else 0,
                "away_score": 6 if winner == "GB" else 0,
                "posteam_score_post": 6 if team == winner else 0,
                "defteam_score_post": 0 if team == winner else 6,
            })
            rows.append(row)
    return pl.DataFrame(rows)


@pytest.fixture
def lifecycle(monkeypatch):
    clock = [10_000.0]
    monkeypatch.setattr("src.infrastructure.cache.simple_cache.time.time", lambda: clock[0])
    monkeypatch.setattr(
        "src.utils.cache_policy.get_current_nfl_season_info",
        lambda: {"current_season": 2026, "season_status": "in_progress"},
    )
    current_season_loads = [0]

    def load_source(year):
        if year == 2026:
            current_season_loads[0] += 1
            weeks = (1,) if current_season_loads[0] == 1 else (1, 2)
        else:
            weeks = (1,)
        return _season_source(year, weeks)

    loader = Mock(side_effect=load_source)
    monkeypatch.setattr("src.infrastructure.data.unified_nfl_repository.nfl.load_pbp", loader)
    repository = UnifiedNFLRepository()
    calculator = NFLStatsCalculator()
    cache = LeagueStatsCache(repository, calculator)
    orchestrator = CalculationOrchestrator(calculator, cache)

    def analyze(team="DET", configuration=None, season_year=2026):
        return orchestrator.calculate_team_analysis(
            Team.from_abbreviation(team), Season(season_year), "REG", configuration or {},
        )

    return SimpleNamespace(
        clock=clock, repository=repository, loader=loader, analyze=analyze,
        cache=cache, calculator=calculator,
        current_season_loads=current_season_loads,
    )


def _assert_consistent_snapshot(analysis, weeks):
    expected_count = len(weeks)
    assert analysis.source_data_timestamp.strftime("%Y-%m-%d") == f"2026-09-{max(weeks) * 7:02d}"
    assert analysis.season_stats.games_played == expected_count
    assert [game.game.week for game in analysis.game_stats] == list(weeks)
    assert analysis.team_record.total_games == expected_count
    assert analysis.season_stats.total_yards == sum(
        game.offensive_stats.total_yards for game in analysis.game_stats
    )
    assert analysis.season_stats.toer == pytest.approx(
        sum(game.offensive_stats.toer for game in analysis.game_stats) / expected_count
    )
    assert analysis.season_stats.toer_allowed == pytest.approx(
        sum(game.defensive_stats.toer for game in analysis.game_stats) / expected_count
    )


def test_league_rating_benchmarks_match_with_unequal_game_counts(monkeypatch):
    first_game = _season_source(2024, (1,)).to_dicts()
    second_game = _season_source(2024, (2,)).to_dicts()
    for row in second_game:
        for key, value in row.items():
            if value == 'GB':
                row[key] = 'MIN'
        row['game_id'] = row['game_id'].replace('_GB_', '_MIN_')
        if row['posteam'] == 'DET':
            row.update(complete_pass=0, yards_gained=0)
    source = pl.DataFrame(first_game + second_game)
    monkeypatch.setattr(
        'src.infrastructure.data.unified_nfl_repository.nfl.load_pbp', lambda year: source,
    )
    cache = LeagueStatsCache(UnifiedNFLRepository(), NFLStatsCalculator())
    snapshot = cache.get_or_compute_analysis_snapshot(2024, 'REG', 'test', {})

    assert {team: stats.games_played for team, stats in snapshot.team_stats.items()} == {
        'DET': 2, 'GB': 1, 'MIN': 1,
    }
    games = snapshot.game_results['DET']
    expected = sum(
        game.home_team_offensive_stats.toer + game.away_team_offensive_stats.toer
        for game in games
    ) / 4
    assert snapshot.league_averages['toer'] == pytest.approx(expected)
    assert snapshot.league_averages['toer_allowed'] == pytest.approx(expected)
    # This fixture must exercise the original unequal-weighting discrepancy.
    unweighted = sum(stats.toer for stats in snapshot.team_stats.values()) / 3
    assert unweighted != pytest.approx(expected)


def test_staggered_configuration_cache_expiry_preserves_one_analysis_snapshot(lifecycle):
    original = lifecycle.analyze()
    _assert_consistent_snapshot(original, (1,))
    original_rankings = original.raw_rankings.copy()

    assert original.source_data_expires_at == 10_600
    # Changing filters near the deadline must not extend the old source's life.
    lifecycle.clock[0] += 599
    configuration = {"include_spikes_completion": False}
    filtered = lifecycle.analyze(configuration=configuration)
    _assert_consistent_snapshot(filtered, (1,))
    assert filtered.source_data_expires_at == original.source_data_expires_at
    assert lifecycle.current_season_loads[0] == 1

    # At the original source deadline, a different team/filter refreshes every
    # component together, even though that aggregate is only one second old.
    lifecycle.clock[0] += 1
    updated = lifecycle.analyze("GB", configuration)
    _assert_consistent_snapshot(updated, (1, 2))
    assert updated.source_data_expires_at == 11_200
    assert updated.team_record.regular_season_wins == 1
    assert updated.team_record.regular_season_losses == 1
    assert lifecycle.current_season_loads[0] == 2
    # A previously rendered/exportable response must keep its original snapshot.
    _assert_consistent_snapshot(original, (1,))
    assert original.raw_rankings == original_rankings


def test_raw_season_lru_eviction_does_not_split_an_existing_analysis(lifecycle):
    _assert_consistent_snapshot(lifecycle.analyze(), (1,))

    # The repository retains three seasons; the aggregate cache retains ten.
    # Loading three others naturally evicts 2026 without expiring its aggregate.
    for year in (2025, 2024, 2023):
        lifecycle.repository.get_play_by_play_data(year)
    assert lifecycle.repository.get_cached_play_by_play_data(2026) is None

    _assert_consistent_snapshot(lifecycle.analyze("GB"), (1,))
    assert lifecycle.loader.call_count == 4
    assert lifecycle.current_season_loads[0] == 1

    lifecycle.clock[0] += 601
    _assert_consistent_snapshot(lifecycle.analyze("GB"), (1, 2))
    assert lifecycle.current_season_loads[0] == 2


def test_historical_filters_share_the_original_thirty_minute_deadline(lifecycle):
    original = lifecycle.analyze(season_year=2025)
    assert original.source_data_expires_at == 11_800

    lifecycle.clock[0] += 900
    filtered = lifecycle.analyze(
        configuration={"include_qb_kneels_rushing": False}, season_year=2025,
    )
    assert filtered.source_data_expires_at == original.source_data_expires_at
    assert lifecycle.loader.call_count == 1

    lifecycle.clock[0] += 899
    assert lifecycle.analyze(season_year=2025).source_data_expires_at == 11_800
    assert lifecycle.loader.call_count == 1

    lifecycle.clock[0] += 1
    refreshed = lifecycle.analyze(
        configuration={"include_qb_kneels_rushing": False}, season_year=2025,
    )
    assert refreshed.source_data_expires_at == 13_600
    assert lifecycle.loader.call_count == 2


def test_calculation_time_does_not_extend_source_freshness(lifecycle, monkeypatch):
    original = lifecycle.analyze()
    lifecycle.clock[0] += 590
    process_games = lifecycle.calculator.process_all_games

    def slow_process(data):
        result = process_games(data)
        lifecycle.clock[0] += 11
        return result

    monkeypatch.setattr(lifecycle.calculator, "process_all_games", slow_process)
    configuration = {"include_spikes_completion": False}
    late = lifecycle.analyze(configuration=configuration)
    _assert_consistent_snapshot(late, (1,))
    assert late.source_data_expires_at == original.source_data_expires_at
    # This completed analysis remains internally coherent, but has no reusable
    # entry because its source expired during processing.
    key = lifecycle.cache.get_cache_key(
        2026, "REG", lifecycle.cache.get_config_hash(configuration)
    )
    assert lifecycle.cache._memory_cache.get(key) is None
    _assert_consistent_snapshot(lifecycle.analyze(configuration=configuration), (1, 2))
    assert lifecycle.current_season_loads[0] == 2
