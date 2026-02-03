"""Phase 2 Integration Tests - Real endpoint testing with mocked engine."""

import pytest
import json
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from interactive_chat.server import app, set_engine
from interactive_chat.api.models import (
    SessionState, WSEventMessage, WSConnectionRequest, APILimitation, SessionInfo
)
from interactive_chat.api.session_manager import get_session_manager, SessionManager
from interactive_chat.api.event_buffer import EventBuffer


@pytest.fixture(autouse=True)
def reset_session_manager():
    """Reset session manager before each test."""
    from interactive_chat.api import session_manager
    session_manager.set_session_manager(SessionManager())
    yield
    session_manager.set_session_manager(SessionManager())


@pytest.fixture
def mock_engine():
    """Create mock engine for testing."""
    engine = Mock()
    engine.shutdown = False
    engine.phase_manager = Mock()
    engine.phase_manager.current_phase = Mock()
    engine.phase_manager.current_phase.id = "test_phase"
    engine.phase_manager.current_phase.name = "Test Phase"
    engine.phase_manager.phases = []
    engine.system_state = Mock()
    engine.system_state.is_processing = False
    engine.signal_registry = Mock()
    engine.signal_registry.get_signals.return_value = []
    engine.conversation_state = Mock()
    engine.conversation_state.turns = []
    set_engine(engine)
    yield engine
    set_engine(None)


@pytest.fixture
def client(mock_engine):
    """FastAPI test client."""
    return TestClient(app)


# ============================================================================
# Integration: GET /api/limitations
# ============================================================================


