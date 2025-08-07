# src/presentation/streamlit/components/sidebar_manager.py - Sidebar management

import streamlit as st
from dataclasses import dataclass
from typing import Dict
from ....config import NFL_TEAMS, TEAM_DATA
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
            st.subheader("Team & Season")
            
            team_abbreviation = st.selectbox(
                "Select Team",
                options=NFL_TEAMS,
                index=NFL_TEAMS.index('ARI')
            )
            
            self._render_team_info(team_abbreviation)
            
            season_info = get_current_nfl_season_info()
            season_year = st.selectbox(
                "Select Season",
                options=season_info['available_seasons'],
                index=0
            )
            
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
            
            st.divider()
            
            configuration = self._render_configuration()
            
            st.markdown("#### Cache Settings")

            cache_nfl_data = st.checkbox(
                "Cache NFL data for session",
                value=True,
                disabled=False,
                help="Cache NFL library data in memory to avoid reloading for each team. Unchecking forces fresh API calls for every analysis."
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
    
    def _render_team_info(self, team_abbreviation: str):
        """Render team information display."""
        if team_abbreviation and team_abbreviation in TEAM_DATA:
            team_info = TEAM_DATA[team_abbreviation]
            primary_color = team_info['colors'][0]
            secondary_color = team_info['colors'][1] if len(team_info['colors']) > 1 else primary_color
            
            st.markdown(f"""
            <div style="text-align: center; 
                        padding: 15px; 
                        background: linear-gradient(135deg, {primary_color}, {secondary_color}); 
                        border-radius: 10px; 
                        margin-bottom: 15px;
                        color: white;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <div style="font-size: 1.8em; margin-bottom: 8px;">{team_info['logo']}</div>
                <div style="font-size: 1.1em; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">{team_info['name']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_configuration(self) -> Dict:
        """Render configuration UI."""
        st.markdown("### Statistics Configuration")
        
        # Always use custom configuration
        configuration = get_configuration('custom')
        
        # Play Exclusion Settings
        st.markdown("#### Play Exclusions")
        
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
            # Add divider before data status
            st.divider()
            st.subheader("Data Status")
            
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
                
                # Always show data status in sidebar
                if data_status.status_type == "success":
                    st.success(f"📅 {data_status.status_message}")
                elif data_status.status_type == "warning":
                    st.warning(f"📅 {data_status.status_message}")
                else:
                    st.info(f"📅 {data_status.status_message}")
                
                st.caption(f"Latest game: {data_status.latest_game_date}")
            else:
                st.info("📅 Data status: Unable to determine data timestamp")
                    
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
    
