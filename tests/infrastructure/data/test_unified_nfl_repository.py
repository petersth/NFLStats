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
