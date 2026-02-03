"""Tests for Phase 4: Interactive Gradio Controls.

Tests new control endpoints and models:
- POST /api/conversation/text-input
- POST /api/engine/command (start/stop/pause/resume)
- POST /api/conversation/reset
"""

import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from interactive_chat.api.models import (
    TextInput,
    EngineCommandRequest,
    EngineCommandResponse,
    ConversationReset,
    ResetResponse,
)

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client(mock_engine):
    """FastAPI test client with mocked engine."""
    from interactive_chat.server import app, set_engine
    
    set_engine(mock_engine)
    return TestClient(app)


@pytest.fixture
def mock_engine():
    """Mock ConversationEngine."""
    engine = Mock()
    engine.event_queue = []
    engine.is_paused = False
    engine.conversation_history = []
    engine.active_phase_profile = 0
    
    def get_state():
        return {
            "phase": {"phase_index": 0},
            "speaker": "AI",
            "history": [],
            "turn_id": 1,
            "is_processing": False
        }
    
    engine.get_state = get_state
    engine.process_turn = Mock()
    
    return engine


class TestTextInputModel:
    """Tests for TextInput Pydantic model."""
    
    def test_text_input_valid(self):
        """Valid text input."""
        data = {"text": "Hello, how are you?"}
        model = TextInput(**data)
        assert model.text == "Hello, how are you?"
    
    def test_text_input_empty_rejected(self):
        """Empty text rejected."""
        with pytest.raises(ValueError):
            TextInput(text="")
    
    def test_text_input_whitespace_only_rejected(self):
        """Whitespace-only text rejected."""
        with pytest.raises(ValueError):
            TextInput(text="   ")
    
    def test_text_input_max_length(self):
        """Text longer than 1000 chars rejected."""
        long_text = "x" * 1001
        with pytest.raises(ValueError):
            TextInput(text=long_text)
    
    def test_text_input_max_length_boundary(self):
        """Text exactly 1000 chars accepted."""
        text = "x" * 1000
        model = TextInput(text=text)
        assert len(model.text) == 1000


class TestEngineCommandRequest:
    """Tests for EngineCommandRequest model."""
    
    def test_command_valid_start(self):
        """Valid 'start' command."""
        cmd = EngineCommandRequest(command="start")
        assert cmd.command == "start"
    
    def test_command_valid_stop(self):
        """Valid 'stop' command."""
        cmd = EngineCommandRequest(command="stop")
        assert cmd.command == "stop"
    
    def test_command_valid_pause(self):
        """Valid 'pause' command."""
        cmd = EngineCommandRequest(command="pause")
        assert cmd.command == "pause"
    
    def test_command_valid_resume(self):
        """Valid 'resume' command."""
        cmd = EngineCommandRequest(command="resume")
        assert cmd.command == "resume"
    
    def test_command_missing_rejected(self):
        """Missing command field rejected."""
        with pytest.raises(ValueError):
            EngineCommandRequest()


class TestEngineCommandResponse:
    """Tests for EngineCommandResponse model."""
    
    def test_response_valid(self):
        """Valid response."""
        data = {
            "status": "paused",
            "message": "Engine paused",
            "timestamp": "2026-02-04T12:34:56.789Z"
        }
        response = EngineCommandResponse(**data)
        assert response.status == "paused"
        assert response.message == "Engine paused"
    
    def test_response_timestamp_optional(self):
        """Timestamp is optional."""
        data = {
            "status": "started",
            "message": "Engine started"
        }
        response = EngineCommandResponse(**data)
        assert response.timestamp is None


class TestConversationReset:
    """Tests for ConversationReset model."""
    
    def test_reset_keep_profile_true(self):
        """Keep profile flag defaults to True."""
        reset = ConversationReset(keep_profile=True)
        assert reset.keep_profile is True
    
    def test_reset_keep_profile_false(self):
        """Keep profile flag can be False."""
        reset = ConversationReset(keep_profile=False)
        assert reset.keep_profile is False
    
    def test_reset_defaults(self):
        """Keep profile defaults to True when not specified."""
        reset = ConversationReset()
        assert reset.keep_profile is True


class TestResetResponse:
    """Tests for ResetResponse model."""
    
    def test_response_valid(self):
        """Valid reset response."""
        data = {
            "status": "reset",
            "message": "Conversation reset successfully",
            "conversation_memory_cleared": True,
            "phase_reset": False,
            "timestamp": "2026-02-04T12:34:56.789Z"
        }
        response = ResetResponse(**data)
        assert response.status == "reset"
        assert response.conversation_memory_cleared is True
        assert response.phase_reset is False


