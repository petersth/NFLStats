import pytest

from src.utils.cache_policy import get_season_cache_ttl


@pytest.mark.parametrize(
    "requested_season,status,expected",
    [
        (2026, "in_progress", 600),
        (2026, "playoffs", 600),
        (2026, "offseason", 1800),
        (2025, "in_progress", 1800),
        (2025, "playoffs", 1800),
    ],
)
def test_source_freshness_policy(monkeypatch, requested_season, status, expected):
    monkeypatch.setattr(
        "src.utils.cache_policy.get_current_nfl_season_info",
        lambda: {"current_season": 2026, "season_status": status},
    )
    assert get_season_cache_ttl(requested_season) == expected
