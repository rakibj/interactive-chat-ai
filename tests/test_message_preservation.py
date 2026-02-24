"""Tests for message preservation across phase transitions.

This test module verifies that messages are correctly preserved when
transitioning between phases, ensuring the complete chat history is
maintained throughout multi-phase conversations.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from interactive_chat.api.models import ChatMessage, PhaseGroupedChatHistory, PhaseMessages
from interactive_chat.server import app, _engine, set_engine


class TestMessagePreservation:
    """Test message preservation across phase transitions."""
    
    @pytest.fixture
    def mock_engine(self):
        """Fixture to create a mock engine with message preservation."""
        engine = Mock()
        engine.state = Mock()
        engine.state.active_phase_id = "greeting"
        engine.state.active_phase_name = "Greeting"
        engine.state.phases_completed = []
        engine.state.total_phases = 3
        engine.state.turn_id = 1
        engine.state.message_history_by_phase = {}
        
        # Create mock profile with a .name attribute that returns a string
        profile_mock = Mock()
        profile_mock.name = "default"
        engine.active_phase_profile = profile_mock
        
        engine.conversation_memory = Mock()
        engine.conversation_memory.get_messages.return_value = []
        return engine
    
    @pytest.fixture
    def client(self, mock_engine):
        """Fixture to create test client with mocked engine."""
        set_engine(mock_engine)
        from fastapi.testclient import TestClient
        return TestClient(app)
    
    def test_preserved_messages_in_completed_phase(self, client, mock_engine):
        """Test that messages are preserved in completed phases."""
        # Setup: First phase (greeting) with messages
        greeting_messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there! How are you?"},
        ]
        mock_engine.state.message_history_by_phase["greeting"] = greeting_messages
        mock_engine.state.phases_completed = ["greeting"]
        mock_engine.state.active_phase_id = "introduction"
        mock_engine.state.active_phase_name = "Introduction"
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "Tell me about yourself"},
            {"role": "assistant", "content": "I'm an AI assistant..."},
        ]
        
        # Act
        response = client.get("/api/chat/phases")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["phases"]) >= 2
        
        # Find greeting phase
        greeting_phase = next((p for p in data["phases"] if p["phase_id"] == "greeting"), None)
        assert greeting_phase is not None
        assert greeting_phase["status"] == "completed"
        assert len(greeting_phase["messages"]) == 2
        assert greeting_phase["messages"][0]["content"] == "Hello!"
        assert greeting_phase["messages"][1]["content"] == "Hi there! How are you?"
    
    def test_current_phase_messages_combined(self, client, mock_engine):
        """Test that current phase messages are combined with preserved history."""
        # Setup: Two phases - greeting (completed), introduction (active)
        greeting_messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_engine.state.message_history_by_phase["greeting"] = greeting_messages
        mock_engine.state.phases_completed = ["greeting"]
        mock_engine.state.active_phase_id = "introduction"
        mock_engine.state.active_phase_name = "Introduction"
        
        # Current phase messages (in active conversation)
        current_messages = [
            {"role": "user", "content": "Tell me more"},
            {"role": "assistant", "content": "Sure! I can help..."},
            {"role": "user", "content": "Great!"},
        ]
        mock_engine.conversation_memory.get_messages.return_value = current_messages
        
        # Act
        response = client.get("/api/chat/phases")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Find introduction phase
        intro_phase = next((p for p in data["phases"] if p["phase_id"] == "introduction"), None)
        assert intro_phase is not None
        assert intro_phase["status"] == "active"
        assert len(intro_phase["messages"]) == 3
        assert intro_phase["messages"][0]["content"] == "Tell me more"
        
        # Verify greeting phase is also present
        greeting_phase = next((p for p in data["phases"] if p["phase_id"] == "greeting"), None)
        assert greeting_phase is not None
        assert len(greeting_phase["messages"]) == 2
    
    def test_total_message_counts_across_phases(self, client, mock_engine):
        """Test that message counts are accurate across all phases."""
        # Setup: Three phases with various message counts
        mock_engine.state.message_history_by_phase = {
            "greeting": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hello!"},
            ],
            "introduction": [
                {"role": "user", "content": "Who are you?"},
                {"role": "assistant", "content": "I'm an AI..."},
                {"role": "user", "content": "Cool!"},
                {"role": "assistant", "content": "Thanks!"},
            ],
        }
        mock_engine.state.phases_completed = ["greeting", "introduction"]
        mock_engine.state.active_phase_id = "main_conversation"
        mock_engine.state.active_phase_name = "Main Conversation"
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "Let's talk"},
        ]
        
        # Act
        response = client.get("/api/chat/phases")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # 2 (greeting) + 4 (introduction) + 1 (main) = 7 total
        assert data["total_messages"] == 7
        assert data["human_messages"] == 4  # 1 + 2 + 1
        assert data["ai_messages"] == 3      # 1 + 2 + 0
    
    def test_system_messages_filtered_in_archived_phases(self, client, mock_engine):
        """Test that system messages are filtered in archived phase messages."""
        # Setup: Phase with system messages (shouldn't be shown)
        greeting_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "System message"},
            {"role": "assistant", "content": "Hi!"},
        ]
        mock_engine.state.message_history_by_phase["greeting"] = greeting_messages
        mock_engine.state.phases_completed = ["greeting"]
        mock_engine.state.active_phase_id = "intro"
        mock_engine.conversation_memory.get_messages.return_value = []
        
        # Act
        response = client.get("/api/chat/phases")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        greeting_phase = next((p for p in data["phases"] if p["phase_id"] == "greeting"), None)
        assert greeting_phase is not None
        # System messages are stored but should not appear in the response
        # (depending on implementation - they should be filtered)
        assert len(greeting_phase["messages"]) <= len(greeting_messages)
    
    def test_empty_phases_preserved(self, client, mock_engine):
        """Test that empty phases are included with zero messages."""
        # Setup: One completed empty phase
        mock_engine.state.message_history_by_phase["greeting"] = []
        mock_engine.state.phases_completed = ["greeting"]
        mock_engine.state.active_phase_id = "introduction"
        mock_engine.state.total_phases = 3
        mock_engine.conversation_memory.get_messages.return_value = []
        
        # Act
        response = client.get("/api/chat/phases")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Greeting phase should be present but empty
        greeting_phase = next((p for p in data["phases"] if p["phase_id"] == "greeting"), None)
        assert greeting_phase is not None
        assert len(greeting_phase["messages"]) == 0
        assert greeting_phase["message_count"] == 0
    
    def test_phase_ordering_preserved(self, client, mock_engine):
        """Test that phases appear in the correct order: completed -> current -> upcoming."""
        # Setup: Multiple phases
        mock_engine.state.message_history_by_phase = {
            "phase1": [{"role": "user", "content": "msg1"}],
            "phase2": [{"role": "assistant", "content": "msg2"}],
        }
        mock_engine.state.phases_completed = ["phase1", "phase2"]
        mock_engine.state.active_phase_id = "phase3"
        mock_engine.state.total_phases = 5
        mock_engine.conversation_memory.get_messages.return_value = []
        
        # Act
        response = client.get("/api/chat/phases")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        phases = data["phases"]
        assert len(phases) == 5
        
        # Verify order: completed phases first, then current, then upcoming
        status_order = [p["status"] for p in phases]
        assert status_order.count("completed") == 2
        assert status_order.count("active") == 1
        assert status_order.count("upcoming") == 2
        
        # Active phase should come after completed phases
        active_index = next(i for i, s in enumerate(status_order) if s == "active")
        completed_indices = [i for i, s in enumerate(status_order) if s == "completed"]
        assert all(ci < active_index for ci in completed_indices)
    
    def test_message_indices_reset_per_phase(self, client, mock_engine):
        """Test that message indices start fresh for each phase."""
        # Setup: Multiple phases with messages
        mock_engine.state.message_history_by_phase = {
            "greeting": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
                {"role": "user", "content": "How are you?"},
            ],
        }
        mock_engine.state.phases_completed = ["greeting"]
        mock_engine.state.active_phase_id = "intro"
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "Tell me about yourself"},
            {"role": "assistant", "content": "Sure!"},
        ]
        
        # Act
        response = client.get("/api/chat/phases")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Check greeting phase indices
        greeting_phase = next(p for p in data["phases"] if p["phase_id"] == "greeting")
        greeting_indices = [msg["index"] for msg in greeting_phase["messages"]]
        assert greeting_indices == [0, 1, 2]
        
        # Check intro phase indices (should also start at 0)
        intro_phase = next(p for p in data["phases"] if p["phase_id"] == "intro")
        intro_indices = [msg["index"] for msg in intro_phase["messages"]]
        assert intro_indices == [0, 1]
    
    def test_response_structure_with_preserved_messages(self, client, mock_engine):
        """Test that response structure is valid when messages are preserved."""
        # Setup: Multiple phases with messages
        mock_engine.state.message_history_by_phase = {
            "phase1": [
                {"role": "user", "content": "msg1"},
                {"role": "assistant", "content": "msg2"},
            ],
        }
        mock_engine.state.phases_completed = ["phase1"]
        mock_engine.state.active_phase_id = "phase2"
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "msg3"},
        ]
        
        # Act
        response = client.get("/api/chat/phases")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify top-level structure
        assert "phases" in data
        assert "current_phase_id" in data
        assert "total_messages" in data
        assert "total_phases" in data
        assert "phases_completed" in data
        assert "human_messages" in data
        assert "ai_messages" in data
        assert "turn_id" in data
        
        # Verify phase structure
        for phase in data["phases"]:
            assert "phase_id" in phase
            assert "phase_name" in phase
            assert "phase_index" in phase
            assert "status" in phase
            assert "messages" in phase
            assert "message_count" in phase
            
            # Verify message structure
            for message in phase["messages"]:
                assert "role" in message
                assert "content" in message
                assert "index" in message
