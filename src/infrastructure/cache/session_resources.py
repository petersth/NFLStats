"""Session-owned calculation resources managed by Streamlit's public cache API.

Streamlit releases this cache on session disconnect. The 30-minute TTL is checked
on access, not by an inactivity timer: an open, idle browser may retain resources
until its next access or disconnect. No resource is shared between sessions.
"""

from contextlib import contextmanager
import logging
from threading import RLock

import streamlit as st

from ..factories import create_calculation_orchestrator

logger = logging.getLogger(__name__)


class AnalysisResources:
    """Own one orchestrator and serialize its use against native cache release."""

    def __init__(self):
        self._lock = RLock()
        self._orchestrator = create_calculation_orchestrator()

    @contextmanager
    def use(self):
        with self._lock:
            if self._orchestrator is None:
                raise RuntimeError("Analysis resources have already been released")
            yield self._orchestrator

    def close(self) -> None:
        """Release every owned cache, safely even after an earlier cleanup error.

        Native release callbacks may run outside a script's session context. This
        method therefore uses no Streamlit calls and only touches this instance.
        """
        with self._lock:
            orchestrator, self._orchestrator = self._orchestrator, None
            if orchestrator is None:
                return
            for name, clear in (
                ("league", orchestrator.league_cache.clear_cache),
                ("repository", orchestrator.league_cache.clear_repository_cache),
                ("calculator", orchestrator.statistics_calculator.clear_cache),
            ):
                try:
                    clear()
                except Exception:
                    logger.exception("Could not release %s analysis cache", name)


@st.cache_resource(
    scope="session",
    ttl=1800,
    max_entries=1,
    show_spinner=False,
    on_release=AnalysisResources.close,
)
def get_session_analysis_resources() -> AnalysisResources:
    """Return this session's resource; derived data retain their own cache keys/TTLs."""
    return AnalysisResources()


@contextmanager
def analysis_orchestrator(cache_enabled: bool):
    """Lease a session resource or release a fresh resource on every exit path."""
    if cache_enabled:
        with get_session_analysis_resources().use() as orchestrator:
            yield orchestrator
        return

    # Disabling caching is an explicit fresh-data request. Drop this session's
    # previous resource as well, so turning caching on cannot revive old raw data.
    get_session_analysis_resources.clear()
    resources = AnalysisResources()
    try:
        with resources.use() as orchestrator:
            yield orchestrator
    finally:
        resources.close()
