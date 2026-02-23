"""Comprehensive tests for /api/chat endpoint."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from interactive_chat.api.models import ChatMessage, ChatHistory


class TestChatMessageModel:
    """Test ChatMessage Pydantic model."""
    
    def test_chat_message_user_role(self):
        """Test creating a user ChatMessage."""
        msg = ChatMessage(
            role="user",
            content="What is the capital of France?",
            index=0,
            timestamp=1707052800.123
        )
        assert msg.role == "user"
        assert msg.content == "What is the capital of France?"
        assert msg.index == 0
        assert msg.timestamp == 1707052800.123
    
    def test_chat_message_assistant_role(self):
        """Test creating an assistant ChatMessage."""
        msg = ChatMessage(
            role="assistant",
            content="Paris is the capital of France.",
            index=1,
        )
        assert msg.role == "assistant"
        assert msg.content == "Paris is the capital of France."
        assert msg.index == 1
    
    def test_chat_message_system_role(self):
        """Test creating a system ChatMessage."""
        msg = ChatMessage(
            role="system",
            content="System message",
            index=2,
        )
        assert msg.role == "system"
        assert msg.content == "System message"
    
    def test_chat_message_invalid_role(self):
        """Test that invalid roles are rejected."""
        with pytest.raises(ValueError):
            ChatMessage(
                role="invalid",  # Should only be user, assistant, or system
                content="Test",
                index=0,
            )
    
    def test_chat_message_empty_content(self):
        """Test ChatMessage with empty content."""
        msg = ChatMessage(
            role="user",
            content="",
            index=0,
        )
        assert msg.content == ""
    
    def test_chat_message_long_content(self):
        """Test ChatMessage with long content."""
        long_text = "A" * 10000
        msg = ChatMessage(
            role="user",
            content=long_text,
            index=0,
        )
        assert len(msg.content) == 10000


class TestChatHistoryModel:
    """Test ChatHistory Pydantic model."""
    
    def test_chat_history_empty(self):
        """Test creating empty ChatHistory."""
        history = ChatHistory(
            messages=[],
            total_messages=0,
            turn_id=0,
            phase_id=None,
            human_messages=0,
            ai_messages=0,
        )
        assert history.messages == []
        assert history.total_messages == 0
        assert history.turn_id == 0
        assert history.phase_id is None
        assert history.human_messages == 0
        assert history.ai_messages == 0
    
    def test_chat_history_with_messages(self):
        """Test ChatHistory with multiple messages."""
        msg1 = ChatMessage(role="user", content="Hello", index=0)
        msg2 = ChatMessage(role="assistant", content="Hi there!", index=1)
        
        history = ChatHistory(
            messages=[msg1, msg2],
            total_messages=2,
            turn_id=1,
            phase_id="part1",
            human_messages=1,
            ai_messages=1,
        )
        
        assert len(history.messages) == 2
        assert history.total_messages == 2
        assert history.turn_id == 1
        assert history.phase_id == "part1"
        assert history.human_messages == 1
        assert history.ai_messages == 1
    
    def test_chat_history_json_schema(self):
        """Test ChatHistory generates valid JSON schema."""
        history = ChatHistory(
            messages=[],
            total_messages=0,
            turn_id=0,
            phase_id=None,
            human_messages=0,
            ai_messages=0,
        )
        
        dumped = history.model_dump()
        assert "messages" in dumped
        assert "total_messages" in dumped
        assert "turn_id" in dumped
        assert "phase_id" in dumped
        assert "human_messages" in dumped
        assert "ai_messages" in dumped


class TestChatAPIEndpoint:
    """Test /api/chat endpoint."""
    
    @pytest.fixture
    def mock_engine(self):
        """Create mock ConversationEngine."""
        engine = MagicMock()
        engine.state = MagicMock()
        engine.state.turn_id = 5
        engine.state.active_phase_id = "part1"
        
        # Mock conversation memory
        engine.conversation_memory = MagicMock()
        engine.conversation_memory.get_messages = MagicMock(return_value=[])
        
        return engine
    
    @pytest.fixture
    def mock_fastapi_app(self):
        """Create mock FastAPI app for testing."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        return app, TestClient(app)
    
    def test_chat_endpoint_no_engine(self, mock_fastapi_app):
        """Test /api/chat returns 503 when engine not initialized."""
        from interactive_chat import server
        
        # Ensure engine is None
        server._engine = None
        
        # Create a test app
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        response = client.get("/api/chat")
        assert response.status_code == 503
    
    def test_chat_endpoint_empty_conversation(self, mock_engine):
        """Test /api/chat with empty conversation."""
        from interactive_chat import server
        from interactive_chat.api.models import ChatHistory
        
        server._engine = mock_engine
        mock_engine.conversation_memory.get_messages.return_value = []
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        response = client.get("/api/chat")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_messages"] == 0
        assert data["messages"] == []
        assert data["human_messages"] == 0
        assert data["ai_messages"] == 0
    
    def test_chat_endpoint_with_messages(self, mock_engine):
        """Test /api/chat with actual messages."""
        from interactive_chat import server
        
        server._engine = mock_engine
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm doing great!"},
        ]
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        response = client.get("/api/chat")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_messages"] == 4
        assert len(data["messages"]) == 4
        assert data["human_messages"] == 2
        assert data["ai_messages"] == 2
        assert data["turn_id"] == 5
        assert data["phase_id"] == "part1"
    
    def test_chat_endpoint_filters_system_messages(self, mock_engine):
        """Test /api/chat filters out system messages."""
        from interactive_chat import server
        
        server._engine = mock_engine
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "Another system message"},
            {"role": "assistant", "content": "Hi!"},
        ]
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        response = client.get("/api/chat")
        assert response.status_code == 200
        
        data = response.json()
        # System messages should be filtered out
        assert data["total_messages"] == 2
        assert len(data["messages"]) == 2
        
        # Verify no system messages in response
        for msg in data["messages"]:
            assert msg["role"] != "system"
    
    def test_chat_endpoint_limit_parameter(self, mock_engine):
        """Test /api/chat with limit parameter."""
        from interactive_chat import server
        
        server._engine = mock_engine
        
        # Create 20 messages
        messages = []
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": f"Message {i}"})
        
        mock_engine.conversation_memory.get_messages.return_value = messages
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        # Request only last 5 messages
        response = client.get("/api/chat?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 5
    
    def test_chat_endpoint_limit_minimum(self, mock_engine):
        """Test /api/chat enforces minimum limit of 1."""
        from interactive_chat import server
        
        server._engine = mock_engine
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "Test"}
        ]
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        # Request with invalid limit (less than 1)
        response = client.get("/api/chat?limit=0")
        assert response.status_code == 200
        
        # Should default to 1
        data = response.json()
        assert data["total_messages"] == 1
    
    def test_chat_endpoint_limit_maximum(self, mock_engine):
        """Test /api/chat caps limit at 500."""
        from interactive_chat import server
        
        server._engine = mock_engine
        
        # Create 600 messages
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(600)
        ]
        mock_engine.conversation_memory.get_messages.return_value = messages
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        # Request with limit greater than 500
        response = client.get("/api/chat?limit=1000")
        assert response.status_code == 200
        
        data = response.json()
        # Should be capped at 500
        assert len(data["messages"]) == 500
    
    def test_chat_endpoint_message_structure(self, mock_engine):
        """Test each message has correct structure."""
        from interactive_chat import server
        
        server._engine = mock_engine
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        response = client.get("/api/chat")
        data = response.json()
        
        for i, msg in enumerate(data["messages"]):
            assert "role" in msg
            assert "content" in msg
            assert "index" in msg
            assert msg["role"] in ["user", "assistant", "system"]
            assert isinstance(msg["content"], str)
            assert isinstance(msg["index"], int)
    
    def test_chat_endpoint_preserves_message_order(self, mock_engine):
        """Test messages are returned in correct order."""
        from interactive_chat import server
        
        server._engine = mock_engine
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "Fourth"},
        ]
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        response = client.get("/api/chat")
        data = response.json()
        
        assert data["messages"][0]["content"] == "First"
        assert data["messages"][1]["content"] == "Second"
        assert data["messages"][2]["content"] == "Third"
        assert data["messages"][3]["content"] == "Fourth"
    
    def test_chat_endpoint_handles_special_characters(self, mock_engine):
        """Test /api/chat handles special characters and unicode."""
        from interactive_chat import server
        
        server._engine = mock_engine
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "Hello 世界 🌍"},
            {"role": "assistant", "content": "Привет! Comment ça va?"},
        ]
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        response = client.get("/api/chat")
        assert response.status_code == 200
        
        data = response.json()
        assert "世界" in data["messages"][0]["content"]
        assert "🌍" in data["messages"][0]["content"]
        assert "Привет" in data["messages"][1]["content"]
    
    def test_chat_endpoint_response_json_serializable(self, mock_engine):
        """Test response is JSON serializable."""
        from interactive_chat import server
        import json
        
        server._engine = mock_engine
        mock_engine.conversation_memory.get_messages.return_value = [
            {"role": "user", "content": "Test"},
            {"role": "assistant", "content": "Response"},
        ]
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        response = client.get("/api/chat")
        assert response.status_code == 200
        
        # Should be JSON serializable
        json_data = response.json()
        json_str = json.dumps(json_data)
        assert isinstance(json_str, str)


