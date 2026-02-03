"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field
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
