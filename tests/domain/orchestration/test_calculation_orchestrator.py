from types import SimpleNamespace

import pandas as pd
import pytest

from src.domain.entities import Season, Team
from src.domain.orchestration.calculation_orchestrator import CalculationOrchestrator
from src.infrastructure.cache.league_stats_cache import LeagueAnalysisSnapshot


def test_league_failures_propagate_instead_of_returning_zero_stats():
    league_cache = SimpleNamespace(
        get_config_hash=lambda configuration: "config",
        get_or_compute_analysis_snapshot=lambda *args, **kwargs: (_ for _ in ()).throw(
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
    source_data = pd.DataFrame([{"posteam": "DET", "season_type": "REG"}])
    game_results = {"DET": []}
    league_cache = SimpleNamespace()
    league_cache.calls = 0
    league_cache.get_config_hash = lambda configuration: "config"

    def get_league_stats(*args, **kwargs):
        league_cache.calls += 1
        return LeagueAnalysisSnapshot(
            {"DET": season_stats}, {"toer": 50.0}, pd.Timestamp("2025-09-07"),
            source_data, game_results,
        )

    league_cache.get_or_compute_analysis_snapshot = get_league_stats
    league_cache.get_cache_key = lambda *args: "league-key"
    league_cache.get_team_rankings = lambda *args: {"toer": 1}

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
