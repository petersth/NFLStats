import pandas as pd

from src.infrastructure.cache.league_stats_cache import LeagueStatsCache


def test_season_cache_clear_matches_readable_keys():
    cache = LeagueStatsCache()
    key_2025 = cache.get_cache_key(2025, "REG", "config")
    key_2024 = cache.get_cache_key(2024, "REG", "config")

    for target in (
        cache._memory_cache,
        cache._rankings_cache,
        cache._game_results_cache,
    ):
        target.set(key_2025, {"DET": 1})
        target.set(key_2024, {"DET": 1})

    cleared = cache.clear_cache(2025)

    assert cleared == {"memory": 1, "rankings": 1, "game_results": 1}
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
