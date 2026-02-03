"""FastAPI server for Interactive Chat AI demo."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

from .api.models import (
    HealthResponse,
    ErrorResponse,
    PhaseState,
    PhaseProgress,
    SpeakerStatus,
    Turn,
    ConversationState,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Interactive Chat AI - Demo API",
    description="Real-time event streaming and state API for Gradio/Next.js dashboard",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for Gradio/Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Note: In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine reference
_engine = None


def set_engine(engine):
    """Register ConversationEngine instance with API server.
    
    Args:
        engine: ConversationEngine instance or None
    
    Note: Engine must be thread-safe. Current implementation is single-user only.
    """
    global _engine
    _engine = engine


# ==================== HEALTH CHECK ====================


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health():
    """Check API and engine health status."""
    is_running = _engine is not None and not _engine.shutdown
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        engine_running=is_running,
    )


# ==================== PHASE STATE ====================


@app.get(
    "/api/state/phase",
    response_model=PhaseState,
    summary="Get current phase state",
    tags=["State"],
)
async def get_phase_state():
    """Get current phase information including progress."""
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    state = _engine.state
    
    if not state.active_phase_id:
        raise HTTPException(status_code=400, detail="No active phase")
    
    progress = _build_phase_progress(state)
    
    return PhaseState(
        current_phase_id=state.active_phase_id,
        phase_index=state.phase_index,
        total_phases=state.total_phases,
        phase_name=state.current_phase_profile.phases[state.active_phase_id].name
        if state.current_phase_profile and state.active_phase_id in state.current_phase_profile.phases
        else "Unknown Phase",
        phase_profile=state.phase_profile_name or "single_profile",
        progress=progress,
    )


# ==================== SPEAKER STATUS ====================


@app.get(
    "/api/state/speaker",
    response_model=SpeakerStatus,
    summary="Get current speaker status",
    tags=["State"],
)
async def get_speaker_status():
    """Get who is currently speaking."""
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    state = _engine.state
    
    return SpeakerStatus(
        speaker=state.current_speaker or "silence",
        timestamp=datetime.now().timestamp(),
        phase_id=state.active_phase_id,
    )


# ==================== CONVERSATION HISTORY ====================


@app.get(
    "/api/conversation/history",
    summary="Get conversation history",
    tags=["Conversation"],
)
async def get_conversation_history(limit: int = 50):
    """Get recent conversation turns.
    
    Args:
        limit: Maximum number of turns to return (default: 50)
    
    Returns:
        Dictionary with 'turns' list and 'total' count
    """
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    
    state = _engine.state
    turns = []
    
    # Get last N turns
    for i, turn_data in enumerate(state.conversation_history[-limit:]):
        turn = Turn(
            turn_id=i,
            speaker=turn_data.get("speaker", "unknown"),
            transcript=turn_data.get("transcript", ""),
            timestamp=turn_data.get("timestamp", 0),
            phase_id=turn_data.get("phase_id", state.active_phase_id or "unknown"),
            duration_sec=turn_data.get("duration_sec", 0),
            latency_ms=turn_data.get("latency_ms"),
        )
        turns.append(turn)
    
    return {
        "turns": turns,
        "total": len(turns),
    }


# ==================== FULL STATE ====================


@app.get(
    "/api/state",
    response_model=ConversationState,
    summary="Get complete conversation state",
    tags=["State"],
)
async def get_full_state():
    """Get all state information needed for UI rendering.
    
    Returns:
        ConversationState with phase, speaker, history, and processing status
    """
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    state = _engine.state
    
    # Build phase state
    progress = _build_phase_progress(state)
    phase_state = PhaseState(
        current_phase_id=state.active_phase_id or "unknown",
        phase_index=state.phase_index,
        total_phases=state.total_phases,
        phase_name=state.current_phase_profile.phases[state.active_phase_id].name
        if state.current_phase_profile and state.active_phase_id in state.current_phase_profile.phases
        else "Unknown",
        phase_profile=state.phase_profile_name or "single_profile",
        progress=progress,
    )
    
    # Build speaker status
    speaker_status = SpeakerStatus(
        speaker=state.current_speaker or "silence",
        timestamp=datetime.now().timestamp(),
        phase_id=state.active_phase_id,
    )
    
    # Build history
    history = []
    for i, turn_data in enumerate(state.conversation_history[-20:]):
        turn = Turn(
            turn_id=i,
            speaker=turn_data.get("speaker", "unknown"),
            transcript=turn_data.get("transcript", ""),
            timestamp=turn_data.get("timestamp", 0),
            phase_id=turn_data.get("phase_id", state.active_phase_id or "unknown"),
            duration_sec=turn_data.get("duration_sec", 0),
            latency_ms=turn_data.get("latency_ms"),
        )
        history.append(turn)
    
    # Check if processing
    is_processing = state.is_ai_speaking or (
        hasattr(_engine, "turn_processing_event")
        and _engine.turn_processing_event.is_set()
    )
    
    return ConversationState(
        phase=phase_state,
        speaker=speaker_status,
        turn_id=state.turn_id,
        history=history,
        is_processing=is_processing,
    )


# ==================== HELPER FUNCTIONS ====================


def _build_phase_progress(state) -> list:
    """Build phase progress array from state.
    
    Args:
        state: SystemState instance
    
    Returns:
        List of PhaseProgress objects
    """
    if not state.current_phase_profile:
        return []
    
    progress = []
    for phase_id, phase_prof in state.current_phase_profile.phases.items():
        # Determine status
        if phase_id in (state.phases_completed or []):
            status = "completed"
        elif phase_id == state.active_phase_id:
            status = "active"
        else:
            status = "upcoming"
        
        # Get duration if available
        duration_sec = None
        if state.phase_progress and phase_id in state.phase_progress:
            duration_sec = state.phase_progress[phase_id].get("duration_sec")
        
        progress.append(
            PhaseProgress(
                id=phase_id,
                name=phase_prof.name,
                status=status,
                duration_sec=duration_sec,
            )
        )
    
    return progress


# ==================== API DOCUMENTATION ====================


@app.get("/docs", include_in_schema=False)
async def get_docs():
    """Swagger UI documentation."""
    pass


@app.get("/redoc", include_in_schema=False)
async def get_redoc():
    """ReDoc documentation."""
    pass


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
