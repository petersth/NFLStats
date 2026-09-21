from datetime import datetime

import pytest

from src.domain.entities import Season
from src.utils import season_utils


@pytest.mark.parametrize("now,season,status", [
    (datetime(2026, 1, 31), 2025, "playoffs"),
    (datetime(2026, 2, 1), 2025, "playoffs"),
    (datetime(2026, 2, 8, 23, 59), 2025, "playoffs"),
    (datetime(2026, 2, 28, 23, 59), 2025, "playoffs"),
    (datetime(2028, 2, 29, 23, 59), 2027, "playoffs"),
    (datetime(2026, 3, 1), 2025, "completed"),
    (datetime(2026, 9, 1), 2026, "in_progress"),
])
def test_season_completion_uses_conservative_end_of_february_cutoff(
    monkeypatch, now, season, status
):
    monkeypatch.setattr(season_utils, "datetime", type("Clock", (), {
        "now": staticmethod(lambda: now),
    }))

    info = season_utils.get_current_nfl_season_info()

    assert info["current_season"] == season
    assert info["season_status"] == status
    context = season_utils.get_season_context_message(Season(season))
    if status == "playoffs":
        assert "Playoffs in progress" in context["message"]
        assert context["type"] == "info"
    elif status == "completed":
        assert context["message"] == f"{season} season: Complete"
