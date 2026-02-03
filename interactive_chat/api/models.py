"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class EventPayload(BaseModel):
    """Real-time signal event for streaming."""
    
    event_name: str = Field(..., description="Signal name (e.g., 'vad.speech_started')")
    timestamp: float = Field(..., description="Unix timestamp")
    phase_id: Optional[str] = Field(None, description="Current phase ID if in phase mode")
    turn_id: Optional[int] = Field(None, description="Current turn ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "event_name": "vad.speech_started",
                "timestamp": 1707052800.123,
                "phase_id": "part1",
                "turn_id": 5,
                "payload": {"duration": 0.5, "confidence": 0.95}
            }
        }
    }


class PhaseProgress(BaseModel):
    """Single phase progress entry."""
    
    id: str = Field(..., description="Phase ID")
    name: str = Field(..., description="Display name")
    status: str = Field(..., description="Status: 'completed', 'active', or 'upcoming'")
    duration_sec: Optional[float] = Field(None, description="Duration of phase in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "greeting",
                "name": "Greeting Phase",
                "status": "completed",
                "duration_sec": 5.2
            }
        }


class PhaseState(BaseModel):
    """Current phase information."""
    
    current_phase_id: str = Field(..., description="Active phase ID")
    phase_index: int = Field(..., description="Current phase index (0-based)")
    total_phases: int = Field(..., description="Total number of phases")
    phase_name: str = Field(..., description="Display name of current phase")
    phase_profile: str = Field(..., description="Profile name (e.g., 'ielts_full_exam')")
    progress: List[PhaseProgress] = Field(..., description="Array of phase statuses")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_phase_id": "part1",
                "phase_index": 1,
                "total_phases": 5,
                "phase_name": "Part 1 Questions",
                "phase_profile": "ielts_full_exam",
                "progress": [
                    {"id": "greeting", "name": "Greeting", "status": "completed"},
                    {"id": "part1", "name": "Part 1", "status": "active"}
                ]
            }
        }


class SpeakerStatus(BaseModel):
    """Real-time speaker status."""
    
    speaker: str = Field(..., description="Current speaker: 'human', 'ai', or 'silence'")
    timestamp: float = Field(..., description="Unix timestamp")
    phase_id: Optional[str] = Field(None, description="Current phase ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "speaker": "ai",
                "timestamp": 1707052800.456,
                "phase_id": "part1"
            }
        }


class Turn(BaseModel):
    """Single conversation turn."""
    
    turn_id: int = Field(..., description="Turn number")
    speaker: str = Field(..., description="'human' or 'ai'")
    transcript: str = Field(..., description="Transcribed text")
    timestamp: float = Field(..., description="Unix timestamp")
    phase_id: str = Field(..., description="Phase ID where turn occurred")
    duration_sec: float = Field(..., description="Turn duration in seconds")
    latency_ms: Optional[int] = Field(None, description="Processing latency in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "turn_id": 1,
                "speaker": "human",
                "transcript": "What is the capital of France?",
                "timestamp": 1707052800.789,
                "phase_id": "part1",
                "duration_sec": 3.5,
                "latency_ms": 1250
            }
        }


class ConversationState(BaseModel):
    """Complete conversation state for UI."""
    
    phase: PhaseState = Field(..., description="Current phase state")
    speaker: SpeakerStatus = Field(..., description="Current speaker status")
    turn_id: int = Field(..., description="Current turn ID")
    history: List[Turn] = Field(..., description="Recent conversation history")
    is_processing: bool = Field(False, description="Whether turn is being processed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phase": {},  # PhaseState object
                "speaker": {},  # SpeakerStatus object
                "turn_id": 5,
                "history": [],  # List of Turn objects
                "is_processing": False
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Health status: 'healthy' or 'unhealthy'")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    engine_running: bool = Field(..., description="Whether ConversationEngine is active")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2026-02-04T12:34:56.789123",
                "engine_running": True
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""
    
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Engine not initialized",
                "status_code": 503,
                "timestamp": "2026-02-04T12:34:56.789123"
            }
        }


# ============================================================================
# Phase 2 Models: WebSocket, Session Management, Event Streaming
# ============================================================================


