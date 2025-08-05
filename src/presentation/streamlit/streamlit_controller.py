# src/presentation/streamlit/streamlit_controller.py - Streamlit controller

import streamlit as st
import logging
from typing import Dict, Any

from .controllers.team_analysis_controller import TeamAnalysisController
from ...application.dto import TeamAnalysisRequest
from ...domain.exceptions import DataAccessError, DataNotFoundError, UseCaseError
from ...infrastructure.factories import get_configured_cache
from ...infrastructure.frameworks.streamlit_utils import StreamlitAdapter
from .components.sidebar_manager import SidebarManager
from .components.metrics_renderer import MetricsRenderer
from .components.tab_manager import TabManager
from .components.progress_manager import create_data_loading_progress
from .styling.app_styling import inject_custom_css, inject_team_colors

logger = logging.getLogger(__name__)


class MultiStageProgressAdapter:
    """Adapter to make MultiStageProgress work with progress callbacks."""
    
    def __init__(self, multi_stage_progress):
        self.progress = multi_stage_progress
        self.current_stage = None
        self.stage_mapping = {
            "Fetching Data": "Fetching Data",
            "Validating Data": "Validating Data", 
            "Computing Rankings": "Computing Rankings",
            "Calculating Statistics": "Calculating Statistics",
            "Preparing Display": "Preparing Display"
        }
    
    def update(self, progress_value: float, message: str) -> None:
        """Update progress with the current message and progress value."""
        try:
            # The orchestrator calls with 0.0-1.0 range, convert to the progress manager's range
            # MultiStageProgress uses ProgressManager internally which expects step counts
            if hasattr(self.progress, 'pm') and self.progress.pm:
                # Convert 0.0-1.0 to step count based on total_weight
                total_weight = getattr(self.progress, 'total_weight', 100)
                step_count = int(progress_value * total_weight)
                self.progress.pm.update(step_count, message)
                
            # Log progress for debugging
            logger.debug(f"Progress: {progress_value:.1%} - {message}")
        except Exception as e:
            logger.warning(f"Failed to update progress: {e}")
            # Continue without breaking the analysis
    
    def stage(self, stage_name: str):
        """Create a stage context manager."""
        mapped_stage_name = self.stage_mapping.get(stage_name, stage_name)
        return self.progress.stage(mapped_stage_name)


