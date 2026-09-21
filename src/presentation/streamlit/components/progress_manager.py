"""Native, operation-driven loading feedback for Streamlit."""

from contextlib import contextmanager
import logging
import math
from numbers import Real
from typing import Any, Dict, Optional

import streamlit as st

logger = logging.getLogger(__name__)


def _finite_number(value: Real, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


class ProgressManager:
    """Show the current operation without inventing a percentage or duration.

    Nested data-loading and analysis callbacks each report their own 0–1 range.
    Those values are useful to existing stage callers, but are not a reliable
    percentage of the complete analysis. The native status therefore displays
    callback messages, and completes only when the tracked operation returns.
    """

    def __init__(self):
        self.status = None
        self.status_placeholder = None
        self.details = None
        self.total_steps = 100.0
        self.current_step = 0.0
        self._active = False

    @contextmanager
    def track_progress(self, total_steps: int = 100, title: str = "Processing..."):
        """Track an operation; remove its transient status on every exit path."""
        total = _finite_number(total_steps, "total_steps")
        if total <= 0:
            raise ValueError("total_steps must be greater than zero")
        if self._active:
            raise RuntimeError("This progress tracker is already active")

        self.total_steps = total
        self.current_step = 0.0
        self._active = True
        try:
            self.status_placeholder = st.empty()
            with self.status_placeholder.container():
                self.status = st.status(title, state="running", type="compact")
            self.details = self.status.empty()
            yield self
        except Exception:
            if self.status is not None:
                self.status.update(state="error")
            raise
        else:
            self.current_step = self.total_steps
            self.status.update(state="complete")
        finally:
            self._cleanup_progress()

    def update(self, step: int, message: str = "", sub_progress: Optional[Dict[str, Any]] = None):
        """Update from actual work callbacks, replacing rather than appending details."""
        if not self._active:
            raise RuntimeError("Use track_progress before updating progress")
        self.current_step = min(self.total_steps, max(0.0, _finite_number(step, "step")))

        if message:
            self.status.update(label=message)
        if sub_progress:
            lines = []
            for key, value in sub_progress.items():
                if isinstance(value, bool):
                    value = "Complete" if value else "In progress"
                lines.append(f"{key}: {value}")
            # Plain text preserves literal labels; no HTML or accumulated log.
            self.details.text("\n".join(lines))
        else:
            self.details.empty()

    def _cleanup_progress(self):
        """Clear once, including after cancellation, and allow safe tracker reuse."""
        placeholder = self.status_placeholder
        self.status_placeholder = None
        self.status = None
        self.details = None
        self._active = False
        if placeholder is not None:
            try:
                placeholder.empty()
            except Exception as exc:
                logger.debug("Error during progress cleanup: %s", exc)


class MultiStageProgress:
    """Track named operations while preserving the existing weighted-stage API."""

    def __init__(self, stages: Dict[str, int]):
        if not stages:
            raise ValueError("At least one stage is required")
        self.stages = {
            name: _finite_number(weight, f"Weight for {name}")
            for name, weight in stages.items()
        }
        if any(weight <= 0 for weight in self.stages.values()):
            raise ValueError("Stage weights must be greater than zero")
        self.total_weight = sum(self.stages.values())
        self.completed_weight = 0.0
        self.current_stage = None
        self.progress_manager = ProgressManager()
        self.pm = None

    @contextmanager
    def track_overall_progress(self, title: str = "Analyzing NFL Statistics"):
        """Track an entire operation and reset stage state for each invocation."""
        if self.pm is not None:
            raise RuntimeError("This stage tracker is already active")
        self.completed_weight = 0.0
        self.current_stage = None
        try:
            with self.progress_manager.track_progress(self.total_weight, title) as pm:
                self.pm = pm
                yield self
        finally:
            self.pm = None
            self.current_stage = None

    @contextmanager
    def stage(self, stage_name: str):
        """Only count a stage after its work has returned successfully."""
        if stage_name not in self.stages:
            raise ValueError(f"Unknown stage: {stage_name}")
        if self.pm is None:
            raise RuntimeError("Use track_overall_progress before starting a stage")
        if self.current_stage is not None:
            raise RuntimeError("Finish the current stage before starting another")

        self.current_stage = stage_name
        stage_weight = self.stages[stage_name]
        try:
            self.pm.update(self.completed_weight, f"{stage_name}...")
            yield StageProgress(self.pm, self.completed_weight, stage_weight, stage_name)
            self.completed_weight += stage_weight
            self.pm.update(self.completed_weight, f"{stage_name} complete")
        finally:
            self.current_stage = None


class StageProgress:
    """Progress callback for a single named operation."""

    def __init__(self, progress_manager: ProgressManager, base_progress: int,
                 stage_weight: int, stage_name: str):
        self.pm = progress_manager
        self.base_progress = base_progress
        self.stage_weight = stage_weight
        self.stage_name = stage_name

    def update(self, percentage: float, message: str = "", details: Optional[Dict] = None):
        """Clamp a finite stage fraction to its own allocation, never another stage."""
        fraction = min(1.0, max(0.0, _finite_number(percentage, "percentage")))
        stage_progress = self.base_progress + fraction * self.stage_weight
        full_message = f"{self.stage_name}: {message}" if message else self.stage_name
        self.pm.update(stage_progress, full_message, details)


def create_simple_progress(message: str = "Loading...") -> Any:
    """Create a native spinner for work without intermediate callbacks."""
    return st.spinner(message)


def create_data_loading_progress() -> MultiStageProgress:
    """Create the stage adapter used by the analysis controller."""
    return MultiStageProgress({
        "Fetching Data": 25,
        "Validating Data": 10,
        "Computing Rankings": 35,
        "Calculating Statistics": 25,
        "Preparing Display": 5,
    })
