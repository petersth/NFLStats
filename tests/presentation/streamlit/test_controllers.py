from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

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
        raw_rankings={"toer": 1, "toer_allowed": 3},
        league_averages={"toer": 50.0, "toer_allowed": 45.0},
        league_team_count=32,
        source_data_timestamp=datetime(2025, 9, 7),
        source_data_expires_at=12345.0,
    )
    controller = TeamAnalysisController(orchestrator)

    response = controller.analyze_team(TeamAnalysisRequest(
        team_abbreviation="DET",
        season_year=2025,
        season_type_filter="REG",
        configuration={},
    ))

    assert response.rankings["toer"].rank == 1
    assert response.rankings["toer_allowed"].rank == 3
    assert response.rankings["toer_allowed"].total_teams == 32
    assert response.league_averages == {"toer": 50.0, "toer_allowed": 45.0}
    assert response.source_data_timestamp == datetime(2025, 9, 7)
    assert response.source_data_expires_at == 12345.0
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
    controller.analysis_cache = SimpleNamespace(get=lambda key: cached, delete=Mock())
    controller.app_state = _AppState(
        current,
        analyzed_cache_mode=analyzed_cache_mode,
    )
    return controller


def test_matching_cached_analysis_is_read_before_recalculation():
    cached = SimpleNamespace(source_data_expires_at=None)
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


@pytest.mark.parametrize("remaining_seconds", [-1, 0, 90, 900])
def test_new_response_cache_never_extends_its_source_lifetime(monkeypatch, remaining_seconds):
    from src.infrastructure.frameworks import streamlit_utils
    from src.presentation.streamlit import streamlit_controller

    class Clock:
        @staticmethod
        def now():
            return datetime(2026, 9, 20, 12)

    session_state = {}
    ui = SimpleNamespace(empty=MagicMock(), info=Mock(), error=Mock())
    monkeypatch.setattr(streamlit_utils, "datetime", Clock)
    monkeypatch.setattr(streamlit_utils, "st", SimpleNamespace(session_state=session_state))
    monkeypatch.setattr(streamlit_controller, "st", ui)
    monkeypatch.setattr(streamlit_controller.time, "time", lambda: 10_000.0)
    monkeypatch.setattr(streamlit_controller, "get_season_cache_ttl", lambda year: 600)
    response = SimpleNamespace(source_data_expires_at=10_000.0 + remaining_seconds)
    controller = object.__new__(StreamlitController)
    controller.analysis_cache = streamlit_utils.StreamlitCacheAdapter()
    controller.app_state = Mock()
    controller._perform_analysis_with_progress = Mock(return_value=response)
    controller._render_analysis_results = Mock()
    controller._rerender_sidebar_with_data_status = Mock()

    controller._render_team_analysis_with_sidebar(SimpleNamespace(
        team_abbreviation="DET", season_year=2026, season_type_filter="REG",
        configuration={}, cache_nfl_data=True, should_analyze=False,
    ))

    if remaining_seconds > 0:
        entry = next(iter(session_state.values()))
        assert entry["value"] is response
        assert entry["expires_at"] == Clock.now() + timedelta(seconds=min(600, remaining_seconds))
    else:
        assert session_state == {}  # An expired source must not become an untimed cache entry.
    controller._render_analysis_results.assert_called_once()
    ui.error.assert_not_called()


@pytest.mark.parametrize("now, reusable", [(10_599.0, True), (10_600.0, False), (10_601.0, False)])
def test_absolute_source_expiry_rejects_cached_response_at_the_boundary(monkeypatch, now, reusable):
    from src.presentation.streamlit import streamlit_controller

    response = SimpleNamespace(source_data_expires_at=10_600.0)
    controller = _bare_streamlit_controller(cached=response, current=response)
    monkeypatch.setattr(streamlit_controller.time, "time", lambda: now)
    result = controller._get_reusable_analysis(
        SimpleNamespace(cache_nfl_data=True), SimpleNamespace(should_analyze=False), "analysis-key",
    )
    assert result is (response if reusable else None)
    if reusable:
        controller.analysis_cache.delete.assert_not_called()
    else:
        controller.analysis_cache.delete.assert_called_once_with("analysis-key")


@pytest.mark.parametrize("season_year, season_status, ttl_minutes", [
    (2026, "in_progress", 10),
    (2026, "playoffs", 10),
    (2026, "offseason", 30),
    (2025, "in_progress", 30),
])
def test_rendering_cached_analysis_preserves_expiry_and_then_recomputes(
    monkeypatch, season_year, season_status, ttl_minutes,
):
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
        "src.utils.cache_policy.get_current_nfl_season_info",
        lambda: {"current_season": 2026, "season_status": season_status},
    )
    selections = SimpleNamespace(
        team_abbreviation="DET", season_year=season_year, season_type_filter="REG",
        configuration={}, cache_nfl_data=True, should_analyze=False,
    )
    initial, refreshed = (SimpleNamespace(source_data_expires_at=None) for _ in range(2))
    controller = object.__new__(StreamlitController)
    controller.analysis_cache = streamlit_utils.StreamlitCacheAdapter()
    controller.app_state = Mock()
    controller._perform_analysis_with_progress = Mock(side_effect=[initial, refreshed])
    controller._render_analysis_results = Mock()
    controller._rerender_sidebar_with_data_status = Mock()

    controller._render_team_analysis_with_sidebar(selections)
    entry = next(iter(session_state.values()))
    original_expiry = entry["expires_at"]
    assert original_expiry == Clock.current + timedelta(minutes=ttl_minutes)

    Clock.current += timedelta(minutes=ttl_minutes - 1)
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


