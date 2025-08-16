# src/presentation/streamlit/components/session_monitor.py - Session monitoring component

import streamlit as st
from typing import Dict, Any
from ....infrastructure.cache.session_cleanup_manager import get_session_cleanup_info


class SessionMonitor:
    """Component for monitoring and displaying session cleanup status."""
    
    @staticmethod
    def render_session_status():
        """Render session status in the sidebar."""
        if st.checkbox("🔧 Show Session Info", help="Display session cleanup information"):
            SessionMonitor._show_session_details()
    
    @staticmethod
    def _show_session_details():
        """Show detailed session information."""
        try:
            cleanup_info = get_session_cleanup_info()
            
            st.markdown("#### Session Management")
            
            # Summary metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Active Sessions", 
                    cleanup_info['active_sessions'],
                    help="Number of active user sessions being tracked"
                )
            
            with col2:
                cleanup_status = "✅ Running" if cleanup_info['cleanup_thread_running'] else "❌ Stopped"
                st.metric(
                    "Cleanup Thread", 
                    cleanup_status,
                    help="Status of background cleanup thread"
                )
            
            # Detailed session info
            if cleanup_info['session_details']:
                with st.expander("Session Details"):
                    for session_id, details in cleanup_info['session_details'].items():
                        st.write(f"**Session:** {session_id[:8]}...")
                        st.write(f"• Age: {details['age_minutes']:.1f} min")
                        st.write(f"• Inactive: {details['inactive_minutes']:.1f} min")
                        st.write(f"• Has Data: {'Yes' if details['has_orchestrator'] else 'No'}")
                        st.write("---")
            
            # Manual cleanup button
            if st.button("🧹 Force Session Cleanup", help="Manually trigger cleanup of inactive sessions"):
                from ....infrastructure.cache.session_cleanup_manager import SessionCleanupManager
                SessionCleanupManager.force_cleanup_all()
                st.success("Manual cleanup triggered!")
                st.rerun()
                
        except Exception as e:
            st.error(f"Error displaying session info: {e}")
    
    @staticmethod
    def render_memory_warning():
        """Show warning if many sessions are active."""
        try:
            cleanup_info = get_session_cleanup_info()
            active_sessions = cleanup_info['active_sessions']
            
            if active_sessions > 5:
                st.warning(f"⚠️ {active_sessions} active sessions detected. "
                          f"Memory usage may be high from multiple users.")
            elif active_sessions > 10:
                st.error(f"🚨 {active_sessions} active sessions! "
                        f"Consider restarting the app to free memory.")
                
        except Exception:
            pass  # Silently fail to avoid disrupting main app


def render_session_cleanup_status():
    """Render session cleanup status in sidebar (simplified version)."""
    try:
        cleanup_info = get_session_cleanup_info()
        active_sessions = cleanup_info['active_sessions']
        
        if active_sessions > 1:
            st.sidebar.caption(f"👥 {active_sessions} active sessions")
            
    except Exception:
        pass  # Silently fail