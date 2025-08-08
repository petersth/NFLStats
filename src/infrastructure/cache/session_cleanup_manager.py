# src/infrastructure/cache/session_cleanup_manager.py - Session cleanup management

import streamlit as st
import time
import logging
import threading
import weakref
from typing import Dict, Set, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SessionCleanupManager:
    """
    Manages cleanup of data from disconnected Streamlit sessions.
    
    Tracks active sessions and cleans up data when sessions disconnect
    or become inactive.
    """
    
    # Class-level tracking of all sessions
    _active_sessions: Dict[str, Dict] = {}
    _cleanup_thread: Optional[threading.Thread] = None
    _cleanup_running = False
    _lock = threading.Lock()
    
    def __init__(self):
        self.session_id = self._get_session_id()
        self._register_session()
        self._ensure_cleanup_thread()
    
    @staticmethod
    def _get_session_id() -> str:
        """Get unique session identifier from Streamlit."""
        try:
            # Try to get session ID from Streamlit runtime
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            ctx = get_script_run_ctx()
            if ctx and ctx.session_id:
                return ctx.session_id
        except:
            pass
        
        # Fallback to session state hash
        return str(hash(str(st.session_state)))
    
    @classmethod
    def _is_session_alive(cls, session_id: str) -> bool:
        """Check if a session is still alive in Streamlit."""
        try:
            from streamlit.runtime import get_instance
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            
            runtime = get_instance()
            if runtime and hasattr(runtime, '_session_mgr'):
                # Check if session exists in Streamlit's session manager
                session_info = runtime._session_mgr.get_session_info(session_id)
                return session_info is not None
        except:
            # If we can't check, assume it's alive
            return True
        
        return True
    
    def _register_session(self):
        """Register this session for tracking."""
        with self._lock:
            self._active_sessions[self.session_id] = {
                'created_at': time.time(),
                'last_activity': time.time(),
                'last_heartbeat': time.time(),  # Track heartbeat separately
                'cleanup_registered': False,
                'orchestrator_ref': None
            }
            session_short_id = self.session_id[:8] if len(self.session_id) > 8 else self.session_id
            logger.info(f"USER CONNECTED - Session {session_short_id} started")
    
    def update_activity(self):
        """Update last activity timestamp for this session."""
        with self._lock:
            if self.session_id in self._active_sessions:
                self._active_sessions[self.session_id]['last_activity'] = time.time()
    
    def register_orchestrator(self, orchestrator):
        """Register orchestrator for cleanup when session ends."""
        with self._lock:
            if self.session_id in self._active_sessions:
                # Use weak reference to avoid circular references
                self._active_sessions[self.session_id]['orchestrator_ref'] = weakref.ref(orchestrator)
                session_short_id = self.session_id[:8] if len(self.session_id) > 8 else self.session_id
                logger.info(f"DATA REGISTERED - Session {session_short_id} has cached data to track")
    
    def cleanup_session(self, session_id: str = None):
        """Clean up data for a specific session."""
        if session_id is None:
            session_id = self.session_id
        
        with self._lock:
            session_data = self._active_sessions.get(session_id)
            if not session_data:
                return
            
            # Calculate session duration
            session_duration_minutes = (time.time() - session_data['created_at']) / 60
            session_short_id = session_id[:8] if len(session_id) > 8 else session_id
            
            logger.info(f"USER DISCONNECT DETECTED - Session {session_short_id} ended (duration: {session_duration_minutes:.1f} minutes)")
            
            # Clean up orchestrator if it still exists
            orchestrator_ref = session_data.get('orchestrator_ref')
            cleanup_stats = {'memory': 0, 'rankings': 0, 'raw_data': 0}
            
            if orchestrator_ref:
                orchestrator = orchestrator_ref()
                if orchestrator and hasattr(orchestrator, 'league_cache'):
                    try:
                        cleanup_stats = orchestrator.league_cache.clear_cache()
                        total_entries_freed = sum(cleanup_stats.values())
                        logger.info(f"CACHE CLEARED - Session {session_short_id}: {total_entries_freed} entries freed {cleanup_stats}")
                    except Exception as e:
                        logger.error(f"CLEANUP ERROR - Session {session_short_id}: {e}")
            else:
                logger.info(f"NO DATA TO CLEAR - Session {session_short_id} had no cached data")
            
            # Remove from active sessions
            del self._active_sessions[session_id]
            logger.info(f"SESSION CLEANUP COMPLETE - Session {session_short_id} removed from tracking")
    
    @classmethod
    def _ensure_cleanup_thread(cls):
        """Ensure cleanup thread is running."""
        if not cls._cleanup_running:
            cls._cleanup_running = True
            cls._cleanup_thread = threading.Thread(
                target=cls._cleanup_worker,
                daemon=True,
                name="SessionCleanupThread"
            )
            cls._cleanup_thread.start()
            logger.info("SESSION MONITOR STARTED - Background cleanup thread is running")
    
    @classmethod
    def _cleanup_worker(cls):
        """Background worker to clean up inactive sessions."""
        check_interval = 30  # Check every 30 seconds for faster detection
        quick_timeout = 300  # 5 minutes for quick cleanup
        normal_timeout = 1800  # 30 minutes for normal cleanup
        
        while cls._cleanup_running:
            try:
                # Check for both quick disconnects and long-term inactive sessions
                cls._cleanup_inactive_sessions(quick_timeout=quick_timeout, normal_timeout=normal_timeout)
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Session cleanup worker error: {e}")
                time.sleep(check_interval)
    
    @classmethod
    def _cleanup_inactive_sessions(cls, quick_timeout=300, normal_timeout=1800):
        """Clean up sessions that have been inactive.
        
        Args:
            quick_timeout: Timeout for sessions with no orchestrator (likely disconnected)
            normal_timeout: Timeout for sessions with data (normal inactivity)
        """
        current_time = time.time()
        
        with cls._lock:
            inactive_sessions = []
            disconnected_sessions = []
            
            for session_id, session_data in cls._active_sessions.items():
                last_activity = session_data['last_activity']
                inactive_duration = current_time - last_activity
                has_orchestrator = session_data.get('orchestrator_ref') is not None
                
                # Check if session is still alive in Streamlit
                if not cls._is_session_alive(session_id):
                    disconnected_sessions.append(session_id)
                    continue
                
                # Use shorter timeout for sessions without data (likely disconnected)
                # and longer timeout for sessions with data
                timeout_to_use = normal_timeout if has_orchestrator else quick_timeout
                
                if inactive_duration > timeout_to_use:
                    inactive_sessions.append(session_id)
            
            # Clean up disconnected sessions immediately
            for session_id in disconnected_sessions:
                session_data = cls._active_sessions[session_id]
                session_duration_minutes = (current_time - session_data['created_at']) / 60
                session_short_id = session_id[:8] if len(session_id) > 8 else session_id
                
                logger.info(f"BROWSER CLOSED - Session {session_short_id} disconnected "
                           f"(duration: {session_duration_minutes:.1f}min)")
                
                # Clean up orchestrator
                orchestrator_ref = session_data.get('orchestrator_ref')
                cleanup_stats = {'memory': 0, 'rankings': 0, 'raw_data': 0}
                
                if orchestrator_ref:
                    orchestrator = orchestrator_ref()
                    if orchestrator and hasattr(orchestrator, 'league_cache'):
                        try:
                            cleanup_stats = orchestrator.league_cache.clear_cache()
                            total_entries_freed = sum(cleanup_stats.values())
                            logger.info(f"DISCONNECT CACHE CLEARED - Session {session_short_id}: {total_entries_freed} entries freed {cleanup_stats}")
                        except Exception as e:
                            logger.error(f"DISCONNECT CLEANUP ERROR - Session {session_short_id}: {e}")
                else:
                    logger.info(f"NO DATA TO CLEAR - Disconnected session {session_short_id} had no cached data")
                
                # Remove from tracking
                del cls._active_sessions[session_id]
                logger.info(f"DISCONNECTED SESSION REMOVED - Session {session_short_id} cleaned up")
            
            # Clean up inactive sessions
            for session_id in inactive_sessions:
                session_data = cls._active_sessions[session_id]
                inactive_minutes = (current_time - session_data['last_activity']) / 60
                session_duration_minutes = (current_time - session_data['created_at']) / 60
                session_short_id = session_id[:8] if len(session_id) > 8 else session_id
                
                # Determine if this looks like a disconnect vs inactivity
                if inactive_minutes < 10:
                    logger.info(f"SESSION DISCONNECT DETECTED - Session {session_short_id} "
                               f"(no activity for {inactive_minutes:.1f}min, total duration: {session_duration_minutes:.1f}min)")
                else:
                    logger.info(f"INACTIVE SESSION TIMEOUT - Session {session_short_id} "
                               f"(inactive: {inactive_minutes:.1f}min, total duration: {session_duration_minutes:.1f}min)")
                
                # Clean up orchestrator
                orchestrator_ref = session_data.get('orchestrator_ref')
                cleanup_stats = {'memory': 0, 'rankings': 0, 'raw_data': 0}
                
                if orchestrator_ref:
                    orchestrator = orchestrator_ref()
                    if orchestrator and hasattr(orchestrator, 'league_cache'):
                        try:
                            cleanup_stats = orchestrator.league_cache.clear_cache()
                            total_entries_freed = sum(cleanup_stats.values())
                            logger.info(f"INACTIVE CACHE CLEARED - Session {session_short_id}: {total_entries_freed} entries freed {cleanup_stats}")
                        except Exception as e:
                            logger.error(f"INACTIVE CLEANUP ERROR - Session {session_short_id}: {e}")
                else:
                    logger.info(f"NO DATA TO CLEAR - Inactive session {session_short_id} had no cached data")
                
                # Remove from tracking
                del cls._active_sessions[session_id]
                logger.info(f"INACTIVE SESSION REMOVED - Session {session_short_id} cleaned up and removed")
    
    @classmethod
    def get_active_session_count(cls) -> int:
        """Get number of active sessions being tracked."""
        with cls._lock:
            return len(cls._active_sessions)
    
    @classmethod
    def get_session_info(cls) -> Dict:
        """Get information about active sessions."""
        current_time = time.time()
        
        with cls._lock:
            session_info = {}
            for session_id, data in cls._active_sessions.items():
                session_info[session_id] = {
                    'created_at': datetime.fromtimestamp(data['created_at']).isoformat(),
                    'last_activity': datetime.fromtimestamp(data['last_activity']).isoformat(),
                    'age_minutes': (current_time - data['created_at']) / 60,
                    'inactive_minutes': (current_time - data['last_activity']) / 60,
                    'has_orchestrator': data['orchestrator_ref'] is not None
                }
        
        return session_info
    
    @classmethod
    def force_cleanup_all(cls):
        """Force cleanup of all tracked sessions."""
        with cls._lock:
            session_ids = list(cls._active_sessions.keys())
        
        if session_ids:
            logger.info(f"FORCE CLEANUP INITIATED - Cleaning {len(session_ids)} active sessions")
        
        total_cleaned = 0
        for session_id in session_ids:
            try:
                temp_manager = cls()
                temp_manager.cleanup_session(session_id)
                total_cleaned += 1
            except Exception as e:
                session_short_id = session_id[:8] if len(session_id) > 8 else session_id
                logger.error(f"FORCE CLEANUP ERROR - Session {session_short_id}: {e}")
        
        if session_ids:
            logger.info(f"FORCE CLEANUP COMPLETE - {total_cleaned}/{len(session_ids)} sessions cleaned")