class TestTextInputEndpoint:
    """Tests for POST /api/conversation/text-input."""
    
    def test_text_input_success(self, client, mock_engine):
        """Send text input successfully."""
        response = client.post(
            "/api/conversation/text-input",
            json={"text": "Hello world"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert "text input" in data["message"].lower()
    
    def test_text_input_empty_rejected(self, client, mock_engine):
        """Empty text rejected."""
        response = client.post(
            "/api/conversation/text-input",
            json={"text": ""}
        )
        assert response.status_code == 422
    
    def test_text_input_engine_not_initialized(self, client, mock_engine):
        """Error when engine not initialized."""
        # Unset engine
        from interactive_chat.server import set_engine
        set_engine(None)
        
        response = client.post(
            "/api/conversation/text-input",
            json={"text": "Hello"}
        )
        assert response.status_code == 503
        assert "Engine not initialized" in response.json()["detail"]
        
        # Reset for other tests
        set_engine(mock_engine)
    
    def test_text_input_injects_event(self, client, mock_engine):
        """Text input creates ASR_FINAL_TRANSCRIPT event."""
        response = client.post(
            "/api/conversation/text-input",
            json={"text": "Test message"}
        )
        assert response.status_code == 200
        # Verify process_turn was called
        assert mock_engine.process_turn.called


class TestEngineCommandEndpoint:
    """Tests for POST /api/engine/command."""
    
    def test_command_start(self, client, mock_engine):
        """Send 'start' command."""
        response = client.post(
            "/api/engine/command",
            json={"command": "start"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert mock_engine.is_paused is False
    
    def test_command_stop(self, client, mock_engine):
        """Send 'stop' command."""
        response = client.post(
            "/api/engine/command",
            json={"command": "stop"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert mock_engine.is_paused is True
        assert len(mock_engine.conversation_history) == 0
    
    def test_command_pause(self, client, mock_engine):
        """Send 'pause' command."""
        response = client.post(
            "/api/engine/command",
            json={"command": "pause"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        assert mock_engine.is_paused is True
    
    def test_command_resume(self, client, mock_engine):
        """Send 'resume' command."""
        mock_engine.is_paused = True
        response = client.post(
            "/api/engine/command",
            json={"command": "resume"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resumed"
        assert mock_engine.is_paused is False
    
    def test_command_case_insensitive(self, client, mock_engine):
        """Commands are case-insensitive."""
        response = client.post(
            "/api/engine/command",
            json={"command": "START"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "started"
    
    def test_command_invalid(self, client, mock_engine):
        """Invalid command rejected."""
        response = client.post(
            "/api/engine/command",
            json={"command": "invalid"}
        )
        assert response.status_code == 400
        assert "Unknown command" in response.json()["detail"]
    
    def test_command_engine_not_initialized(self, client, mock_engine):
        """Error when engine not initialized."""
        from interactive_chat.server import set_engine
        set_engine(None)
        
        response = client.post(
            "/api/engine/command",
            json={"command": "start"}
        )
        assert response.status_code == 503
        
        # Reset for other tests
        set_engine(mock_engine)
    
    def test_command_response_has_timestamp(self, client, mock_engine):
        """Response includes ISO timestamp."""
        response = client.post(
            "/api/engine/command",
            json={"command": "pause"}
        )
        data = response.json()
        assert "timestamp" in data
        # Verify it's a valid ISO format
        datetime.fromisoformat(data["timestamp"])


class TestConversationResetEndpoint:
    """Tests for POST /api/conversation/reset."""
    
    def test_reset_keep_profile(self, client, mock_engine):
        """Reset with keep_profile=True."""
        mock_engine.conversation_history = [{"text": "test"}]
        response = client.post(
            "/api/conversation/reset",
            json={"keep_profile": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reset"
        assert data["conversation_memory_cleared"] is True
        assert data["phase_reset"] is False
        # Verify memory cleared
        assert len(mock_engine.conversation_history) == 0
    
    def test_reset_new_profile(self, client, mock_engine):
        """Reset with keep_profile=False."""
        mock_engine.active_phase_profile = 2
        mock_engine.conversation_history = [{"text": "test"}]
        response = client.post(
            "/api/conversation/reset",
            json={"keep_profile": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phase_reset"] is True
        # Verify profile reset
        assert mock_engine.active_phase_profile == 0
    
    def test_reset_defaults_to_keep_profile(self, client, mock_engine):
        """Reset defaults to keep_profile=True."""
        response = client.post(
            "/api/conversation/reset",
            json={}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phase_reset"] is False
    
    def test_reset_clears_pause_state(self, client, mock_engine):
        """Reset clears pause state."""
        mock_engine.is_paused = True
        response = client.post(
            "/api/conversation/reset",
            json={"keep_profile": True}
        )
        assert response.status_code == 200
        assert mock_engine.is_paused is False
    
    def test_reset_engine_not_initialized(self, client, mock_engine):
        """Error when engine not initialized."""
        from interactive_chat.server import set_engine
        set_engine(None)
        
        response = client.post(
            "/api/conversation/reset",
            json={"keep_profile": True}
        )
        assert response.status_code == 503
        
        # Reset for other tests
        set_engine(mock_engine)
    
    def test_reset_response_has_timestamp(self, client, mock_engine):
        """Response includes ISO timestamp."""
        response = client.post(
            "/api/conversation/reset",
            json={"keep_profile": True}
        )
        data = response.json()
        assert "timestamp" in data
        # Verify it's a valid ISO format
        datetime.fromisoformat(data["timestamp"])


class TestPhase4Integration:
    """Integration tests for Phase 4 control flow."""
    
    def test_control_flow_start_input_pause(self, client, mock_engine):
        """Control flow: Start → Input → Pause."""
        # Start
        response = client.post(
            "/api/engine/command",
            json={"command": "start"}
        )
        assert response.status_code == 200
        assert mock_engine.is_paused is False
        
        # Send text
        response = client.post(
            "/api/conversation/text-input",
            json={"text": "Test"}
        )
        assert response.status_code == 200
        
        # Pause
        response = client.post(
            "/api/engine/command",
            json={"command": "pause"}
        )
        assert response.status_code == 200
        assert mock_engine.is_paused is True
    
    def test_control_flow_reset_then_input(self, client, mock_engine):
        """Control flow: Reset → Input."""
        mock_engine.conversation_history = [{"text": "old"}]
        
        # Reset
        response = client.post(
            "/api/conversation/reset",
            json={"keep_profile": True}
        )
        assert response.status_code == 200
        assert len(mock_engine.conversation_history) == 0
        
        # Send text
        response = client.post(
            "/api/conversation/text-input",
            json={"text": "New"}
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