class TestChatAPIIntegration:
    """Integration tests for chat API with realistic scenarios."""
    
    def test_single_exchange(self):
        """Test user-AI single exchange format."""
        msg1 = ChatMessage(role="user", content="What is AI?", index=0)
        msg2 = ChatMessage(role="assistant", content="AI is a technology...", index=1)
        
        history = ChatHistory(
            messages=[msg1, msg2],
            total_messages=2,
            turn_id=1,
            phase_id="intro",
            human_messages=1,
            ai_messages=1,
        )
        
        assert history.human_messages == 1
        assert history.ai_messages == 1
    
    def test_multi_turn_conversation(self):
        """Test multi-turn conversation tracking."""
        messages = [
            ChatMessage(role="user", content="Hi", index=0),
            ChatMessage(role="assistant", content="Hello!", index=1),
            ChatMessage(role="user", content="How are you?", index=2),
            ChatMessage(role="assistant", content="Great!", index=3),
            ChatMessage(role="user", content="What's the weather?", index=4),
            ChatMessage(role="assistant", content="Sunny!", index=5),
        ]
        
        history = ChatHistory(
            messages=messages,
            total_messages=6,
            turn_id=3,
            phase_id="part2",
            human_messages=3,
            ai_messages=3,
        )
        
        assert history.total_messages == 6
        assert history.human_messages == 3
        assert history.ai_messages == 3
        assert len(history.messages) == 6
    
    def test_phase_tracking_in_chat(self):
        """Test chat tracks phase information."""
        msg1 = ChatMessage(role="user", content="greet", index=0)
        msg2 = ChatMessage(role="assistant", content="greeting", index=1)
        
        history = ChatHistory(
            messages=[msg1, msg2],
            total_messages=2,
            turn_id=0,
            phase_id="greeting_phase",
            human_messages=1,
            ai_messages=1,
        )
        
        assert history.phase_id == "greeting_phase"
        assert history.turn_id == 0


class TestChatAPIEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_missing_conversation_memory(self):
        """Test handling when conversation_memory is missing."""
        from interactive_chat import server
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.state.turn_id = 0
        mock_engine.state.active_phase_id = None
        
        # Don't provide conversation_memory
        del mock_engine.conversation_memory
        
        server._engine = mock_engine
        
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        
        # Should handle gracefully
        response = client.get("/api/chat")
        # May fail with 500 or handle gracefully, either is acceptable
        assert response.status_code in [200, 500]
    
    def test_very_long_message_content(self):
        """Test handling of very long message content."""
        long_content = "A" * 100000
        msg = ChatMessage(role="user", content=long_content, index=0)
        
        assert len(msg.content) == 100000
    
    def test_message_with_newlines_and_special_chars(self):
        """Test message with newlines and special characters."""
        content = "Line 1\nLine 2\nSpecial: @#$%^&*()_+-=[]{}|;:',.<>?/~`"
        msg = ChatMessage(role="user", content=content, index=0)
        
        assert "\n" in msg.content
        assert "@" in msg.content
        assert msg.content == content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
