"""Tests for phase-grouped chat history endpoint."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import json

from interactive_chat.server import app, _engine, set_engine
from interactive_chat.core.event_driven_core import SystemState
from interactive_chat.api.models import PhaseMessages, PhaseGroupedChatHistory
from interactive_chat.config import PHASE_PROFILES


class TestPhaseGroupedChatHistory:
    """Tests for /api/chat/phases endpoint."""
    
    def test_phase_endpoint_no_engine(self):
        """Test that endpoint returns 503 when engine not initialized."""
        client = TestClient(app)
        set_engine(None)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 503
    
    def test_phase_endpoint_empty_conversation(self):
        """Test endpoint with no messages."""
        client = TestClient(app)
        
        # Mock engine
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "greeting"
        mock_engine.state.turn_id = 0
        mock_engine.state.total_phases = 1
        mock_engine.state.phases_completed = []
        mock_engine.conversation_memory.get_messages.return_value = []
        mock_engine.active_phase_profile = None
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_messages"] == 0
        assert data["current_phase_id"] == "greeting"
        assert data["human_messages"] == 0
        assert data["ai_messages"] == 0
        assert len(data["phases"]) >= 1
    
    def test_phase_endpoint_single_phase_with_messages(self):
        """Test endpoint with messages in single phase."""
        client = TestClient(app)
        
        # Mock engine with messages
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "greeting"
        mock_engine.state.turn_id = 1
        mock_engine.state.total_phases = 1
        mock_engine.state.phases_completed = []
        
        messages_raw = [
            {"role": "system", "content": "System message"},
            {"role": "assistant", "content": "Hello there!"},
            {"role": "user", "content": "Hi back!"},
        ]
        mock_engine.conversation_memory.get_messages.return_value = messages_raw
        mock_engine.active_phase_profile = None
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_messages"] == 2  # System message filtered out
        assert data["human_messages"] == 1
        assert data["ai_messages"] == 1
        assert data["current_phase_id"] == "greeting"
        
        # Check phases array
        assert len(data["phases"]) >= 1
        current_phase = next((p for p in data["phases"] if p["phase_id"] == "greeting"), None)
        assert current_phase is not None
        assert current_phase["status"] == "active"
        assert current_phase["message_count"] == 2
        assert len(current_phase["messages"]) == 2
    
    def test_phase_endpoint_multi_phase_tracking(self):
        """Test endpoint with multiple phases completed."""
        client = TestClient(app)
        
        # Mock engine with completed phases
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "introduction"
        mock_engine.state.turn_id = 5
        mock_engine.state.total_phases = 4
        mock_engine.state.phase_index = 1
        mock_engine.state.phases_completed = ["greeting"]
        
        messages_raw = [
            {"role": "assistant", "content": "What is your issue?"},
            {"role": "user", "content": "I have a problem with login."},
        ]
        mock_engine.conversation_memory.get_messages.return_value = messages_raw
        mock_engine.active_phase_profile = Mock()
        mock_engine.active_phase_profile.name = "technical_support"
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_phases"] == 4
        assert data["phases_completed"] == ["greeting"]
        assert data["current_phase_id"] == "introduction"
        assert data["phase_profile"] == "technical_support"
        
        # Check phase statuses
        greeting_phase = next((p for p in data["phases"] if p["phase_id"] == "greeting"), None)
        intro_phase = next((p for p in data["phases"] if p["phase_id"] == "introduction"), None)
        
        assert greeting_phase is not None
        assert greeting_phase["status"] == "completed"
        
        assert intro_phase is not None
        assert intro_phase["status"] == "active"
    
    def test_phase_endpoint_respects_profile_order(self):
        """Test that phases are returned in PROFILE ORDER, not completion order.
        
        This is the critical fix: /api/chat/phases endpoint should iterate through
        phase_profile.phases.keys() (profile definition order) rather than completion order.
        
        Scenario: User completes Part 1, Part 2 in that order. Phases should be returned
        as: Greeting (completed), Part1 (completed), Part2 (active), Part3 (upcoming), Closing (upcoming)
        NOT as: Greeting (completed), Part1 (completed), Part2 (active), Closing, Part3
        """
        client = TestClient(app)
        
        # Create a mock profile with defined phase order
        mock_profile = Mock()
        mock_profile.name = "test_profile"
        # Profile defines phases in this order: phase_a, phase_b, phase_c, phase_d
        mock_profile.phases = {
            "phase_a": Mock(),
            "phase_b": Mock(),
            "phase_c": Mock(),
            "phase_d": Mock(),
        }
        
        # Simulate user completing phases: phase_a, then phase_b (not in alphabetical order)
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "phase_c"
        mock_engine.state.turn_id = 3
        mock_engine.state.total_phases = 4
        mock_engine.state.phases_completed = ["phase_a", "phase_b"]
        mock_engine.conversation_memory.get_messages.return_value = []
        mock_engine.active_phase_profile = mock_profile
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        data = response.json()
        phases = data["phases"]
        
        # CRITICAL: Phases must be in profile definition order
        phase_ids = [p["phase_id"] for p in phases]
        expected_order = ["phase_a", "phase_b", "phase_c", "phase_d"]
        assert phase_ids == expected_order, f"Phases returned as {phase_ids}, expected {expected_order}"
        
        # Verify correct status assignments based on completion state
        assert phases[0]["phase_id"] == "phase_a"
        assert phases[0]["status"] == "completed"
        assert phases[0]["phase_index"] == 0
        
        assert phases[1]["phase_id"] == "phase_b"
        assert phases[1]["status"] == "completed"
        assert phases[1]["phase_index"] == 1
        
        assert phases[2]["phase_id"] == "phase_c"
        assert phases[2]["status"] == "active"
        assert phases[2]["phase_index"] == 2
        
        assert phases[3]["phase_id"] == "phase_d"
        assert phases[3]["status"] == "upcoming"
        assert phases[3]["phase_index"] == 3
    
    def test_phase_endpoint_with_ielts_profile(self):
        """Test with actual IELTS profile to validate phase ordering fix.
        
        Validates that IELTS phases are returned in correct order:
        greeting → part1 → part2 → part3 → closing
        """
        if "ielts" not in PHASE_PROFILES:
            pytest.skip("IELTS profile not available")
        
        client = TestClient(app)
        ielts_profile = PHASE_PROFILES["ielts"]
        
        # Mock engine with some completed phases
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "part2"
        mock_engine.state.turn_id = 10
        mock_engine.state.phases_completed = ["greeting", "part1"]
        mock_engine.conversation_memory.get_messages.return_value = []
        mock_engine.active_phase_profile = ielts_profile
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        data = response.json()
        phases = data["phases"]
        
        # Validate IELTS phase order
        phase_ids = [p["phase_id"] for p in phases]
        expected_ielts_order = ["greeting", "part1", "part2", "part3", "closing"]
        assert phase_ids == expected_ielts_order, f"IELTS phases in wrong order: {phase_ids}"
        
        # Validate status assignments
        assert phases[0]["status"] == "completed"  # greeting
        assert phases[1]["status"] == "completed"  # part1
        assert phases[2]["status"] == "active"      # part2
        assert phases[3]["status"] == "upcoming"    # part3
        assert phases[4]["status"] == "upcoming"    # closing
    
    def test_phase_endpoint_with_name_age_test_profile(self):
        """Test with simple name_age_test profile for validation of 2-phase flow.
        
        The name_age_test profile is a minimal test case with 2 phases:
        ask_name → ask_age
        """
        if "name_age_test" not in PHASE_PROFILES:
            pytest.skip("name_age_test profile not available")
        
        client = TestClient(app)
        test_profile = PHASE_PROFILES["name_age_test"]
        
        # Mock engine at ask_name phase
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "ask_name"
        mock_engine.state.turn_id = 1
        mock_engine.state.phases_completed = []
        
        messages = [
            {"role": "assistant", "content": "What is your name?"},
            {"role": "user", "content": "John"},
        ]
        mock_engine.conversation_memory.get_messages.return_value = messages
        mock_engine.active_phase_profile = test_profile
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        data = response.json()
        phases = data["phases"]
        
        # Validate 2-phase order
        phase_ids = [p["phase_id"] for p in phases]
        assert phase_ids == ["ask_name", "ask_age"], f"Test profile phases in wrong order: {phase_ids}"
        
        # Validate status and messages
        assert phases[0]["status"] == "active"
        assert phases[0]["message_count"] == 2
        assert phases[1]["status"] == "upcoming"
        assert phases[1]["message_count"] == 0
    
    def test_phase_endpoint_message_content_preserved(self):
        """Test that message content is correctly preserved."""
        client = TestClient(app)
        
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "test_phase"
        mock_engine.state.turn_id = 1
        mock_engine.state.total_phases = 1
        mock_engine.state.phases_completed = []
        
        test_content = "This is a test message with special chars: !@#$%"
        messages_raw = [
            {"role": "user", "content": test_content},
        ]
        mock_engine.conversation_memory.get_messages.return_value = messages_raw
        mock_engine.active_phase_profile = None
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["phases"]) > 0
        phase = data["phases"][0]
        assert len(phase["messages"]) > 0
        assert phase["messages"][0]["content"] == test_content
    
    def test_phase_endpoint_response_model_validation(self):
        """Test that response matches PhaseGroupedChatHistory model."""
        client = TestClient(app)
        
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "greeting"
        mock_engine.state.turn_id = 0
        mock_engine.state.total_phases = 2
        mock_engine.state.phases_completed = []
        
        mock_engine.conversation_memory.get_messages.return_value = []
        mock_engine.active_phase_profile = None
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        data = response.json()
        
        # Validate structure
        assert "phases" in data
        assert "current_phase_id" in data
        assert "total_messages" in data
        assert "total_phases" in data
        assert "phases_completed" in data
        assert "human_messages" in data
        assert "ai_messages" in data
        assert "turn_id" in data
        assert "phase_profile" in data
        
        # Validate phases array structure
        for phase in data["phases"]:
            assert "phase_id" in phase
            assert "phase_name" in phase
            assert "phase_index" in phase
            assert "status" in phase
            assert phase["status"] in ["completed", "active", "upcoming"]
            assert "messages" in phase
            assert "message_count" in phase
            assert "duration_sec" in phase
            
            # Validate messages structure
            for msg in phase["messages"]:
                assert "role" in msg
                assert msg["role"] in ["user", "assistant"]
                assert "content" in msg
                assert "index" in msg
    
    def test_phase_endpoint_handles_special_characters(self):
        """Test that special characters in messages are handled correctly."""
        client = TestClient(app)
        
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "test"
        mock_engine.state.turn_id = 1
        mock_engine.state.total_phases = 1
        mock_engine.state.phases_completed = []
        
        special_messages = [
            {"role": "user", "content": 'Message with "quotes"'},
            {"role": "assistant", "content": "Message with\nnewline"},
            {"role": "user", "content": "Message with emoji: 😀"},
            {"role": "assistant", "content": "Message with <html> tags"},
        ]
        mock_engine.conversation_memory.get_messages.return_value = special_messages
        mock_engine.active_phase_profile = None
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        data = response.json()
        messages = data["phases"][0]["messages"] if data["phases"] else []
        
        assert len(messages) == 4
        assert messages[0]["content"] == 'Message with "quotes"'
        assert messages[1]["content"] == "Message with\nnewline"
        assert messages[2]["content"] == "Message with emoji: 😀"
        assert messages[3]["content"] == "Message with <html> tags"
    
    def test_phase_endpoint_json_serializable(self):
        """Test that response is JSON serializable."""
        client = TestClient(app)
        
        mock_engine = Mock()
        mock_engine.state = SystemState()
        mock_engine.state.active_phase_id = "greeting"
        mock_engine.state.turn_id = 0
        mock_engine.state.total_phases = 1
        mock_engine.state.phases_completed = []
        
        messages_raw = [
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "Hi!"},
        ]
        mock_engine.conversation_memory.get_messages.return_value = messages_raw
        mock_engine.active_phase_profile = None
        
        set_engine(mock_engine)
        
        response = client.get("/api/chat/phases")
        assert response.status_code == 200
        
        # Should be JSON serializable
        json_str = response.text
        data = json.loads(json_str)
        
        # Re-serialize should work
        re_serialized = json.dumps(data)
        assert isinstance(re_serialized, str)
        assert len(re_serialized) > 0


class TestPhaseMessageModel:
    """Tests for PhaseMessages Pydantic model."""
    
    def test_phase_messages_creation(self):
        """Test creating PhaseMessages model."""
        from interactive_chat.api.models import ChatMessage
        
        msg = ChatMessage(
            role="user",
            content="Test",
            index=0,
            timestamp=datetime.now().timestamp()
        )
        
        phase = PhaseMessages(
            phase_id="test",
            phase_name="Test Phase",
            phase_index=0,
            status="active",
            messages=[msg],
            message_count=1,
            duration_sec=10.5
        )
        
        assert phase.phase_id == "test"
        assert phase.message_count == 1
        assert phase.status == "active"
    
    def test_phase_messages_json_schema(self):
        """Test PhaseMessages JSON schema."""
        schema = PhaseMessages.model_json_schema()
        
        assert "properties" in schema
        assert "phase_id" in schema["properties"]
        assert "messages" in schema["properties"]
        assert "status" in schema["properties"]


class TestPhaseGroupedChatHistoryModel:
    """Tests for PhaseGroupedChatHistory Pydantic model."""
    
    def test_grouped_history_creation(self):
        """Test creating PhaseGroupedChatHistory model."""
        from interactive_chat.api.models import ChatMessage
        
        phase = PhaseMessages(
            phase_id="greeting",
            phase_name="Greeting",
            phase_index=0,
            status="completed",
            messages=[],
            message_count=0
        )
        
        history = PhaseGroupedChatHistory(
            phases=[phase],
            current_phase_id="greeting",
            total_messages=0,
            total_phases=1,
            phases_completed=["greeting"],
            human_messages=0,
            ai_messages=0,
            turn_id=0
        )
        
        assert len(history.phases) == 1
        assert history.total_phases == 1
        assert history.current_phase_id == "greeting"
    
    def test_grouped_history_json_schema(self):
        """Test PhaseGroupedChatHistory JSON schema."""
        schema = PhaseGroupedChatHistory.model_json_schema()
        
        assert "properties" in schema
        assert "phases" in schema["properties"]
        assert "current_phase_id" in schema["properties"]
        assert "total_phases" in schema["properties"]
