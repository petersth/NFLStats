# src/presentation/streamlit/components/progress_manager.py - Progress indicator management

import logging
import streamlit as st
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ProgressManager:
    """Manages progress indicators for long-running operations."""
    
    def __init__(self):
        self.progress_bar = None
        self.status_text = None
        self.start_time = None
        
    @contextmanager
    def track_progress(self, total_steps: int = 100, title: str = "Processing..."):
        """Context manager for tracking progress with detailed status updates."""
        status_placeholder = st.empty()
        progress_placeholder = st.empty()
        elapsed_placeholder = st.empty()
        
        try:
            with status_placeholder.container():
                self.status_text = st.empty()
            with progress_placeholder.container():
                # Create custom skinny progress bar instead of using st.progress
                self.progress_container = st.empty()
                self._render_custom_progress_bar(0)
            with elapsed_placeholder.container():
                self.elapsed_text = st.empty()
            
            self.start_time = time.time()
            self.total_steps = total_steps
            self.current_step = 0
            
            # Store placeholders for cleanup
            self.status_placeholder = status_placeholder
            self.progress_placeholder = progress_placeholder
            self.elapsed_placeholder = elapsed_placeholder
            
            # Set initial status with title
            self.update(0, title)
            self._update_elapsed_time()
            
            yield self
            
            # Complete progress and show briefly
            self.update(self.total_steps, "✅ Analysis complete!")
            time.sleep(0.3)  # Brief pause to show completion
            
        finally:
            # Clean up all placeholders
            self._cleanup_progress()
    
    def _render_custom_progress_bar(self, progress_value: float):
        """Render a custom skinny progress bar."""
        progress_percent = int(progress_value * 100)
        
        progress_html = f"""
        <div style="
            width: 100%;
            height: 8px;
            background-color: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        ">
            <div style="
                width: {progress_percent}%;
                height: 100%;
                background: linear-gradient(90deg, #1976d2, #42a5f5);
                transition: width 0.3s ease;
                border-radius: 4px;
            "></div>
        </div>
        """
        
        self.progress_container.markdown(progress_html, unsafe_allow_html=True)
    
    def update(self, step: int, message: str = "", sub_progress: Optional[Dict[str, Any]] = None):
        """Update progress bar and status message."""
        self.current_step = min(step, self.total_steps)
        progress = self.current_step / self.total_steps
        
        if hasattr(self, 'progress_container'):
            self._render_custom_progress_bar(progress)
        
        if self.status_text and message:
            # Build status message with optional sub-progress
            status_html = f"<div style='margin-bottom: 10px;'>{message}</div>"
            
            if sub_progress:
                sub_items = []
                for key, value in sub_progress.items():
                    if isinstance(value, bool):
                        icon = "✅" if value else "⏳"
                        sub_items.append(f"{icon} {key}")
                    else:
                        sub_items.append(f"• {key}: {value}")
                
                if sub_items:
                    status_html += "<div style='font-size: 0.9em; color: #666; margin-left: 20px;'>"
                    status_html += "<br>".join(sub_items)
                    status_html += "</div>"
            
            self.status_text.markdown(status_html, unsafe_allow_html=True)
        
        self._update_elapsed_time()
    
    def _update_elapsed_time(self):
        """Update the elapsed time display."""
        if self.start_time and hasattr(self, 'elapsed_text') and self.elapsed_text:
            elapsed = time.time() - self.start_time
            self.elapsed_text.caption(f"⏱️ {elapsed:.1f}s elapsed")
    
    def _cleanup_progress(self):
        """Clean up all progress indicators."""
        try:
            # Clear the main placeholders which will remove all content
            if hasattr(self, 'status_placeholder') and self.status_placeholder:
                self.status_placeholder.empty()
            if hasattr(self, 'progress_placeholder') and self.progress_placeholder:
                self.progress_placeholder.empty()
            if hasattr(self, 'elapsed_placeholder') and self.elapsed_placeholder:
                self.elapsed_placeholder.empty()
        except Exception as e:
            # Ignore cleanup errors but log them for debugging
            logger.debug(f"Error during progress cleanup: {e}")
            pass


class MultiStageProgress:
    """Manages multi-stage progress with detailed breakdowns."""
    
    def __init__(self, stages: Dict[str, int]):
        """
        Initialize with stages and their relative weights.
        
        Args:
            stages: Dict mapping stage names to their relative weights
                   e.g., {"Loading Data": 30, "Processing": 50, "Finalizing": 20}
        """
        self.stages = stages
        self.total_weight = sum(stages.values())
        self.completed_weight = 0
        self.current_stage = None
        self.progress_manager = ProgressManager()
        
    @contextmanager
    def track_overall_progress(self, title: str = "Analyzing NFL Statistics"):
        """Track overall progress across all stages."""
        try:
            with self.progress_manager.track_progress(self.total_weight, title) as pm:
                self.pm = pm
                yield self
        finally:
            # Ensure cleanup happens
            if hasattr(self, 'pm'):
                self.pm._cleanup_progress()
    
    @contextmanager
    def stage(self, stage_name: str):
        """Context manager for a single stage."""
        if stage_name not in self.stages:
            raise ValueError(f"Unknown stage: {stage_name}")
        
        self.current_stage = stage_name
        stage_weight = self.stages[stage_name]
        
        # Update progress to start of this stage
        self.pm.update(
            self.completed_weight,
            f"{stage_name}...",
            {"Previous stages": "Complete" if self.completed_weight > 0 else "Starting"}
        )
        
        yield StageProgress(
            self.pm,
            self.completed_weight,
            stage_weight,
            stage_name
        )
        
        # Mark stage as complete
        self.completed_weight += stage_weight
        self.pm.update(
            self.completed_weight,
            f"✅ {stage_name} complete"
        )


class StageProgress:
    """Progress tracking for a single stage."""
    
    def __init__(self, progress_manager: ProgressManager, base_progress: int, 
                 stage_weight: int, stage_name: str):
        self.pm = progress_manager
        self.base_progress = base_progress
        self.stage_weight = stage_weight
        self.stage_name = stage_name
        
    def update(self, percentage: float, message: str = "", details: Optional[Dict] = None):
        """Update progress within this stage (0.0 to 1.0)."""
        stage_progress = self.base_progress + int(percentage * self.stage_weight)
        full_message = f"{self.stage_name}: {message}" if message else f"{self.stage_name}"
        self.pm.update(stage_progress, full_message, details)


def create_simple_progress(message: str = "Loading...") -> Any:
    """Create a simple progress spinner with message."""
    return st.spinner(message)


def create_data_loading_progress() -> MultiStageProgress:
    """Create a pre-configured progress tracker for data loading operations."""
    stages = {
        "Fetching Data": 25,
        "Validating Data": 10,
        "Computing Rankings": 35,  # League-wide statistics (includes target team)
        "Calculating Statistics": 25,  # Extract team stats and game data
        "Preparing Display": 5
    }
    return MultiStageProgress(stages)