# src/presentation/streamlit/streamlit_controller.py - Streamlit controller

import streamlit as st
import logging
import time
from datetime import timedelta

from .controllers.team_analysis_controller import TeamAnalysisController
from ...application.dto import TeamAnalysisRequest
from ...domain.exceptions import DataNotFoundError, UseCaseError
from ...infrastructure.frameworks.streamlit_utils import StreamlitAdapter
from .components.sidebar_manager import SidebarManager
from .components.metrics_renderer import MetricsRenderer
from .components.tab_manager import TabManager
from .components.progress_manager import create_data_loading_progress
from .styling.app_styling import inject_custom_css
from ...infrastructure.cache.session_resources import analysis_orchestrator
from ...utils.config_hasher import get_config_hash
from ...utils.cache_policy import get_season_cache_ttl

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
        self.analysis_cache = adapter.cache
        self.notification_service = adapter.notifications
        self.app_state = adapter.app_state
        
        # Initialize UI components
        self.sidebar_manager = SidebarManager(self.app_state, self.notification_service)
        self.metrics_renderer = MetricsRenderer()
        self.tab_manager = TabManager(self.app_state)
        

    def run(self) -> None:
        """Main entry point for the Streamlit application."""
        try:
            st.set_page_config(
                page_title="NFL Team Statistics Dashboard",
                page_icon=":material/bar_chart:",
                layout="wide",
                initial_sidebar_state="collapsed"
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
            
            # Create analysis request
            request = TeamAnalysisRequest(
                team_abbreviation=selections.team_abbreviation,
                season_year=selections.season_year,
                season_type_filter=selections.season_type_filter,
                configuration=selections.configuration,
                cache_nfl_data=selections.cache_nfl_data
            )
            
            # Disabling the cache requests a fresh snapshot. Also discard this
            # session's response cache so re-enabling cannot restore an old one.
            if (
                not request.cache_nfl_data
                and self.app_state.get_analyzed_cache_mode() is not False
            ):
                self.analysis_cache.clear()

            # Check for existing analysis (include season type and config hash in cache key)
            config_hash = get_config_hash(request.configuration)
            cache_key = f"analysis_{request.team_abbreviation}_{request.season_year}_{request.season_type_filter}_{config_hash}"

            analysis_response = self._get_reusable_analysis(
                request, selections, cache_key
            )
            computed_analysis = analysis_response is None
            
            if analysis_response is None:
                # Reset analysis state to clear stale UI elements
                self.app_state.reset_analysis()
                
                # Create main content container that will be populated after analysis
                main_content = st.empty()
                
                with main_content.container():
                    # Show appropriate message based on why we're recalculating
                    st.info("Loading team statistics...")
                    
                    # Perform new analysis with progress tracking
                    analysis_response = self._perform_analysis_with_progress(request)
                
                # Clear the loading message and render results
                main_content.empty()
                
            if analysis_response:
                # A rerun must not restart the lifetime of an existing response.
                if request.cache_nfl_data and computed_analysis:
                    ttl = get_season_cache_ttl(request.season_year)
                    source_expiry = analysis_response.source_data_expires_at
                    if source_expiry is not None:
                        ttl = min(ttl, source_expiry - time.time())
                    # A late calculation must not extend its source's lifetime.
                    # Zero TTL means untimed in the response cache, so skip it.
                    if ttl > 0:
                        self.analysis_cache.set(
                            cache_key, analysis_response, ttl=timedelta(seconds=ttl),
                        )
                self.app_state.set_analyzed_selections(
                    request.team_abbreviation,
                    request.season_year,
                    request.season_type_filter,
                    request.cache_nfl_data,
                )
                self.app_state.set_analysis_complete(analysis_response)
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

    def _get_reusable_analysis(self, request, selections, cache_key):
        """Reuse a matching response without suppressing an intentional refresh."""
        if request.cache_nfl_data:
            cached_response = self.analysis_cache.get(cache_key)
            if (
                cached_response is not None
                and cached_response.source_data_expires_at is not None
                and time.time() >= cached_response.source_data_expires_at
            ):
                self.analysis_cache.delete(cache_key)
                return None
            # A miss includes expiry. Do not fall through to CURRENT_ANALYSIS,
            # which has no TTL and would otherwise make this cache permanent.
            return cached_response
        elif self.app_state.get_analyzed_cache_mode() is not False:
            # Switching caching off is the explicit refresh action. Once that
            # fresh result is displayed, unrelated Streamlit reruns may reuse it.
            return None

        if selections.should_analyze or not self.app_state.is_analysis_complete():
            return None

        analyzed = self.app_state.get_analyzed_selections()
        requested = (
            request.team_abbreviation,
            request.season_year,
            request.season_type_filter,
        )
        if analyzed == requested:
            return self.app_state.get_current_analysis()
        return None
    
    def _perform_analysis_with_progress(self, request: TeamAnalysisRequest):
        """Perform analysis with progress tracking."""
        # The resource lease covers initialization and execution. Temporary,
        # cache-off resources are released even when setup or analysis fails.
        with analysis_orchestrator(request.cache_nfl_data) as orchestrator:
            try:
                controller = TeamAnalysisController(calculation_orchestrator=orchestrator)
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to create TeamAnalysisController via DI: {e}")
                st.error(f"Failed to initialize analysis components: {e}")
                return None

            progress_manager = create_data_loading_progress()
            try:
                with progress_manager.track_overall_progress("Analyzing NFL Statistics") as multi_stage:
                    progress_adapter = MultiStageProgressAdapter(multi_stage)
                    return controller.analyze_team(request, progress_adapter)
            except Exception:
                logger.exception("Analysis failed")
                raise

    def _render_analysis_results(self, analysis_response, selections) -> None:
        """Render the analysis results."""
        # Render team header
        self.metrics_renderer.render_team_header(
            analysis_response.team, 
            analysis_response.season,
            season_type_filter=selections.season_type_filter,
            team_record=analysis_response.team_record,
            game_stats=analysis_response.game_stats,
            season_stats=analysis_response.season_stats,
            toer_rank=(analysis_response.rankings or {}).get('toer'),
            league_toer=(analysis_response.league_averages or {}).get('toer'),
            toer_allowed_rank=(analysis_response.rankings or {}).get('toer_allowed'),
            league_toer_allowed=(analysis_response.league_averages or {}).get('toer_allowed'),
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
                analysis_response=analysis_response,
                cache_nfl_data=selections.cache_nfl_data,
            )
    
    
    def _render_specific_error_message(self, error_message: str, selections) -> None:
        """Render a specific error message, or fall back to generic message."""
        if "did not make the playoffs" in error_message:
            # Show specific playoff message with helpful UI
            st.warning(f"""
            **{error_message}**
            
            Use the season type selector to choose:
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
        """Show the displayed snapshot's source date beneath the analysis."""
        try:
            with st.container(key="analysis_source_status"):
                self.sidebar_manager._render_data_status_sidebar(analysis_response)
        except Exception as e:
            logger.debug(f"Could not rerender sidebar with data status: {e}")
    
    def _render_welcome_screen(self) -> None:
        """Render the welcome screen when no team is selected."""
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            ## Welcome to the NFL Statistics Dashboard
            
            ### Getting Started
            1. **Select a team** in the filters above
            2. **Choose a season** to analyze
            3. **Choose a season type** and adjust **Analysis settings** if needed

            Statistics update automatically when you change your selections.
            
            ### Features
            - Comprehensive team statistics
            - League rankings and comparisons
            - Game-by-game statistics
            - Detailed methodology explanations
            - Export capabilities
            
            ### Tips
            - Enable **Cache NFL data for session** in **Analysis settings** to reuse loaded data
            - Try different **Season Types** (Regular, Playoffs, All)
            - Use **Analysis settings** to include or exclude QB kneels and spikes
            """)
            
            st.info("Start by selecting a team in the filters above.")


def main():
    """Main entry point for the Streamlit application."""
    controller = StreamlitController()
    controller.run()


if __name__ == "__main__":
    main()
