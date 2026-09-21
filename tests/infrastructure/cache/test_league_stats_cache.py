from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from src.infrastructure.cache.league_stats_cache import LeagueAnalysisSnapshot, LeagueStatsCache


def test_season_cache_clear_matches_readable_keys():
    cache = LeagueStatsCache()
    key_2025 = cache.get_cache_key(2025, "REG", "config")
    key_2024 = cache.get_cache_key(2024, "REG", "config")

    for target in (
        cache._memory_cache,
        cache._rankings_cache,
    ):
        target.set(key_2025, {"DET": 1})
        target.set(key_2024, {"DET": 1})

    cleared = cache.clear_cache(2025)

    assert cleared == {"memory": 1, "rankings": 1}
    assert cache._memory_cache.get(key_2025) is None
    assert cache._memory_cache.get(key_2024) == {"DET": 1}


def test_config_hash_defaults_match_the_actual_inclusion_defaults():
    cache = LeagueStatsCache()
    all_included = {
        "include_qb_kneels_rushing": True,
        "include_qb_kneels_success_rate": True,
        "include_spikes_completion": True,
        "include_spikes_success_rate": True,
    }
    all_excluded = {key: False for key in all_included}

    assert cache.get_config_hash({}) == cache.get_config_hash(all_included)
    assert cache.get_config_hash({}) != cache.get_config_hash(all_excluded)


def test_team_grouping_ignores_blank_and_unsupported_possession_values():
    data = pd.DataFrame({
        "posteam": ["DET", "", None, "NOT_A_TEAM", "GB"],
        "yards_gained": [5, 0, 0, 0, 4],
    })

    grouped = LeagueStatsCache._group_team_data(data)

    assert sorted(grouped) == ["DET", "GB"]
    assert grouped["DET"]["yards_gained"].tolist() == [5]


@pytest.mark.parametrize("refresh_reason", ["expiry", "eviction"])
def test_rankings_refresh_with_aggregate_snapshot(monkeypatch, refresh_reason):
    clock = [1000.0]
    monkeypatch.setattr(
        "src.infrastructure.cache.simple_cache.time.time", lambda: clock[0]
    )
    monkeypatch.setattr(
        "src.utils.cache_policy.get_current_nfl_season_info",
        lambda: {"current_season": 2026, "season_status": "in_progress"},
    )
    initial = {"DET": SimpleNamespace(toer=90), "GB": SimpleNamespace(toer=80)}
    refreshed = {"DET": SimpleNamespace(toer=70), "GB": SimpleNamespace(toer=80)}
    cache = LeagueStatsCache(nfl_data_repo=Mock())
    initial_games = {"DET": [object()]}
    refreshed_games = {"DET": [object(), object()]}
    cache._compute_from_raw_data = Mock(side_effect=[
        LeagueAnalysisSnapshot(initial, {}, datetime(2026, 9, 20, 12),
                               pd.DataFrame({"game_id": ["first"]}), initial_games),
        LeagueAnalysisSnapshot(refreshed, {}, datetime(2026, 9, 20, 12, 11),
                               pd.DataFrame({"game_id": ["first", "second"]}), refreshed_games),
    ])
    cache_key = cache.get_cache_key(2026, "REG", "config")

    first, _, _ = cache.get_or_compute_league_stats(2026, "REG", "config", {})
    assert cache.get_cached_game_results(2026, "REG", "config") is initial_games
    assert cache.get_team_rankings("DET", first, cache_key)["toer"] == 1

    if refresh_reason == "expiry":
        clock[0] += 601  # Aggregates expire before the 30-minute ranking cache.
    else:
        cache._memory_cache._max_size = 1
        cache._memory_cache.set("another-season", ({}, {}, datetime.now()))

    assert cache.get_cached_game_results(2026, "REG", "config") is None
    second, _, _ = cache.get_or_compute_league_stats(2026, "REG", "config", {})
    assert cache.get_cached_game_results(2026, "REG", "config") is refreshed_games
    assert second is refreshed
    assert cache.get_team_rankings("DET", second, cache_key)["toer"] == 2
    assert cache._compute_from_raw_data.call_count == 2
    # A caller holding an earlier snapshot must still receive its own ranks.
    assert cache.get_team_rankings("DET", first, cache_key)["toer"] == 1
    assert cache.get_team_rankings("DET", second, cache_key)["toer"] == 2
