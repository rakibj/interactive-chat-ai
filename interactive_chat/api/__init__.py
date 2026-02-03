"""API package initialization."""

from .models import (
    EventPayload,
    PhaseState,
    PhaseProgress,
    SpeakerStatus,
    Turn,
    ConversationState,
    HealthResponse,
    ErrorResponse,
    SessionState,
    SessionInfo,
    WSEventMessage,
    WSConnectionRequest,
    APILimitation,
)
from .event_buffer import EventBuffer
from .session_manager import SessionManager, get_session_manager, set_session_manager

__all__ = [
    # Phase 1 Models
    "EventPayload",
    "PhaseState",
    "PhaseProgress",
    "SpeakerStatus",
    "Turn",
    "ConversationState",
    "HealthResponse",
    "ErrorResponse",
    # Phase 2 Models
    "SessionState",
    "SessionInfo",
    "WSEventMessage",
    "WSConnectionRequest",
    "APILimitation",
    # Phase 2 Utilities
    "EventBuffer",
    "SessionManager",
    "get_session_manager",
    "set_session_manager",
]
