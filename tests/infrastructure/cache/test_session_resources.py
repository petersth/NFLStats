"""Exercise native resource caching without network calls or a browser process."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.infrastructure.cache import session_resources


@pytest.fixture
def native_sessions(monkeypatch):
    # AppTest currently gives every test app the same session ID. Replace only
    # this library test seam to exercise two sessions through the actual public
    # cache_resource wrapper, including its release hook and per-session clear.
    from streamlit.runtime.caching import cache_resource_api, cache_utils

    first_session, second_session = f"first-{uuid4()}", f"second-{uuid4()}"
    active_session = [first_session]
    clock = [100.0]
    monkeypatch.setattr(
        cache_resource_api, "get_session_id_or_throw", lambda: active_session[0],
    )
    monkeypatch.setattr(cache_utils, "TTLCACHE_TIMER", lambda: clock[0])
    orchestrators = []

    def create_orchestrator():
        orchestrator = SimpleNamespace(
            league_cache=SimpleNamespace(clear_cache=Mock(), clear_repository_cache=Mock()),
            statistics_calculator=SimpleNamespace(clear_cache=Mock()),
        )
        orchestrators.append(orchestrator)
        return orchestrator

    monkeypatch.setattr(session_resources, "create_calculation_orchestrator", create_orchestrator)
    yield SimpleNamespace(
        session=active_session, clock=clock, orchestrators=orchestrators,
        first_session=first_session, second_session=second_session,
    )
    for session_id in (first_session, second_session):
        active_session[0] = session_id
        session_resources.get_session_analysis_resources.clear()


def _assert_released(orchestrator):
    orchestrator.league_cache.clear_cache.assert_called_once_with()
    orchestrator.league_cache.clear_repository_cache.assert_called_once_with()
    orchestrator.statistics_calculator.clear_cache.assert_called_once_with()


def test_native_resource_reuses_only_its_own_session_and_clears_only_that_session(native_sessions):
    with session_resources.analysis_orchestrator(True) as first:
        pass
    with session_resources.analysis_orchestrator(True) as again:
        assert again is first

    native_sessions.session[0] = native_sessions.second_session
    with session_resources.analysis_orchestrator(True) as second:
        assert second is not first
    session_resources.get_session_analysis_resources.clear()
    _assert_released(second)
    first.league_cache.clear_cache.assert_not_called()

    native_sessions.session[0] = native_sessions.first_session
    with session_resources.analysis_orchestrator(True) as again:
        assert again is first
    session_resources.get_session_analysis_resources.clear()
    _assert_released(first)


def test_native_expiry_releases_all_caches_on_next_access_without_resetting_ttl(native_sessions):
    with session_resources.analysis_orchestrator(True) as first:
        pass
    native_sessions.clock[0] += 1799
    with session_resources.analysis_orchestrator(True) as again:
        assert again is first
    native_sessions.clock[0] += 2
    with session_resources.analysis_orchestrator(True) as refreshed:
        assert refreshed is not first
    _assert_released(first)
    refreshed.league_cache.clear_cache.assert_not_called()


def test_disabling_cache_discards_old_resource_and_releases_each_fresh_resource(native_sessions):
    with session_resources.analysis_orchestrator(True) as cached:
        pass
    with session_resources.analysis_orchestrator(False) as fresh:
        assert fresh is not cached
        _assert_released(cached)
        fresh.league_cache.clear_cache.assert_not_called()
    _assert_released(fresh)
    with session_resources.analysis_orchestrator(True) as reenabled:
        assert reenabled is not cached and reenabled is not fresh


@pytest.mark.parametrize("error", [ValueError, RuntimeError, KeyboardInterrupt])
def test_temporary_resource_is_released_on_every_exception_path(native_sessions, error):
    with pytest.raises(error):
        with session_resources.analysis_orchestrator(False) as fresh:
            raise error("analysis aborted")
    _assert_released(fresh)


def test_cleanup_continues_after_an_individual_cache_fails_and_is_idempotent(native_sessions):
    resources = session_resources.AnalysisResources()
    with resources.use() as orchestrator:
        orchestrator.league_cache.clear_cache.side_effect = RuntimeError("cache error")
    resources.close()
    resources.close()
    _assert_released(orchestrator)
    with pytest.raises(RuntimeError, match="already been released"):
        with resources.use():
            pytest.fail("Released resources must not be leased")


def test_real_calculator_cache_is_released_without_modifying_cached_results():
    from src.domain.nfl_stats_calculator import NFLStatsCalculator

    calculator = NFLStatsCalculator()
    result = [object()]
    calculator._game_stats_cache.set("game", result)
    assert calculator.clear_cache() == 1
    assert calculator.get_cache_stats()["stats"]["size"] == 0
    assert len(result) == 1