@pytest.mark.parametrize("failure_stage", ["initialization", "progress", "analysis"])
def test_analysis_resource_lease_covers_every_failure_path(monkeypatch, failure_stage):
    from contextlib import contextmanager
    from src.presentation.streamlit import streamlit_controller

    released = []
    orchestrator = object()

    @contextmanager
    def lease(cache_enabled):
        assert cache_enabled is False
        try:
            yield orchestrator
        finally:
            released.append(orchestrator)

    controller_factory = Mock()
    progress_factory = MagicMock()
    monkeypatch.setattr(streamlit_controller, "analysis_orchestrator", lease)
    monkeypatch.setattr(streamlit_controller, "TeamAnalysisController", controller_factory)
    monkeypatch.setattr(streamlit_controller, "create_data_loading_progress", progress_factory)
    monkeypatch.setattr(streamlit_controller, "st", SimpleNamespace(error=Mock()))
    request = SimpleNamespace(cache_nfl_data=False)
    controller = object.__new__(StreamlitController)

    if failure_stage == "initialization":
        controller_factory.side_effect = ValueError("bad initialization")
        assert controller._perform_analysis_with_progress(request) is None
    else:
        if failure_stage == "progress":
            progress_factory.side_effect = RuntimeError("progress failure")
        else:
            controller_factory.return_value.analyze_team.side_effect = RuntimeError("analysis failure")
        with pytest.raises(RuntimeError, match="failure"):
            controller._perform_analysis_with_progress(request)
    assert released == [orchestrator]


@pytest.mark.parametrize("changed_selection", [
    {"team_abbreviation": "GB"},
    {"season_year": 2024},
    {"season_type_filter": "POST"},
    {"configuration": {"include_kneels": False}},
])
def test_response_cache_isolates_team_season_type_and_configuration(monkeypatch, changed_selection):
    from src.infrastructure.frameworks import streamlit_utils
    from src.presentation.streamlit import streamlit_controller

    session_state = {}
    monkeypatch.setattr(streamlit_utils, "st", SimpleNamespace(session_state=session_state))
    monkeypatch.setattr(streamlit_controller, "st", SimpleNamespace(empty=MagicMock(), info=Mock(), error=Mock()))
    selections = SimpleNamespace(
        team_abbreviation="DET", season_year=2025, season_type_filter="REG",
        configuration={}, cache_nfl_data=True, should_analyze=False,
    )
    controller = object.__new__(StreamlitController)
    controller.analysis_cache = streamlit_utils.StreamlitCacheAdapter()
    controller.app_state = Mock()
    original, changed = (SimpleNamespace(source_data_expires_at=None) for _ in range(2))
    controller._perform_analysis_with_progress = Mock(side_effect=[original, changed])
    controller._render_analysis_results = Mock()
    controller._rerender_sidebar_with_data_status = Mock()

    controller._render_team_analysis_with_sidebar(selections)
    controller._render_team_analysis_with_sidebar(SimpleNamespace(**(vars(selections) | changed_selection)))
    controller._render_team_analysis_with_sidebar(selections)
    assert controller._perform_analysis_with_progress.call_count == 2
    assert [call.args[0] for call in controller._render_analysis_results.call_args_list] == [
        original, changed, original,
    ]


def test_turning_cache_off_clears_old_responses_without_clearing_other_session_state(monkeypatch):
    from src.infrastructure.frameworks import streamlit_utils
    from src.presentation.streamlit import streamlit_controller

    session_state = {"cache_old_analysis": object(), "team_selector": "DET"}
    monkeypatch.setattr(streamlit_utils, "st", SimpleNamespace(session_state=session_state))
    monkeypatch.setattr(streamlit_controller, "st", SimpleNamespace(empty=MagicMock(), info=Mock(), error=Mock()))
    controller = object.__new__(StreamlitController)
    controller.analysis_cache = streamlit_utils.StreamlitCacheAdapter()
    controller.app_state = Mock()
    controller.app_state.get_analyzed_cache_mode.return_value = True
    controller._perform_analysis_with_progress = Mock(return_value=object())
    controller._render_analysis_results = Mock()
    controller._rerender_sidebar_with_data_status = Mock()
    controller._render_team_analysis_with_sidebar(SimpleNamespace(
        team_abbreviation="DET", season_year=2025, season_type_filter="REG",
        configuration={}, cache_nfl_data=False, should_analyze=False,
    ))
    assert session_state == {"team_selector": "DET"}
    controller._perform_analysis_with_progress.assert_called_once()


def test_sidebar_uses_the_displayed_snapshot_timestamp_after_resource_release(monkeypatch):
    from src.presentation.streamlit.components import sidebar_manager

    timestamp = datetime(2025, 9, 7)
    season = object()
    status = SimpleNamespace(status_type="info", latest_game_date="2025-09-07")
    status_lookup = Mock(return_value=status)
    ui = SimpleNamespace(caption=Mock(), warning=Mock(), error=Mock())
    monkeypatch.setattr(sidebar_manager, "get_data_status", status_lookup)
    monkeypatch.setattr(sidebar_manager, "st", ui)
    manager = sidebar_manager.SidebarManager(Mock(), Mock())

    manager._render_data_status_sidebar(SimpleNamespace(
        season=season, source_data_timestamp=timestamp,
    ))
    assert status_lookup.call_args.args == (timestamp, season)
    ui.caption.assert_called_once_with("Latest game in source: 2025-09-07")
    ui.error.assert_not_called()
