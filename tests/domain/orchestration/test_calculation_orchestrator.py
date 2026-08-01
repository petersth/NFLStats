from types import SimpleNamespace

import pandas as pd
import pytest

from src.domain.entities import Season, Team
from src.domain.orchestration.calculation_orchestrator import CalculationOrchestrator


def test_league_failures_propagate_instead_of_returning_zero_stats():
    league_cache = SimpleNamespace(
        get_config_hash=lambda configuration: "config",
        get_or_compute_league_stats=lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("schema changed")
        ),
    )
    orchestrator = CalculationOrchestrator(
        statistics_calculator=object(),
        league_cache=league_cache,
    )

    with pytest.raises(RuntimeError, match="schema changed"):
        orchestrator.calculate_team_analysis(
            Team.from_abbreviation("DET"),
            Season(2025),
            "REG",
            {},
        )


def test_analysis_reuses_the_single_league_result_for_rankings_and_averages():
    season_stats = object()
    league_cache = SimpleNamespace()
    league_cache.calls = 0
    league_cache.get_config_hash = lambda configuration: "config"

    def get_league_stats(*args, **kwargs):
        league_cache.calls += 1
        return {"DET": season_stats}, {"toer": 50.0}, pd.Timestamp("2025-09-07")

    league_cache.get_or_compute_league_stats = get_league_stats
    league_cache.get_cache_key = lambda *args: "league-key"
    league_cache.get_team_rankings = lambda *args: {"toer": 1}
    league_cache.get_play_data = lambda *args: pd.DataFrame([{
        "posteam": "DET",
        "season_type": "REG",
    }])
    league_cache.get_cached_game_results = lambda *args: {}

    calculator = SimpleNamespace(
        calculate_team_record=lambda *args: None,
        calculate_game_stats_with_toer_allowed=lambda *args, **kwargs: [],
    )
    orchestrator = CalculationOrchestrator(calculator, league_cache)

    result = orchestrator.calculate_team_analysis(
        Team.from_abbreviation("DET"), Season(2025), "REG", {}
    )

    assert result.season_stats is season_stats
    assert result.raw_rankings == {"toer": 1}
    assert result.league_averages == {"toer": 50.0}
    assert league_cache.calls == 1
