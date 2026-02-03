"""
TDD: API endpoint tests for FastAPI server.

Tests follow the red-green-refactor cycle:
1. Tests written first (RED)
2. Implementation makes tests pass (GREEN)
3. Code cleanup and optimization (REFACTOR)
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

# Fixtures will reference the server after it's created
pytestmark = pytest.mark.asyncio


class TestAPIEndpoints:
    """Test suite for API endpoints."""

    @pytest.fixture
    def mock_engine(self):
        """Mock ConversationEngine for testing."""
        engine = Mock()
        engine.shutdown = False
        engine.turn_processing_event = Mock()
        engine.turn_processing_event.is_set.return_value = False
        
        # Mock SystemState
        state = Mock()
        state.active_phase_id = "part1"
        state.phase_index = 1
        state.total_phases = 5
        state.phase_profile_name = "ielts_full_exam"
        state.current_speaker = "ai"
        state.turn_id = 5
        state.is_ai_speaking = False
        state.conversation_history = [
            {
                "speaker": "ai",
                "transcript": "Hello, what's your name?",
                "timestamp": 100.0,
                "turn_id": 1,
                "phase_id": "greeting",
                "latency_ms": 1250
            },
            {
                "speaker": "human",
                "transcript": "My name is John",
                "timestamp": 105.0,
                "turn_id": 1,
                "phase_id": "greeting",
                "latency_ms": None
            },
        ]
        state.current_phase_profile = Mock()
        state.current_phase_profile.phases = {
            "greeting": Mock(name="Greeting Phase"),
            "part1": Mock(name="Part 1 Questions"),
            "part2": Mock(name="Part 2 Long Turn"),
            "part3": Mock(name="Part 3 Discussion"),
            "closing": Mock(name="Closing"),
        }
        # Set .name attributes properly (Mock().name returns Mock, not string)
        state.current_phase_profile.phases["greeting"].name = "Greeting Phase"
        state.current_phase_profile.phases["part1"].name = "Part 1 Questions"
        state.current_phase_profile.phases["part2"].name = "Part 2 Long Turn"
        state.current_phase_profile.phases["part3"].name = "Part 3 Discussion"
        state.current_phase_profile.phases["closing"].name = "Closing"
        state.phases_completed = ["greeting"]
        state.phase_progress = {
            "greeting": {"duration_sec": 5.2},
            "part1": {"duration_sec": 0}
        }
        state.active_phase_id = "part1"
        state.phase_index = 1
        
        engine.state = state
        
        # Add active_phase_profile for Phase 4 endpoints
        engine.active_phase_profile = state.current_phase_profile
        
        return engine

    @pytest.fixture
    def client(self, mock_engine):
        """FastAPI test client with mocked engine."""
        from interactive_chat.server import app, set_engine
        
        set_engine(mock_engine)
        return TestClient(app)

    # ==================== HEALTH CHECK ====================

    def test_health_endpoint_returns_status(self, client):
        """GET /api/health returns healthy status."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["engine_running"] is True
        assert "timestamp" in data

    def test_health_endpoint_when_engine_shutdown(self, client, mock_engine):
        """GET /api/health returns false when engine is shutdown."""
        mock_engine.shutdown = True
        
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["engine_running"] is False

    def test_health_endpoint_when_no_engine(self, client):
        """GET /api/health handles missing engine."""
        from interactive_chat.server import set_engine
        set_engine(None)
        
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["engine_running"] is False

    # ==================== PHASE STATE ====================

    def test_get_phase_state_returns_current_phase(self, client):
        """GET /api/state/phase returns current phase information."""
        response = client.get("/api/state/phase")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["current_phase_id"] == "part1"
        assert data["phase_index"] == 1
        assert data["total_phases"] == 5
        assert data["phase_profile"] == "ielts_full_exam"
        assert "progress" in data
        assert isinstance(data["progress"], list)

    def test_get_phase_state_progress_includes_all_phases(self, client):
        """GET /api/state/phase includes all phases in progress array."""
        response = client.get("/api/state/phase")
        
        assert response.status_code == 200
        data = response.json()
        progress = data["progress"]
        
        # Should have 5 phases
        assert len(progress) == 5
        
        # Check completed phase
        greeting = next(p for p in progress if p["id"] == "greeting")
        assert greeting["status"] == "completed"
        assert "name" in greeting
        
        # Check active phase
        part1 = next(p for p in progress if p["id"] == "part1")
        assert part1["status"] == "active"
        
        # Check upcoming phases
        part2 = next(p for p in progress if p["id"] == "part2")
        assert part2["status"] == "upcoming"

    def test_get_phase_state_no_engine_returns_503(self, client):
        """GET /api/state/phase returns 503 when engine not initialized."""
        from interactive_chat.server import set_engine
        set_engine(None)
        
        response = client.get("/api/state/phase")
        
        assert response.status_code == 503
        assert "Engine not initialized" in response.json()["detail"]

    # ==================== SPEAKER STATUS ====================

    def test_get_speaker_status_returns_current_speaker(self, client):
        """GET /api/state/speaker returns current speaker information."""
        response = client.get("/api/state/speaker")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["speaker"] in ["human", "ai", "silence"]
        assert "timestamp" in data
        assert data["speaker"] == "ai"

    def test_get_speaker_status_includes_phase_id(self, client):
        """GET /api/state/speaker includes current phase ID."""
        response = client.get("/api/state/speaker")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "phase_id" in data
        assert data["phase_id"] == "part1"

    # ==================== CONVERSATION HISTORY ====================

    def test_get_conversation_history_returns_turns(self, client):
        """GET /api/conversation/history returns conversation turns."""
        response = client.get("/api/conversation/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "turns" in data
        assert "total" in data
        assert isinstance(data["turns"], list)
        assert data["total"] == 2

    def test_get_conversation_history_includes_turn_fields(self, client):
        """GET /api/conversation/history includes all required turn fields."""
        response = client.get("/api/conversation/history")
        
        assert response.status_code == 200
        data = response.json()
        turns = data["turns"]
        
        # Check first turn
        assert turns[0]["speaker"] == "ai"
        assert turns[0]["transcript"] == "Hello, what's your name?"
        assert "timestamp" in turns[0]
        assert "phase_id" in turns[0]
        assert "latency_ms" in turns[0]

    def test_get_conversation_history_respects_limit(self, client):
        """GET /api/conversation/history?limit=1 limits results."""
        response = client.get("/api/conversation/history?limit=1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert len(data["turns"]) == 1

    def test_get_conversation_history_default_limit_is_50(self, client):
        """GET /api/conversation/history defaults to limit=50."""
        response = client.get("/api/conversation/history")
        
        assert response.status_code == 200
        data = response.json()
        
        # Our mock has only 2 turns, so should return 2
        assert data["total"] == 2

    # ==================== FULL STATE ====================

    def test_get_full_state_returns_complete_state(self, client):
        """GET /api/state returns complete conversation state."""
        response = client.get("/api/state")
        
        assert response.status_code == 200
        data = response.json()
        
        # All sections present
        assert "phase" in data
        assert "speaker" in data
        assert "turn_id" in data
        assert "history" in data
        assert "is_processing" in data

    def test_get_full_state_phase_section(self, client):
        """GET /api/state phase section includes progress."""
        response = client.get("/api/state")
        
        assert response.status_code == 200
        data = response.json()
        phase = data["phase"]
        
        assert phase["current_phase_id"] == "part1"
        assert phase["phase_index"] == 1
        assert phase["total_phases"] == 5
        assert "progress" in phase
        assert isinstance(phase["progress"], list)

    def test_get_full_state_speaker_section(self, client):
        """GET /api/state speaker section includes current speaker."""
        response = client.get("/api/state")
        
        assert response.status_code == 200
        data = response.json()
        speaker = data["speaker"]
        
        assert "speaker" in speaker
        assert "timestamp" in speaker
        assert speaker["speaker"] == "ai"

    def test_get_full_state_history_section(self, client):
        """GET /api/state history section includes recent turns."""
        response = client.get("/api/state")
        
        assert response.status_code == 200
        data = response.json()
        history = data["history"]
        
        assert isinstance(history, list)
        assert len(history) == 2
        assert history[0]["speaker"] == "ai"

    def test_get_full_state_is_processing_flag(self, client, mock_engine):
        """GET /api/state is_processing reflects engine state."""
        mock_engine.state.is_ai_speaking = False
        mock_engine.turn_processing_event.is_set.return_value = False
        
        response = client.get("/api/state")
        data = response.json()
        assert data["is_processing"] is False
        
        # Now AI is speaking
        mock_engine.state.is_ai_speaking = True
        response = client.get("/api/state")
        data = response.json()
        assert data["is_processing"] is True

    # ==================== ERROR CASES ====================

    def test_endpoints_return_503_when_engine_not_set(self, client):
        """All endpoints return 503 when engine not initialized."""
        from interactive_chat.server import set_engine
        set_engine(None)
        
        endpoints = [
            "/api/state/phase",
            "/api/state/speaker",
            "/api/conversation/history",
            "/api/state"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 503
            assert "Engine not initialized" in response.json()["detail"]

    def test_invalid_limit_parameter(self, client):
        """GET /api/conversation/history with invalid limit parameter."""
        response = client.get("/api/conversation/history?limit=-5")
        
        # FastAPI should handle validation
        assert response.status_code in [200, 422]  # 422 if validation fails


class TestAPIModels:
    """Test Pydantic models for API requests/responses."""

    def test_event_payload_model(self):
        """EventPayload Pydantic model validates correctly."""
        from interactive_chat.api.models import EventPayload
        
        payload = EventPayload(
            event_name="vad.speech_started",
            timestamp=time.time(),
            phase_id="part1",
            turn_id=5,
            payload={"duration": 0.5}
        )
        
        assert payload.event_name == "vad.speech_started"
        assert payload.phase_id == "part1"
        assert payload.turn_id == 5

    def test_phase_state_model(self):
        """PhaseState Pydantic model validates correctly."""
        from interactive_chat.api.models import PhaseState
        
        progress = [
            {"id": "greeting", "name": "Greeting", "status": "completed"},
            {"id": "part1", "name": "Part 1", "status": "active"},
        ]
        
        state = PhaseState(
            current_phase_id="part1",
            phase_index=1,
            total_phases=5,
            phase_name="Part 1 Questions",
            phase_profile="ielts_full_exam",
            progress=progress
        )
        
        assert state.current_phase_id == "part1"
        assert len(state.progress) == 2

    def test_speaker_status_model(self):
        """SpeakerStatus Pydantic model validates correctly."""
        from interactive_chat.api.models import SpeakerStatus
        
        status = SpeakerStatus(
            speaker="ai",
            timestamp=time.time(),
            phase_id="part1"
        )
        
        assert status.speaker == "ai"
        assert status.speaker in ["human", "ai", "silence"]

    def test_turn_model(self):
        """Turn Pydantic model validates correctly."""
        from interactive_chat.api.models import Turn
        
        turn = Turn(
            turn_id=1,
            speaker="human",
            transcript="What is the capital of France?",
            timestamp=time.time(),
            phase_id="part1",
            duration_sec=3.5,
            latency_ms=1250
        )
        
        assert turn.turn_id == 1
        assert turn.speaker == "human"
        assert turn.latency_ms == 1250

    def test_conversation_state_model(self):
        """ConversationState Pydantic model validates correctly."""
        from interactive_chat.api.models import (
            ConversationState, PhaseState, SpeakerStatus, Turn
        )
        
        phase_state = PhaseState(
            current_phase_id="part1",
            phase_index=1,
            total_phases=5,
            phase_name="Part 1",
            phase_profile="ielts",
            progress=[]
        )
        
        speaker_status = SpeakerStatus(
            speaker="ai",
            timestamp=time.time(),
            phase_id="part1"
        )
        
        turn = Turn(
            turn_id=1,
            speaker="human",
            transcript="Test",
            timestamp=time.time(),
            phase_id="part1",
            duration_sec=2.0,
            latency_ms=None
        )
        
        state = ConversationState(
            phase=phase_state,
            speaker=speaker_status,
            turn_id=1,
            history=[turn],
            is_processing=False
        )
        
        assert state.turn_id == 1
        assert len(state.history) == 1
        assert state.is_processing is False
