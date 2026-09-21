from unittest.mock import patch

import pandas as pd
import polars as pl
import pytest

from src.domain.exceptions import DataNotFoundError
from src.infrastructure.data.unified_nfl_repository import UnifiedNFLRepository


def _required_pbp_frame(**extra_columns) -> pl.DataFrame:
    columns = {
        column: [0]
        for column in UnifiedNFLRepository.CALCULATION_REQUIRED_COLUMNS
    }
    columns.update({
        "season": [2025],
        "season_type": ["REG"],
        "week": [1],
        "game_id": ["2025_01_TEST"],
        "game_date": ["2025-09-07"],
        "home_team": ["DET"],
        "away_team": ["GB"],
        "posteam": ["DET"],
        "defteam": ["GB"],
        "play_type": ["pass"],
        "field_goal_result": [None],
        "extra_point_result": [None],
        "two_point_conv_result": [None],
        "td_team": [None],
        "penalty_team": [None],
    })
    columns.update(extra_columns)
    return pl.DataFrame(columns)


class TestUnifiedNFLRepositoryDataLoading:
    @patch("src.infrastructure.data.unified_nfl_repository.nfl.load_pbp")
    def test_retains_official_down_and_fumble_context(self, load_pbp):
        context = {
            "third_down_converted": [0], "third_down_failed": [1],
            "fumbled_1_team": ["CIN"], "fumbled_2_team": [None],
            "fumble_recovery_1_team": ["NE"], "fumble_recovery_2_team": [None],
            "touchback": [0],
        }
        load_pbp.return_value = _required_pbp_frame(**context)
        data = UnifiedNFLRepository()._load_play_by_play_data(2024)
        assert set(context).issubset(data.columns)
        assert data.loc[0, "fumbled_1_team"] == "CIN"
        assert data.loc[0, "fumble_recovery_1_team"] == "NE"
        assert data.loc[0, "third_down_failed"] == 1

    @pytest.mark.parametrize("column", ["third_down_converted", "fumble_recovery_1_team"])
    @patch("src.infrastructure.data.unified_nfl_repository.nfl.load_pbp")
    def test_rejects_missing_attribution_context(self, load_pbp, column):
        load_pbp.return_value = _required_pbp_frame().drop(column)
        with pytest.raises(DataNotFoundError, match=column):
            UnifiedNFLRepository()._load_play_by_play_data(2024)

    @patch("src.infrastructure.data.unified_nfl_repository.nfl.load_pbp")
    def test_loads_requested_season_as_a_trimmed_pandas_frame(self, load_pbp):
        load_pbp.return_value = _required_pbp_frame(unused_column=["discard me"])
        repository = UnifiedNFLRepository()

        result = repository._load_play_by_play_data(2025)

        load_pbp.assert_called_once_with(2025)
        assert "unused_column" not in result.columns
        assert set(repository.REQUIRED_COLUMNS).issubset(result.columns)
        assert result.iloc[0]["game_id"] == "2025_01_TEST"

    @patch("src.infrastructure.data.unified_nfl_repository.nfl.load_pbp")
    def test_rejects_datasets_missing_required_columns(self, load_pbp):
        load_pbp.return_value = pl.DataFrame({"season": [2025]})
        repository = UnifiedNFLRepository()

        with pytest.raises(DataNotFoundError, match="missing required columns"):
            repository._load_play_by_play_data(2025)

    def test_repository_pipeline_optimizes_loaded_data(self):
        repository = UnifiedNFLRepository()
        row = {column: 0 for column in repository.NEEDED_COLUMNS_ESSENTIAL}
        row.update({
            "season": 2025,
            "season_type": "REG",
            "week": 1,
            "game_id": "2025_01_TEST",
            "game_date": "2025-09-07",
            "home_team": "DET",
            "away_team": "GB",
            "posteam": "DET",
            "defteam": "GB",
            "play_type": "pass",
            "field_goal_result": "made",
            "extra_point_result": "good",
            "two_point_conv_result": "success",
            "td_team": "DET",
            "penalty_team": "GB",
        })

        with patch.object(
            repository,
            "_load_play_by_play_data",
            return_value=pd.DataFrame([row]),
        ):
            result, timestamp = repository.get_play_by_play_data(2025)

        assert timestamp == pd.Timestamp("2025-09-07")
        assert result["week"].dtype == "int8"
        assert pd.api.types.is_bool_dtype(result["pass_attempt"])
        assert isinstance(result["posteam"].dtype, pd.CategoricalDtype)


@pytest.mark.parametrize("season,ttl", [(2026, 600), (2025, 1800)])
def test_raw_cache_uses_source_deadline_after_loading(monkeypatch, season, ttl):
    clock = [1000.0]
    monkeypatch.setattr("src.infrastructure.cache.simple_cache.time.time", lambda: clock[0])
    monkeypatch.setattr(
        "src.utils.cache_policy.get_current_nfl_season_info",
        lambda: {"current_season": 2026, "season_status": "in_progress"},
    )
    loads = []

    def load_source(year):
        loads.append(year)
        clock[0] += 30  # Fetch time must not shorten the newly loaded source's TTL.
        return _required_pbp_frame(season=[year])

    monkeypatch.setattr("src.infrastructure.data.unified_nfl_repository.nfl.load_pbp", load_source)
    repository = UnifiedNFLRepository()
    original = repository.get_play_by_play_snapshot(season)
    assert original.expires_at == 1030 + ttl
    assert repository.get_cached_play_by_play_data(season)[0] is original.data

    clock[0] = original.expires_at - 0.001
    assert repository.get_play_by_play_snapshot(season) is original
    assert loads == [season]

    clock[0] = original.expires_at
    assert repository.get_cached_play_by_play_data(season) is None
    updated = repository.get_play_by_play_snapshot(season)
    assert updated.expires_at == clock[0] + ttl
    assert updated is not original
    assert loads == [season, season]