class StreamlitController:
    """Streamlit controller."""
    
    def __init__(self):
        # Create Streamlit adapters
        adapter = StreamlitAdapter()
        self.state_manager = adapter.state
        self.notification_service = adapter.notifications
        self.app_state = adapter.app_state
        
        # Initialize UI components
        self.sidebar_manager = SidebarManager(self.app_state, self.notification_service)
        self.metrics_renderer = MetricsRenderer()
        self.tab_manager = TabManager(self.app_state)
        
        # Initialize session state for persistent cache instances
        if 'league_cache_instances' not in st.session_state:
            st.session_state.league_cache_instances = {}
    
    def run(self) -> None:
        """Main entry point for the Streamlit application."""
        try:
            st.set_page_config(
                page_title="NFL Team Statistics Dashboard",
                page_icon="🏈",
                layout="wide",
                initial_sidebar_state="expanded"
            )
            
            inject_custom_css()
            
            # First get basic selections without analysis data
            selections = self.sidebar_manager.render()
            
            if selections.team_abbreviation and selections.season_year:
                self._render_team_analysis_with_sidebar(selections)
            else:
                self._render_welcome_screen()
                
        except Exception as e:
            logger.error(f"Application error: {e}")
            st.error("An unexpected error occurred. Please try refreshing the page.")
    
    def _render_team_analysis_with_sidebar(self, selections) -> None:
        """Render the main team analysis interface with sidebar updates."""
        try:
            
            # Inject team colors
            inject_team_colors(selections.team_abbreviation)
            
            # Create analysis request
            request = TeamAnalysisRequest(
                team_abbreviation=selections.team_abbreviation,
                season_year=selections.season_year,
                season_type_filter=selections.season_type_filter,
                configuration=selections.configuration,
                cache_nfl_data=selections.cache_nfl_data
            )
            
            # Check for existing analysis (include season type and config hash in cache key)
            config_hash = self._get_cache_config_hash(request.configuration)
            cache_key = f"analysis_{request.team_abbreviation}_{request.season_year}_{request.season_type_filter}_{config_hash}"
            
            # Skip cache if user wants fresh data
            analysis_response = None
            
            if analysis_response is None:
                # Reset analysis state to clear stale UI elements
                self.app_state.reset_analysis()
                
                # Create main content container that will be populated after analysis
                main_content = st.empty()
                
                with main_content.container():
                    # Show appropriate message based on why we're recalculating
                    st.info("🔄 Loading team statistics...")
                    
                    # Perform new analysis with progress tracking
                    analysis_response = self._perform_analysis_with_progress(request)
                
                # Clear the loading message and render results
                main_content.empty()
                
                if analysis_response:
                    # Cache the result
                    self.state_manager.set(cache_key, analysis_response)
                    
                    # Store analyzed selections for comparison
                    self.app_state.set_analyzed_selections(
                        request.team_abbreviation, 
                        request.season_year, 
                        request.season_type_filter
                    )
                    
                    # Mark analysis as complete
                    self.app_state.set_analysis_complete(analysis_response)
            
            if analysis_response:
                self._render_analysis_results(analysis_response, selections)
                # Force re-render sidebar with data status
                self._rerender_sidebar_with_data_status(analysis_response)
            
        except DataNotFoundError as e:
            self._render_specific_error_message(str(e), selections)
        except UseCaseError as e:
            st.error(f"Analysis failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during analysis: {e}")
            st.error("An unexpected error occurred during analysis.")
    
    def _perform_analysis_with_progress(self, request: TeamAnalysisRequest):
        """Perform analysis with progress tracking."""
        # Create controller with injected dependencies
        try:
            controller = TeamAnalysisController()
                
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to create TeamAnalysisController via DI: {e}")
            error_message = str(e)
            st.error(f"Failed to initialize analysis components: {error_message}")
            return
        
        # Get or create a league cache instance
        cache_key = "nfl_api"
        
        if request.cache_nfl_data:
            # Use persistent cache instance when caching is enabled
            if cache_key not in st.session_state.league_cache_instances:
                st.session_state.league_cache_instances[cache_key] = get_configured_cache()
            league_cache = st.session_state.league_cache_instances[cache_key]
        else:
            # Create a fresh cache instance when caching is disabled (forces fresh data)
            league_cache = get_configured_cache()
        
        # Configure NFL data caching
        if hasattr(league_cache, 'set_nfl_data_caching') and hasattr(request, 'cache_nfl_data'):
            league_cache.set_nfl_data_caching(request.cache_nfl_data)
        
        controller._orchestrator._league_cache = league_cache
        
        
        # Create progress tracker
        progress_manager = create_data_loading_progress()
        
        try:
            # Execute with progress tracking using the context manager properly
            with progress_manager.track_overall_progress("Analyzing NFL Statistics") as multi_stage:
                progress_adapter = MultiStageProgressAdapter(multi_stage)
                analysis_response = controller.analyze_team(request, progress_adapter)
                return analysis_response
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    
    
    def _get_cache_config_hash(self, configuration: Dict) -> str:
        """Get configuration hash for cache key generation."""
        import json
        import hashlib
        
        # Create a deterministic string representation
        # Sort keys and handle nested dicts consistently  
        def normalize_config(obj):
            if isinstance(obj, dict):
                return {k: normalize_config(v) for k, v in sorted(obj.items())}
            elif isinstance(obj, list):
                return [normalize_config(item) for item in obj]
            else:
                return obj
        
        normalized = normalize_config(configuration)
        config_string = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
        return hashlib.md5(config_string.encode()).hexdigest()[:8]  # Short hash for readability
    
    def _render_analysis_results(self, analysis_response, selections) -> None:
        """Render the analysis results."""
        # Render team header
        self.metrics_renderer.render_team_header(
            analysis_response.team, 
            analysis_response.season,
            season_type_filter=selections.season_type_filter,
            team_record=analysis_response.team_record,
            game_stats=analysis_response.game_stats
        )
        
        # Create container for season metrics that can be cleared
        metrics_container = st.container()
        with metrics_container:
            # Render season metrics
            self.metrics_renderer.render_season_metrics(analysis_response)
        
        # Create container for tabs that can be cleared  
        tabs_container = st.container()
        with tabs_container:
            # Render main content tabs
            self.tab_manager.render_analysis_tabs(
                analysis_response=analysis_response
            )
    
    
    def _render_specific_error_message(self, error_message: str, selections) -> None:
        """Render a specific error message, or fall back to generic message."""
        if "did not make the playoffs" in error_message:
            # Show specific playoff message with helpful UI
            st.warning(f"""
            🏈 **{error_message}**
            
            💡 **Quick Fix**: Use the season type selector above to choose:
            - **Regular Season** - See their regular season performance
            - **All Games** - See complete season overview
            """)
        else:
            # Fall back to generic no data message
            self._render_no_data_message(selections)
    
    def _render_no_data_message(self, selections) -> None:
        """Render a message when no data is available."""
        st.warning(f"""
        No data available for **{selections.team_abbreviation}** in **{selections.season_year}**.
        
        This could be because:
        - The season hasn't started yet
        - The team didn't exist in that season
        - There's a data loading issue
        
        Please try a different team or season.
        """)
    
    def _rerender_sidebar_with_data_status(self, analysis_response):
        """Force re-render sidebar with data status information."""
        try:
            # Force a sidebar rerender with the analysis data
            with st.sidebar:
                self.sidebar_manager._render_data_status_sidebar(analysis_response)
        except Exception as e:
            logger.debug(f"Could not rerender sidebar with data status: {e}")
    
    def _render_welcome_screen(self) -> None:
        """Render the welcome screen when no team is selected."""
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            ## Welcome to the NFL Statistics Dashboard! 🏈
            
            ### Getting Started
            1. **Select a team** from the sidebar
            2. **Choose a season** to analyze
            3. **Customize filters** (optional)
            4. **Click "Analyze Team"** to view statistics
            
            ### Features
            - 📊 Comprehensive team statistics
            - 🏆 League rankings and comparisons
            - 📈 Game-by-game performance charts
            - 📋 Detailed methodology explanations
            - 📥 Export capabilities
            
            ### Tips
            - Use **Turbo Mode** for faster loading with cached data
            - Try different **Season Types** (Regular, Playoffs, All)
            - Explore the **Configuration** options for advanced filtering
            """)
            
            st.info("👈 Start by selecting a team from the sidebar!")


def main():
    """Main entry point for the Streamlit application."""
    controller = StreamlitController()
    controller.run()


if __name__ == "__main__":
    main()