class SessionState:
    """Session lifecycle states."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class SessionInfo(BaseModel):
    """WebSocket session metadata."""
    
    session_id: str = Field(..., description="Unique session ID (UUID)")
    created_at: float = Field(..., description="Creation timestamp (Unix time)")
    state: str = Field(default=SessionState.INITIALIZING, description="Current session state")
    phase_profile: Optional[str] = Field(None, description="Phase profile name if applicable")
    user_agent: Optional[str] = Field(None, description="Client user agent string")
    last_activity: float = Field(..., description="Last activity timestamp for TTL tracking")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": 1707052800.123,
                "state": "active",
                "phase_profile": "default",
                "user_agent": "Mozilla/5.0...",
                "last_activity": 1707052810.456
            }
        }


class WSEventMessage(BaseModel):
    """WebSocket event message with deduplication."""
    
    message_id: str = Field(..., description="Unique message ID for deduplication")
    event_type: str = Field(..., description="Event type (signal, phase_change, turn_update, etc.)")
    timestamp: float = Field(..., description="Event timestamp (Unix time)")
    payload: Dict[str, Any] = Field(..., description="Event-specific data")
    phase_id: Optional[str] = Field(None, description="Phase ID if applicable")
    turn_id: Optional[int] = Field(None, description="Turn ID if applicable")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_550e8400_0001",
                "event_type": "signal",
                "timestamp": 1707052800.123,
                "payload": {"event_name": "vad.speech_started", "duration": 0.5},
                "phase_id": "part1",
                "turn_id": 5
            }
        }


class WSConnectionRequest(BaseModel):
    """WebSocket connection request payload."""
    
    session_id: Optional[str] = Field(None, description="Existing session ID to resume (optional)")
    phase_profile: Optional[str] = Field(None, description="Phase profile to load")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "phase_profile": "default",
                "user_agent": "Mozilla/5.0..."
            }
        }


class APILimitation(BaseModel):
    """API limitation documentation."""
    
    limitation: str = Field(..., description="Description of the limitation")
    workaround: str = Field(..., description="Current workaround")
    planned_fix: Optional[str] = Field(None, description="When/how it will be fixed")
    phase: Optional[str] = Field(None, description="Phase that addresses this (e.g., 'phase_2')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "limitation": "Single user only - engine breaks with 2+ concurrent users",
                "workaround": "Reload page to reset state between conversations",
                "planned_fix": "Phase 2 adds session isolation via WebSocket",
                "phase": "phase_2"
            }
        }

class TextInput(BaseModel):
    """User text input to engine (simulates ASR output)."""
    
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User input text to process"
    )
    
    @field_validator('text')
    @classmethod
    def validate_non_whitespace(cls, v):
        """Ensure text is not just whitespace."""
        if not v or not v.strip():
            raise ValueError('Text must contain non-whitespace characters')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "My hometown is in the mountains"
            }
        }


class EngineCommandRequest(BaseModel):
    """Command to control engine state."""
    
    command: str = Field(
        ...,
        description="Command: 'start', 'stop', 'pause', or 'resume'"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "command": "pause"
            }
        }


class EngineCommandResponse(BaseModel):
    """Response from engine command."""
    
    status: str = Field(..., description="Command status")
    message: str = Field(..., description="Human-readable message")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "paused",
                "message": "Engine paused",
                "timestamp": "2026-02-04T12:34:56.789Z"
            }
        }


class ConversationReset(BaseModel):
    """Reset conversation to start fresh."""
    
    keep_profile: bool = Field(
        True,
        description="Keep current profile (True) or reset to initial phase (False)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "keep_profile": True
            }
        }


class ResetResponse(BaseModel):
    """Response from reset operation."""
    
    status: str = Field(..., description="'reset' on success")
    message: str = Field(..., description="Status message")
    conversation_memory_cleared: bool = Field(..., description="Whether memory was cleared")
    phase_reset: bool = Field(..., description="Whether phase was reset")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "reset",
                "message": "Conversation reset successfully",
                "conversation_memory_cleared": True,
                "phase_reset": False,
                "timestamp": "2026-02-04T12:34:56.789Z"
            }
        }