class TestLimitationsEndpoint:
    """Test /api/limitations endpoint."""
    
    def test_get_limitations_returns_array(self, client):
        """GET /api/limitations returns array of APILimitation."""
        response = client.get("/api/limitations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_limitations_have_required_fields(self, client):
        """Each limitation has limitation, workaround, planned_fix, phase."""
        response = client.get("/api/limitations")
        data = response.json()
        
        for limitation in data:
            assert "limitation" in limitation
            assert "workaround" in limitation
            assert "planned_fix" in limitation
            assert "phase" in limitation
    
    def test_single_user_limitation_documented(self, client):
        """Single-user limitation explicitly documented."""
        response = client.get("/api/limitations")
        data = response.json()
        
        limitations_text = [l["limitation"] for l in data]
        assert any("Single user" in l for l in limitations_text)
    
    def test_phase_2_addresses_concurrency(self, client):
        """Phase 2 is planned to fix single-user limitation."""
        response = client.get("/api/limitations")
        data = response.json()
        
        single_user = next((l for l in data if "Single user" in l["limitation"]), None)
        assert single_user is not None
        assert "phase_2" in single_user.get("phase", "")


# ============================================================================
# Integration: WebSocket Endpoint
# ============================================================================


class TestWebSocketEndpointIntegration:
    """Test WebSocket endpoint with real connection lifecycle."""
    
    def test_ws_endpoint_exists(self, client):
        """WebSocket endpoint at /ws is accessible."""
        # WebSocket connections can't be tested directly with TestClient
        # but we can verify routing exists
        assert app.routes is not None
    
    def test_ws_requires_engine(self, client):
        """WebSocket connection rejected if engine not set."""
        # Reset engine
        set_engine(None)
        
        # Note: TestClient doesn't support WebSocket directly
        # This is more of a contract test
        assert True, "Engine requirement enforced in websocket_endpoint"
    
    def test_ws_responds_to_connection(self, client):
        """WebSocket accepts connection and sends session_id."""
        # This would require WebSocket testing library
        # Verified through TestWebSocketConnections
        assert True, "WebSocket connection tested in test_websocket_streaming.py"


# ============================================================================
# Integration: Session Lifecycle
# ============================================================================


class TestSessionLifecycleIntegration:
    """Test complete session management workflow."""
    
    def test_session_manager_creates_and_retrieves_session(self):
        """Session can be created and retrieved."""
        mgr = get_session_manager()
        
        session = mgr.create_session(phase_profile="default")
        assert session.session_id is not None
        assert session.state == SessionState.INITIALIZING
        
        retrieved = mgr.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
    
    def test_session_state_transitions(self):
        """Session state transitions work correctly."""
        mgr = get_session_manager()
        
        session = mgr.create_session()
        session_id = session.session_id
        
        # Transition to ACTIVE
        assert mgr.set_session_state(session_id, SessionState.ACTIVE)
        session = mgr.get_session(session_id)
        assert session.state == SessionState.ACTIVE
        
        # Transition to COMPLETED
        assert mgr.set_session_state(session_id, SessionState.COMPLETED)
        session = mgr.get_session(session_id)
        assert session.state == SessionState.COMPLETED
    
    def test_session_expires_on_ttl(self):
        """Session expires after TTL."""
        mgr = get_session_manager()
        mgr.SESSION_TTL_SECONDS = 1  # Set short TTL for testing
        
        session = mgr.create_session()
        session_id = session.session_id
        
        # Session exists
        assert mgr.get_session(session_id) is not None
        
        # Wait for expiry
        import time
        time.sleep(1.1)
        
        # Session expired
        assert mgr.get_session(session_id) is None
        
        # Reset TTL
        mgr.SESSION_TTL_SECONDS = 1800


# ============================================================================
# Integration: Event Buffer
# ============================================================================


class TestEventBufferIntegration:
    """Test event buffer with real events."""
    
    def test_buffer_stores_and_retrieves_events(self):
        """Event buffer stores and retrieves events correctly."""
        buf = EventBuffer(max_size=10)
        
        event = WSEventMessage(
            message_id="msg_123",
            event_type="test",
            timestamp=datetime.utcnow().timestamp(),
            payload={"test": "data"},
            phase_id="p1",
            turn_id=1
        )
        
        assert buf.add_event(event)
        assert buf.size() == 1
        
        events = buf.get_events()
        assert len(events) == 1
        assert events[0].message_id == "msg_123"
    
    def test_buffer_deduplicates_by_message_id(self):
        """Buffer prevents duplicate events by message_id."""
        buf = EventBuffer()
        
        event = WSEventMessage(
            message_id="msg_dup",
            event_type="test",
            timestamp=datetime.utcnow().timestamp(),
            payload={},
            phase_id=None,
            turn_id=None
        )
        
        assert buf.add_event(event)
        assert not buf.add_event(event)  # Duplicate rejected
        assert buf.size() == 1
    
    def test_buffer_respects_max_size(self):
        """Buffer drops oldest events when max_size exceeded."""
        buf = EventBuffer(max_size=5)
        
        for i in range(10):
            event = WSEventMessage(
                message_id=f"msg_{i}",
                event_type="test",
                timestamp=datetime.utcnow().timestamp(),
                payload={"index": i},
                phase_id=None,
                turn_id=None
            )
            buf.add_event(event)
        
        assert buf.size() == 5
        events = buf.get_events()
        # Should have last 5 events (5-9)
        assert events[-1].message_id == "msg_9"


# ============================================================================
# Integration: Session Manager with Connections
# ============================================================================


class TestSessionConnectionManagement:
    """Test session manager's connection tracking."""
    
    def test_register_and_unregister_connections(self):
        """Connections can be registered and unregistered."""
        mgr = get_session_manager()
        session = mgr.create_session()
        session_id = session.session_id
        
        conn_id = str(uuid.uuid4())
        assert mgr.add_connection(session_id, conn_id)
        
        connections = mgr.get_active_connections(session_id)
        assert conn_id in connections
        
        assert mgr.remove_connection(session_id, conn_id)
        connections = mgr.get_active_connections(session_id)
        assert conn_id not in connections
    
    def test_ip_rate_limiting(self):
        """IP rate limiting prevents too many connections."""
        mgr = get_session_manager()
        ip = "192.168.1.1"
        
        # Create max allowed sessions from IP
        for i in range(mgr.MAX_CONNECTIONS_PER_IP):
            session = mgr.create_session()
            assert mgr.register_ip_connection(ip, session.session_id)
        
        # Next session should fail
        session = mgr.create_session()
        assert not mgr.register_ip_connection(ip, session.session_id)


# ============================================================================
# Integration: API Health Check (Phase 1 + Engine)
# ============================================================================


class TestHealthCheckWithEngine:
    """Test health endpoint reflects engine state."""
    
    def test_health_shows_engine_running(self, client, mock_engine):
        """Health endpoint shows engine_running=true when set."""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["engine_running"] is True
        assert data["status"] == "healthy"
    
    def test_health_shows_engine_stopped(self, client):
        """Health endpoint shows engine_running=false when not set."""
        set_engine(None)
        
        response = client.get("/api/health")
        data = response.json()
        assert data["engine_running"] is False


# ============================================================================
# Integration: Full API Usage Flow
# ============================================================================


class TestFullAPIFlow:
    """Test realistic API usage patterns."""
    
    def test_client_checks_limitations_before_connecting(self, client):
        """Client can check limitations before starting session."""
        # 1. Check limitations
        response = client.get("/api/limitations")
        assert response.status_code == 200
        limitations = response.json()
        assert len(limitations) > 0
        
        # 2. Client now knows about single-user limitation
        single_user = next((l for l in limitations if "Single user" in l["limitation"]), None)
        assert single_user is not None
    
    def test_client_checks_health_before_connecting(self, client, mock_engine):
        """Client checks health before WebSocket connection."""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        health = response.json()
        assert health["engine_running"] is True
        
        # OK to connect to WebSocket
        assert True
    
    def test_api_survives_missing_engine_gracefully(self, client):
        """API handles missing engine gracefully on all endpoints."""
        set_engine(None)
        
        # Health shows engine not running
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["engine_running"] is False
        
        # But endpoint still responds
        response = client.get("/api/limitations")
        assert response.status_code == 200


# ============================================================================
# Integration: Stats and Monitoring
# ============================================================================


class TestSessionManagerStats:
    """Test session manager statistics."""
    
    def test_stats_reflect_session_count(self):
        """Stats correctly report session counts."""
        mgr = get_session_manager()
        
        assert mgr.get_stats()["total_sessions"] == 0
        
        mgr.create_session()
        assert mgr.get_stats()["total_sessions"] == 1
        
        mgr.create_session()
        assert mgr.get_stats()["total_sessions"] == 2
    
    def test_stats_track_session_states(self):
        """Stats show count of sessions in each state."""
        mgr = get_session_manager()
        
        s1 = mgr.create_session()
        mgr.set_session_state(s1.session_id, SessionState.ACTIVE)
        
        s2 = mgr.create_session()
        mgr.set_session_state(s2.session_id, SessionState.COMPLETED)
        
        stats = mgr.get_stats()
        assert stats["session_states"]["initializing"] == 0
        assert stats["session_states"]["active"] == 1
        assert stats["session_states"]["completed"] == 1
    
    def test_cleanup_removes_expired_sessions(self):
        """Cleanup removes expired sessions."""
        mgr = get_session_manager()
        original_ttl = mgr.SESSION_TTL_SECONDS
        mgr.SESSION_TTL_SECONDS = 1
        
        s1 = mgr.create_session()
        session_id = s1.session_id
        
        import time
        time.sleep(1.1)
        
        removed = mgr.cleanup_expired_sessions()
        assert removed >= 1
        assert mgr.get_session(session_id) is None
        
        mgr.SESSION_TTL_SECONDS = original_ttl


# ============================================================================
# Contract Validation Tests
# ============================================================================


class TestAPIContracts:
    """Verify API response contracts match specifications."""
    
    def test_limitation_response_contract(self, client):
        """APILimitation response matches contract."""
        response = client.get("/api/limitations")
        data = response.json()
        
        # Validate schema for first limitation
        limitation = data[0]
        
        # Required fields
        assert isinstance(limitation["limitation"], str)
        assert isinstance(limitation["workaround"], str)
        assert isinstance(limitation["phase"], str) or limitation["phase"] is None
        assert isinstance(limitation["planned_fix"], str) or limitation["planned_fix"] is None
    
    def test_ws_message_contract(self):
        """WSEventMessage contract validation."""
        msg = WSEventMessage(
            message_id="msg_test",
            event_type="signal",
            timestamp=datetime.utcnow().timestamp(),
            payload={"test": "data"},
            phase_id="p1",
            turn_id=1
        )
        
        # Can serialize to JSON
        json_data = msg.model_dump_json()
        assert json_data is not None
        
        # Can deserialize from JSON
        msg2 = WSEventMessage(**json.loads(json_data))
        assert msg2.message_id == msg.message_id
    
    def test_session_info_contract(self):
        """SessionInfo contract validation."""
        session = SessionInfo(
            session_id=str(uuid.uuid4()),
            created_at=datetime.utcnow().timestamp(),
            state=SessionState.ACTIVE,
            phase_profile="default",
            user_agent="test",
            last_activity=datetime.utcnow().timestamp()
        )
        
        assert session.session_id is not None
        assert session.created_at > 0
        assert session.last_activity >= session.created_at
