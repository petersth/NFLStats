from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

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


def test_rendering_cached_analysis_preserves_expiry_and_then_recomputes(monkeypatch):
    from src.infrastructure.frameworks import streamlit_utils
    from src.presentation.streamlit import streamlit_controller

    class Clock:
        current = datetime(2026, 9, 20, 12)

        @classmethod
        def now(cls):
            return cls.current

    session_state = {}
    monkeypatch.setattr(streamlit_utils, "datetime", Clock)
    monkeypatch.setattr(streamlit_utils, "st", SimpleNamespace(session_state=session_state))
    ui = SimpleNamespace(empty=MagicMock(), info=Mock(), error=Mock())
    monkeypatch.setattr(streamlit_controller, "st", ui)
    monkeypatch.setattr(
        streamlit_controller,
        "get_current_nfl_season_info",
        lambda: {"current_season": 2026, "season_status": "in_progress"},
    )
    selections = SimpleNamespace(
        team_abbreviation="DET", season_year=2026, season_type_filter="REG",
        configuration={}, cache_nfl_data=True, should_analyze=False,
    )
    initial, refreshed = object(), object()
    controller = object.__new__(StreamlitController)
    controller.analysis_cache = streamlit_utils.StreamlitCacheAdapter()
    controller.app_state = Mock()
    controller._perform_analysis_with_progress = Mock(side_effect=[initial, refreshed])
    controller._render_analysis_results = Mock()
    controller._rerender_sidebar_with_data_status = Mock()

    controller._render_team_analysis_with_sidebar(selections)
    entry = next(iter(session_state.values()))
    original_expiry = entry["expires_at"]
    assert original_expiry == Clock.current + timedelta(minutes=10)

    Clock.current += timedelta(minutes=9)
    controller._render_team_analysis_with_sidebar(selections)
    assert next(iter(session_state.values()))["expires_at"] == original_expiry
    controller._perform_analysis_with_progress.assert_called_once()

    Clock.current += timedelta(minutes=2)
    controller._render_team_analysis_with_sidebar(selections)
    assert controller._perform_analysis_with_progress.call_count == 2
    assert [call.args[0] for call in controller._render_analysis_results.call_args_list] == [
        initial, initial, refreshed,
    ]
    ui.error.assert_not_called()
