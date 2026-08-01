from types import SimpleNamespace
from unittest.mock import Mock

from src.application.dto import TeamAnalysisRequest
from src.presentation.streamlit.controllers.team_analysis_controller import (
    TeamAnalysisController,
)
from src.presentation.streamlit.streamlit_controller import StreamlitController


def test_controller_consumes_orchestrated_league_context_without_another_lookup():
    orchestrator = Mock()
    orchestrator.calculate_team_analysis.return_value = SimpleNamespace(
        season_stats=object(),
        game_stats=[],
        team_record=None,
        raw_rankings={"toer": 1},
        league_averages={"toer": 50.0},
        league_team_count=32,
    )
    controller = TeamAnalysisController(orchestrator)

    response = controller.analyze_team(TeamAnalysisRequest(
        team_abbreviation="DET",
        season_year=2025,
        season_type_filter="REG",
        configuration={},
    ))

    assert response.rankings["toer"].rank == 1
    assert response.league_averages == {"toer": 50.0}
    orchestrator.calculate_team_analysis.assert_called_once()


class _AppState:
    def __init__(
        self,
        response=None,
        analyzed=("DET", 2025, "REG"),
        analyzed_cache_mode=None,
    ):
        self.response = response
        self.analyzed = analyzed
        self.analyzed_cache_mode = analyzed_cache_mode

    def is_analysis_complete(self):
        return self.response is not None

    def get_analyzed_selections(self):
        return self.analyzed

    def get_current_analysis(self):
        return self.response

    def get_analyzed_cache_mode(self):
        return self.analyzed_cache_mode


def _bare_streamlit_controller(cached=None, current=None, analyzed_cache_mode=None):
    controller = object.__new__(StreamlitController)
    controller.analysis_cache = SimpleNamespace(get=lambda key: cached)
    controller.app_state = _AppState(
        current,
        analyzed_cache_mode=analyzed_cache_mode,
    )
    return controller


def test_matching_cached_analysis_is_read_before_recalculation():
    cached = object()
    controller = _bare_streamlit_controller(cached=cached)
    request = SimpleNamespace(
        cache_nfl_data=True,
        team_abbreviation="DET",
        season_year=2025,
        season_type_filter="REG",
    )

    result = controller._get_reusable_analysis(
        request, SimpleNamespace(should_analyze=True), "analysis-key"
    )

    assert result is cached


def test_current_analysis_is_reused_for_unrelated_streamlit_rerun():
    current = object()
    controller = _bare_streamlit_controller(
        current=current,
        analyzed_cache_mode=False,
    )
    request = SimpleNamespace(
        cache_nfl_data=False,
        team_abbreviation="DET",
        season_year=2025,
        season_type_filter="REG",
    )

    result = controller._get_reusable_analysis(
        request, SimpleNamespace(should_analyze=False), "analysis-key"
    )

    assert result is current


def test_disabling_cache_refreshes_an_analysis_created_with_cache():
    controller = _bare_streamlit_controller(
        current=object(),
        analyzed_cache_mode=True,
    )
    request = SimpleNamespace(
        cache_nfl_data=False,
        team_abbreviation="DET",
        season_year=2025,
        season_type_filter="REG",
    )

    result = controller._get_reusable_analysis(
        request, SimpleNamespace(should_analyze=False), "analysis-key"
    )

    assert result is None


def test_expired_analysis_cache_does_not_fall_back_to_untimed_current_response():
    controller = _bare_streamlit_controller(
        cached=None,
        current=object(),
        analyzed_cache_mode=True,
    )
    request = SimpleNamespace(
        cache_nfl_data=True,
        team_abbreviation="DET",
        season_year=2025,
        season_type_filter="REG",
    )

    result = controller._get_reusable_analysis(
        request, SimpleNamespace(should_analyze=False), "analysis-key"
    )

    assert result is None
