"""FastAPI server for Interactive Chat AI demo."""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
import json
import uuid
import asyncio

from .api.models import (
    HealthResponse,
    ErrorResponse,
    PhaseState,
    PhaseProgress,
    SpeakerStatus,
    Turn,
    ConversationState,
    APILimitation,
    WSEventMessage,
    WSConnectionRequest,
)
from .api.session_manager import get_session_manager
from .api.event_buffer import EventBuffer

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


@app.get(
    "/api/limitations",
    response_model=list[APILimitation],
    summary="Get API limitations and workarounds",
    tags=["System"],
)
async def get_limitations():
    """
    Get list of known API limitations and their workarounds.
    
    Phase 1 is a single-user demo. Phase 2 (WebSocket) will add multi-user support.
    """
    return [
        APILimitation(
            limitation="Single user only - engine breaks with 2+ concurrent users",
            workaround="Reload page to reset state between conversations",
            planned_fix="Phase 2 adds session isolation via WebSocket streaming",
            phase="phase_2"
        ),
        APILimitation(
            limitation="No persistent storage - state lost on shutdown",
            workaround="Session logs saved to /logs before shutdown",
            planned_fix="Phase 3 adds database persistence layer",
            phase="phase_3"
        ),
        APILimitation(
            limitation="No authentication - API is public",
            workaround="Deploy behind reverse proxy with auth (nginx, etc.)",
            planned_fix="Phase 3 adds JWT authentication",
            phase="phase_3"
        ),
    ]


# ==================== WEBSOCKET STREAMING ====================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time event streaming.
    
    Connection flow:
    1. Client connects to /ws
    2. Client sends optional WSConnectionRequest (session_id, phase_profile)
    3. Server responds with SessionInfo
    4. Server sends buffered events (catch-up)
    5. Server streams live events in real-time
    6. Client can reconnect with session_id to resume
    
    Message format: All messages are WSEventMessage (JSON)
    
    Close codes:
    - 4001: Invalid session_id (resume failed)
    - 4029: Too many connections from this IP
    - 4503: Engine not initialized
    - 1002: Invalid JSON in message
    """
    
    # Check engine availability
    if _engine is None:
        await websocket.close(code=4503, reason="Engine not initialized")
        return
    
    # Get session manager
    session_mgr = get_session_manager()
    
    # Get client IP
    client_ip = websocket.client.host if websocket.client else "unknown"
    
    # Accept connection
    await websocket.accept()
    
    session_id = None
    connection_id = str(uuid.uuid4())
    
    try:
        # Receive connection request or create new session
        data = await websocket.receive_text()
        
        try:
            req_data = json.loads(data)
            request = WSConnectionRequest(**req_data)
            session_id = request.session_id
        except (json.JSONDecodeError, ValueError):
            await websocket.close(code=1002, reason="Invalid JSON in message")
            return
        
        # Try to resume or create session
        if session_id:
            # Resume existing session
            session = session_mgr.get_session(session_id)
            if not session:
                await websocket.close(code=4001, reason="Invalid session_id")
                return
        else:
            # Check IP rate limit
            if not session_mgr.check_ip_limit(client_ip):
                await websocket.close(code=4029, reason="Too many connections from this IP")
                return
            
            # Create new session
            session = session_mgr.create_session(
                phase_profile=request.phase_profile if request else None,
                user_agent=request.user_agent if request else None
            )
            session_id = session.session_id
        
        # Register connection and IP
        session_mgr.add_connection(session_id, connection_id)
        session_mgr.register_ip_connection(client_ip, session_id)
        
        # Send session info
        session_info_msg = {
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "event_type": "session_created",
            "timestamp": datetime.utcnow().timestamp(),
            "payload": {
                "session_id": session_id,
                "created_at": session.created_at,
                "state": session.state,
            },
            "phase_id": None,
            "turn_id": None,
        }
        await websocket.send_json(session_info_msg)
        
        # Send buffered events (catch-up)
        buffer = session_mgr.get_buffer(session_id)
        if buffer:
            for event in buffer.get_events():
                await websocket.send_json({
                    "message_id": event.message_id,
                    "event_type": event.event_type,
                    "timestamp": event.timestamp,
                    "payload": event.payload,
                    "phase_id": event.phase_id,
                    "turn_id": event.turn_id,
                })
        
        # Set session to ACTIVE
        from .api.models import SessionState
        session_mgr.set_session_state(session_id, SessionState.ACTIVE)
        
        # Listen for messages and stream events
        # In a real implementation, this would:
        # - Listen for client heartbeat messages
        # - Subscribe to engine signals
        # - Stream events to client in real-time
        # - Handle reconnects and catch-up
        
        while True:
            # Try to receive heartbeat or command from client (with timeout)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                # Client sent a message (heartbeat or command)
                session_mgr.update_activity(session_id)
                
                try:
                    json.loads(data)  # Validate JSON
                except json.JSONDecodeError:
                    await websocket.close(code=1002, reason="Invalid JSON in message")
                    return
                
            except asyncio.TimeoutError:
                # No message for 60 seconds - but keep connection alive
                # Send heartbeat
                heartbeat = {
                    "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                    "event_type": "heartbeat",
                    "timestamp": datetime.utcnow().timestamp(),
                    "payload": {},
                    "phase_id": None,
                    "turn_id": None,
                }
                await websocket.send_json(heartbeat)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up
        if session_id:
            session_mgr.remove_connection(session_id, connection_id)
            session_mgr.unregister_ip_connection(client_ip, session_id)


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
