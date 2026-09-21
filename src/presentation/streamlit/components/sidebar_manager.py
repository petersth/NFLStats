# src/presentation/streamlit/components/sidebar_manager.py - Sidebar management

import streamlit as st
from dataclasses import dataclass
from typing import Dict
from ....config import NFL_TEAMS
from ....utils.season_utils import get_current_nfl_season_info
from ....utils.configuration_utils import get_configuration
from ....domain.services import get_data_status


@dataclass
class SidebarState:
    """State object for sidebar selections."""
    team_abbreviation: str
    season_year: int
    season_type_filter: str
    configuration: Dict
    should_analyze: bool
    config_changed: bool = False
    cache_nfl_data: bool = False
    
class SidebarManager:
    """Manages the sidebar UI and state."""
    
    def __init__(self, app_state, notification_service):
        self._app_state = app_state
        self._notification_service = notification_service
    
    def render(self) -> SidebarState:
        """Render sidebar and return state."""
        with st.sidebar:
            st.markdown("**Team & season**")
            
            # Select season first so we can show correct team names
            season_info = get_current_nfl_season_info()
            season_year = st.selectbox(
                "Select Season",
                options=season_info['available_seasons'],
                index=0
            )
            
            team_options = self._get_team_options(season_year)
            
            # Use the team_selector key directly if it exists (user just selected)
            # Otherwise fall back to selected_team (for persistence across reruns)
            if 'team_selector' in st.session_state:
                current_team = st.session_state.team_selector
            else:
                current_team = st.session_state.get('selected_team', None)
            
            default_index = 0
            if current_team and current_team in team_options:
                default_index = list(team_options.keys()).index(current_team)
            
            team_abbreviation = st.selectbox(
                "Select Team",
                options=list(team_options.keys()),
                format_func=lambda x: team_options[x],
                index=default_index,
                key='team_selector'
            )
            
            # Store the selected team in session state for persistence
            st.session_state.selected_team = team_abbreviation
            
            season_type_options = {
                "Regular Season": "REG", 
                "Playoffs": "POST",
                "Regular Season + Playoffs": "ALL"
            }
            
            season_type_filter = st.selectbox(
                "Season Type",
                options=list(season_type_options.keys()),
                index=0
            )
            
            season_type_value = season_type_options[season_type_filter]
            
            with st.expander("Analysis settings", expanded=False):
                configuration = self._render_configuration()
                cache_nfl_data = st.checkbox(
                    "Cache NFL data for session",
                    value=True,
                    disabled=False,
                    help=(
                        "Cache NFL data and completed analyses for up to 30 minutes. "
                        "Unchecking immediately refreshes the current selection and "
                        "uses fresh nflverse data for subsequent analyses."
                    )
                )
            
            config_changed = self._check_config_changed(configuration)
            
            should_analyze = self._should_analyze_fixed(
                config_changed, team_abbreviation, season_year, season_type_value
            )
            self._app_state.set_current_selections(team_abbreviation, season_year, season_type_value)
            
            return SidebarState(
                team_abbreviation=team_abbreviation,
                season_year=season_year,
                season_type_filter=season_type_value,
                configuration=configuration,
                should_analyze=should_analyze,
                config_changed=config_changed,
                cache_nfl_data=cache_nfl_data,
            )
    
    def _should_analyze_fixed(self, config_changed: bool, 
                             team: str, season: int, season_type: str) -> bool:
        """Auto-trigger analysis when selections or configuration changes."""
        if not self._app_state.is_analysis_complete():
            return True
        selections_changed = self._check_selections_changed(team, season, season_type)
        return config_changed or selections_changed
    
    def _check_selections_changed(self, team: str, season: int, season_type: str) -> bool:
        """Check if team, season, or season type has changed since last analysis.
        
        This method implements a comparison system that tracks the last successfully
        analyzed selections and determines if any core selection (team, season, or 
        season type) has changed, requiring a new analysis to be performed.
        """
        if not self._app_state.is_analysis_complete():
            return False
            
        analyzed_team, analyzed_season, analyzed_season_type = self._app_state.get_analyzed_selections()
        
        return (team != analyzed_team or 
                season != analyzed_season or 
                season_type != analyzed_season_type)
    
    def _get_team_options(self, season_year: int) -> dict:
        """Get team options with appropriate names for the selected year."""
        from ....utils.team_code_mapper import get_team_display_name
        
        team_options = {}
        for team_abbr in NFL_TEAMS:
            # Get the historically accurate team name for this year
            display_name = get_team_display_name(team_abbr, season_year)
            team_options[team_abbr] = display_name
        
        # Sort by team name for better UX
        sorted_options = dict(sorted(team_options.items(), key=lambda x: x[1]))
        return sorted_options
    
    def _render_configuration(self) -> Dict:
        """Render configuration UI."""
        # Always use custom configuration
        configuration = get_configuration('custom')
        
        include_qb_kneels = st.checkbox(
            "Include QB kneels",
            value=configuration.get('include_qb_kneels_rushing', True) and configuration.get('include_qb_kneels_success_rate', True),
            help="Include QB kneel downs in all statistics (rushing, efficiency, volume metrics)"
        )
        
        include_qb_spikes = st.checkbox(
            "Include QB spikes", 
            value=configuration.get('include_spikes_completion', True) and configuration.get('include_spikes_success_rate', True),
            help="Include QB spikes (clock-stopping throws) in all statistics (passing, efficiency, volume metrics)"
        )
        
        configuration.update({
            'include_qb_kneels_rushing': include_qb_kneels,
            'include_qb_kneels_success_rate': include_qb_kneels,
            'include_spikes_completion': include_qb_spikes,
            'include_spikes_success_rate': include_qb_spikes
        })
        
        return configuration
    
    
    def _check_config_changed(self, current_config: Dict) -> bool:
        """Check if configuration has changed."""
        return self._app_state.check_config_changed(current_config)
    
    def _render_data_status_sidebar(self, analysis_response):
        """Render data status information in sidebar."""
        try:
            # Get data timestamp from repository instead of trying to parse game dates
            data_timestamp = self._get_data_timestamp(analysis_response.season.year)
            
            if data_timestamp:
                import pandas as pd
                # Convert to pandas timestamp and ensure it's timezone-naive
                latest_game_date = pd.to_datetime(data_timestamp)
                if latest_game_date.tz is not None:
                    latest_game_date = latest_game_date.tz_localize(None)
                
                # Get data status
                data_status = get_data_status(latest_game_date, analysis_response.season)
                
                if data_status.status_type == "warning":
                    st.warning(data_status.status_message)
                elif data_status.status_type == "error":
                    st.error(data_status.status_message)

                st.caption(f"Latest game in source: {data_status.latest_game_date}")
            else:
                st.caption("Latest game in source: unavailable")
                    
        except Exception as e:
            st.error(f"Data status error: {str(e)}")
            import logging
            logging.getLogger(__name__).debug(f"Could not render data status in sidebar: {e}")
    
    def _get_data_timestamp(self, season_year: int):
        """Get data timestamp from the shared league cache."""
        try:
            import streamlit as st
            
            # Use the same persistent cache instance that the main app uses
            cache_key = "calculation_orchestrator"
            
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'league_cache_instances'):
                if cache_key in st.session_state.league_cache_instances:
                    orchestrator = st.session_state.league_cache_instances[cache_key]
                    
                    # The orchestrator has a league_cache attribute which has the NFL data repository
                    if hasattr(orchestrator, 'league_cache') and orchestrator.league_cache:
                        league_cache = orchestrator.league_cache
                        
                        if hasattr(league_cache, '_nfl_data_repo') and league_cache._nfl_data_repo:
                            timestamp = league_cache._nfl_data_repo.get_data_timestamp(season_year)
                            if timestamp:
                                return timestamp
            
            # If no cached data available, return None (we don't want to fetch just for timestamp)
            return None
            
        except ImportError as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not import dependencies for data timestamp: {e}")
            return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not get data timestamp for season {season_year}: {e}")
            return None
    