def register_session_cleanup():
    """
    Register session cleanup for the current Streamlit session.
    Call this early in your Streamlit app.
    """
    # Initialize session cleanup manager
    if 'session_cleanup_manager' not in st.session_state:
        st.session_state.session_cleanup_manager = SessionCleanupManager()
        # Log total active sessions for monitoring
        total_active = SessionCleanupManager.get_active_session_count()
        logger.info(f"ACTIVE SESSIONS - {total_active} concurrent users being tracked")
    
    # Update activity
    st.session_state.session_cleanup_manager.update_activity()
    
    return st.session_state.session_cleanup_manager


def register_orchestrator_for_cleanup(orchestrator):
    """
    Register an orchestrator for cleanup when session ends.
    
    Args:
        orchestrator: The calculation orchestrator to clean up
    """
    if 'session_cleanup_manager' in st.session_state:
        st.session_state.session_cleanup_manager.register_orchestrator(orchestrator)
        # Log cache sizes being tracked
        if hasattr(orchestrator, 'league_cache'):
            cache_stats = {
                'memory': orchestrator.league_cache._memory_cache.get_stats()['size'],
                'rankings': orchestrator.league_cache._rankings_cache.get_stats()['size'],
                'raw_data': orchestrator.league_cache._raw_data_cache.get_stats()['size']
            }
            total_entries = sum(cache_stats.values())
            session_id = st.session_state.session_cleanup_manager.session_id
            session_short_id = session_id[:8] if len(session_id) > 8 else session_id
            logger.info(f"ORCHESTRATOR LINKED - Session {session_short_id} tracking {total_entries} cache entries {cache_stats}")
        else:
            logger.debug("Orchestrator registered for session cleanup (no cache found)")


def get_session_cleanup_info() -> Dict:
    """Get information about session cleanup status."""
    return {
        'active_sessions': SessionCleanupManager.get_active_session_count(),
        'cleanup_thread_running': SessionCleanupManager._cleanup_running,
        'session_details': SessionCleanupManager.get_session_info()
    }