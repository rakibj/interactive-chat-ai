"""Session manager for WebSocket session lifecycle and isolation."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Set
from interactive_chat.api.models import SessionInfo, SessionState
from interactive_chat.api.event_buffer import EventBuffer


class SessionManager:
    """Manages WebSocket sessions: creation, storage, expiry, isolation."""
    
    # Session TTL: 30 minutes
    SESSION_TTL_SECONDS = 1800
    # Maximum concurrent sessions
    MAX_SESSIONS = 1000
    # Connections per IP limit
    MAX_CONNECTIONS_PER_IP = 5
    
    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, SessionInfo] = {}
        self.buffers: Dict[str, EventBuffer] = {}
        self.active_connections: Dict[str, Set[str]] = {}  # session_id -> set of connection IDs
        self.ip_connections: Dict[str, Set[str]] = {}  # IP -> set of session_ids
    
    def create_session(
        self,
        phase_profile: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SessionInfo:
        """
        Create new session.
        
        Args:
            phase_profile: Phase profile to load
            user_agent: Client user agent
            
        Returns:
            SessionInfo with new session_id
            
        Raises:
            RuntimeError: If max sessions reached
        """
        if len(self.sessions) >= self.MAX_SESSIONS:
            raise RuntimeError("Maximum sessions reached")
        
        now = datetime.utcnow().timestamp()
        session_id = str(uuid.uuid4())
        
        session = SessionInfo(
            session_id=session_id,
            created_at=now,
            state=SessionState.INITIALIZING,
            phase_profile=phase_profile,
            user_agent=user_agent,
            last_activity=now
        )
        
        self.sessions[session_id] = session
        self.buffers[session_id] = EventBuffer(max_size=100)
        self.active_connections[session_id] = set()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionInfo if exists and not expired, None otherwise
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if expired
        age_seconds = datetime.utcnow().timestamp() - session.created_at
        if age_seconds > self.SESSION_TTL_SECONDS:
            self.delete_session(session_id)
            return None
        
        # Check last activity
        inactivity_seconds = datetime.utcnow().timestamp() - session.last_activity
        if inactivity_seconds > self.SESSION_TTL_SECONDS:
            self.delete_session(session_id)
            return None
        
        return session
    
    def update_activity(self, session_id: str) -> None:
        """
        Update session last_activity timestamp.
        
        Args:
            session_id: Session to update
        """
        if session_id in self.sessions:
            self.sessions[session_id].last_activity = datetime.utcnow().timestamp()
    
    def set_session_state(self, session_id: str, state: str) -> bool:
        """
        Set session state.
        
        Args:
            session_id: Session to update
            state: New state (INITIALIZING, ACTIVE, PAUSED, COMPLETED, ERROR)
            
        Returns:
            True if updated, False if session not found
        """
        if session_id not in self.sessions:
            return False
        
        self.sessions[session_id].state = state
        self.update_activity(session_id)
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete session and its event buffer.
        
        Args:
            session_id: Session to delete
            
        Returns:
            True if deleted, False if not found
        """
        if session_id not in self.sessions:
            return False
        
        # Remove connections mapping
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        # Remove buffer
        if session_id in self.buffers:
            del self.buffers[session_id]
        
        # Remove session
        del self.sessions[session_id]
        
        return True
    
    def get_buffer(self, session_id: str) -> Optional[EventBuffer]:
        """
        Get event buffer for session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            EventBuffer if exists, None otherwise
        """
        return self.buffers.get(session_id)
    
    def add_connection(self, session_id: str, connection_id: str) -> bool:
        """
        Register a WebSocket connection to session.
        
        Args:
            session_id: Session identifier
            connection_id: Unique connection identifier
            
        Returns:
            True if added, False if session not found
        """
        if session_id not in self.active_connections:
            return False
        
        self.active_connections[session_id].add(connection_id)
        self.update_activity(session_id)
        return True
    
    def remove_connection(self, session_id: str, connection_id: str) -> bool:
        """
        Unregister a WebSocket connection from session.
        
        Args:
            session_id: Session identifier
            connection_id: Connection to remove
            
        Returns:
            True if removed, False if not found
        """
        if session_id not in self.active_connections:
            return False
        
        self.active_connections[session_id].discard(connection_id)
        
        # Delete session if no active connections (optional cleanup)
        # Commented out: let TTL handle cleanup instead
        # if not self.active_connections[session_id]:
        #     self.delete_session(session_id)
        
        return True
    
    def get_active_connections(self, session_id: str) -> Set[str]:
        """
        Get all active connection IDs for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Set of connection IDs
        """
        return self.active_connections.get(session_id, set()).copy()
    
    def check_ip_limit(self, client_ip: str) -> bool:
        """
        Check if client IP has reached connection limit.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if under limit, False if at/over limit
        """
        if client_ip not in self.ip_connections:
            return True
        
        return len(self.ip_connections[client_ip]) < self.MAX_CONNECTIONS_PER_IP
    
    def register_ip_connection(self, client_ip: str, session_id: str) -> bool:
        """
        Register IP to session mapping.
        
        Args:
            client_ip: Client IP address
            session_id: Session identifier
            
        Returns:
            True if registered, False if IP limit exceeded
        """
        if not self.check_ip_limit(client_ip):
            return False
        
        if client_ip not in self.ip_connections:
            self.ip_connections[client_ip] = set()
        
        self.ip_connections[client_ip].add(session_id)
        return True
    
    def unregister_ip_connection(self, client_ip: str, session_id: str) -> None:
        """
        Unregister IP to session mapping.
        
        Args:
            client_ip: Client IP address
            session_id: Session to unregister
        """
        if client_ip in self.ip_connections:
            self.ip_connections[client_ip].discard(session_id)
            if not self.ip_connections[client_ip]:
                del self.ip_connections[client_ip]
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (called periodically).
        
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow().timestamp()
        expired = []
        
        for session_id, session in self.sessions.items():
            age_seconds = now - session.created_at
            inactivity_seconds = now - session.last_activity
            
            if age_seconds > self.SESSION_TTL_SECONDS or inactivity_seconds > self.SESSION_TTL_SECONDS:
                expired.append(session_id)
        
        for session_id in expired:
            self.delete_session(session_id)
        
        return len(expired)
    
    def get_stats(self) -> Dict:
        """
        Get session manager statistics.
        
        Returns:
            Dictionary with session counts and stats
        """
        total_connections = sum(len(conns) for conns in self.active_connections.values())
        
        return {
            "total_sessions": len(self.sessions),
            "active_connections": total_connections,
            "session_states": {
                "initializing": sum(1 for s in self.sessions.values() if s.state == SessionState.INITIALIZING),
                "active": sum(1 for s in self.sessions.values() if s.state == SessionState.ACTIVE),
                "paused": sum(1 for s in self.sessions.values() if s.state == SessionState.PAUSED),
                "completed": sum(1 for s in self.sessions.values() if s.state == SessionState.COMPLETED),
                "error": sum(1 for s in self.sessions.values() if s.state == SessionState.ERROR),
            },
            "unique_ips": len(self.ip_connections),
            "buffer_size_total": sum(buf.size() for buf in self.buffers.values())
        }


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def set_session_manager(manager: SessionManager) -> None:
    """Set global session manager (for testing)."""
    global _session_manager
    _session_manager = manager
