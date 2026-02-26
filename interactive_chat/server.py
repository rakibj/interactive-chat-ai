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
    TextInput,
    EngineCommandRequest,
    EngineCommandResponse,
    ConversationReset,
    ResetResponse,
    WSConnectionRequest,
    ChatMessage,
    ChatHistory,
    PhaseMessages,
    PhaseGroupedChatHistory,
)
from .api.session_manager import get_session_manager
from .api.event_buffer import EventBuffer
from .core.event_driven_core import Event

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
    is_running = _engine is not None and not _engine.shutdown_event.is_set()
    
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
    
    progress = _build_phase_progress(state, _engine)
    
    # Get phase name from engine's active_phase_profile
    phase_name = "Unknown Phase"
    if _engine.active_phase_profile and state.active_phase_id:
        try:
            phases_dict = getattr(_engine.active_phase_profile, 'phases', None)
            if phases_dict and isinstance(phases_dict, dict) and state.active_phase_id in phases_dict:
                phase_obj = phases_dict[state.active_phase_id]
                if hasattr(phase_obj, 'name') and isinstance(phase_obj.name, str):
                    phase_name = phase_obj.name
        except (KeyError, AttributeError, TypeError):
            phase_name = "Unknown Phase"
    
    return PhaseState(
        current_phase_id=state.active_phase_id,
        phase_index=state.phase_index,
        total_phases=state.total_phases,
        phase_name=phase_name,
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
    
    # Get last N turns from conversation_history (if available)
    conversation_history = getattr(state, 'conversation_history', [])
    for i, turn_data in enumerate(conversation_history[-limit:]):
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


# ==================== CHAT MESSAGES API ====================


@app.get(
    "/api/chat",
    response_model=None,
    summary="Get formatted chat messages (human + AI texts)",
    tags=["Conversation"],
)
async def get_chat_messages(limit: int = 100):
    """Get conversation messages formatted for UI display.
    
    Returns the complete conversation history from ALL PHASES with human and AI messages
    formatted and ready for chat UI rendering.
    
    Args:
        limit: Maximum number of messages to return (default: 100, max: 500)
    
    Returns:
        ChatHistory with messages, metadata, and statistics
    """
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Validate limit
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    
    state = _engine.state
    
    # IMPORTANT: Build complete message history from ALL PHASES
    # Include messages from message_history_by_phase (previous phases) + current memory
    all_messages = []
    
    # 1. Get messages from completed phases (preserved in message_history_by_phase)
    message_history_by_phase = getattr(state, "message_history_by_phase", {})
    
    # Add messages from each completed phase in order
    phases_completed = getattr(state, "phases_completed", [])
    for phase_id in phases_completed:
        if phase_id in message_history_by_phase:
            phase_messages = message_history_by_phase[phase_id]
            for msg in phase_messages:
                role = msg.get("role", "system")
                if role != "system":  # Skip system messages
                    all_messages.append(msg)
    
    # 2. Get messages from current phase (conversation memory)
    current_phase_id = state.active_phase_id or "current"
    try:
        current_messages_raw = _engine.conversation_memory.get_messages()
        for msg in current_messages_raw:
            role = msg.get("role", "system")
            if role != "system":  # Skip system messages
                all_messages.append(msg)
    except AttributeError:
        pass
    
    # Count message types and skip duplicates
    human_count = 0
    ai_count = 0
    current_time = datetime.now().timestamp()
    
    # Filter and format messages (skip system messages for display)
    for raw_msg in all_messages:
        role = raw_msg.get("role", "system")
        
        # Count message types
        if role == "user":
            human_count += 1
        elif role == "assistant":
            ai_count += 1
    
    # Take only the last `limit` messages for display and assign indices
    messages = []
    displayed_messages = all_messages[-limit:] if all_messages else []
    
    for display_index, msg_dict in enumerate(displayed_messages):
        chat_msg = ChatMessage(
            role=msg_dict["role"],
            content=msg_dict["content"],
            index=display_index,
            timestamp=current_time
        )
        messages.append(chat_msg)
    
    return ChatHistory(
        messages=messages,
        total_messages=len(messages),
        turn_id=state.turn_id,
        phase_id=state.active_phase_id,
        human_messages=human_count,
        ai_messages=ai_count,
    ).model_dump()


# ==================== PHASE-GROUPED CHAT HISTORY ====================


@app.get(
    "/api/chat/phases",
    response_model=None,
    summary="Get chat messages grouped by phases",
    tags=["Conversation"],
)
async def get_chat_messages_by_phases():
    """Get conversation messages grouped by phases with complete phase metadata.
    
    Returns all messages organized by phase boundaries with phase information.
    This endpoint is optimized for UI display with phase dividers.
    
    Returns:
        PhaseGroupedChatHistory with phases, messages, and phase tracking
    """
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    state = _engine.state
    
    # Build complete message history from history log + current messages
    message_history_by_phase = dict(getattr(state, "message_history_by_phase", {}))
    
    # Add current phase's messages (from conversation_memory)
    try:
        current_messages_raw = _engine.conversation_memory.get_messages()
        current_messages = [
            msg for msg in current_messages_raw
            if msg.get("role") != "system"
        ]
        active_phase_id = state.active_phase_id or "default"
        message_history_by_phase[active_phase_id] = current_messages
    except AttributeError:
        current_messages = []
    
    # Count total messages and types across ALL phases
    human_count = 0
    ai_count = 0
    all_messages_flat = []
    
    for phase_id, phase_messages in message_history_by_phase.items():
        for msg in phase_messages:
            role = msg.get("role", "system")
            if role == "user":
                human_count += 1
            elif role == "assistant":
                ai_count += 1
            all_messages_flat.append({"role": role, "content": msg.get("content", ""), "phase_id": phase_id})
    
    current_time = datetime.now().timestamp()
    
    # Get phase information from engine
    active_phase_id = state.active_phase_id or "default"
    phases_completed = getattr(state, "phases_completed", [])
    total_phases = getattr(state, "total_phases", 1)
    current_phase_profile = _engine.active_phase_profile if hasattr(_engine, "active_phase_profile") else None
    
    # Build phase list in PROFILE ORDER (not completion order)
    phases_list = []
    
    # CRITICAL: Get phases in their actual profile order, not in completed order
    # Check if current_phase_profile has a valid .phases dict
    all_profile_phase_ids = []
    
    if current_phase_profile:
        try:
            # Try to get phases from profile (handles both real profiles and properly configured mocks)
            phases_dict = getattr(current_phase_profile, 'phases', None)
            if phases_dict and isinstance(phases_dict, dict):
                all_profile_phase_ids = list(phases_dict.keys())
        except (AttributeError, TypeError):
            pass
    
    # If no phases from profile, build from completed phases and message history
    if not all_profile_phase_ids:
        # Combine all phase IDs that have either messages or are marked as completed
        all_phase_ids_set = set()
        
        # Add completed phases
        if phases_completed:
            all_phase_ids_set.update(phases_completed)
        
        # Add phases that have messages in history
        all_phase_ids_set.update(message_history_by_phase.keys())
        
        # Add active phase if not already included
        if active_phase_id:
            all_phase_ids_set.add(active_phase_id)
        
        # Order: completed phases first, then active, then any others
        ordered_ids = []
        for phase_id in (phases_completed or []):
            if phase_id in all_phase_ids_set:
                ordered_ids.append(phase_id)
                all_phase_ids_set.discard(phase_id)
        
        # Add active phase if not already added
        if active_phase_id and active_phase_id in all_phase_ids_set:
            ordered_ids.append(active_phase_id)
            all_phase_ids_set.discard(active_phase_id)
        
        # Add remaining phases from message history
        ordered_ids.extend(sorted(all_phase_ids_set))
        
        all_profile_phase_ids = ordered_ids if ordered_ids else [active_phase_id or "default"]
    
    # Build phases list in profile order
    for phase_index, phase_id in enumerate(all_profile_phase_ids):
        # Determine phase status
        if phase_id in phases_completed:
            phase_status = "completed"
        elif phase_id == active_phase_id:
            phase_status = "active"
        else:
            phase_status = "upcoming"
        
        # Get messages for this phase
        phase_msgs = message_history_by_phase.get(phase_id, [])
        chat_messages = []
        for idx, msg_dict in enumerate(phase_msgs):
            chat_msg = ChatMessage(
                role=msg_dict["role"],
                content=msg_dict["content"],
                index=idx,
                timestamp=current_time
            )
            chat_messages.append(chat_msg)
        
        # Get phase name from profile if available
        phase_name = phase_id.replace("_", " ").title()
        if current_phase_profile:
            try:
                phases_dict = getattr(current_phase_profile, 'phases', None)
                if phases_dict and isinstance(phases_dict, dict) and phase_id in phases_dict:
                    phase_obj = phases_dict[phase_id]
                    if hasattr(phase_obj, 'name') and isinstance(phase_obj.name, str):
                        phase_name = phase_obj.name
            except (AttributeError, TypeError):
                pass
        
        # Create phase entry with correct index based on profile order
        phase_entry = PhaseMessages(
            phase_id=phase_id,
            phase_name=phase_name,
            phase_index=phase_index,  # Index is position in profile
            status=phase_status,
            messages=chat_messages,
            message_count=len(chat_messages),
            duration_sec=None
        )
        phases_list.append(phase_entry)
    
    return PhaseGroupedChatHistory(
        phases=phases_list,
        current_phase_id=active_phase_id,
        total_messages=len(all_messages_flat),
        total_phases=total_phases,
        phases_completed=phases_completed,
        human_messages=human_count,
        ai_messages=ai_count,
        turn_id=state.turn_id,
        phase_profile=current_phase_profile.name if current_phase_profile else None
    ).model_dump()


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
    progress = _build_phase_progress(state, _engine)
    
    # Get phase name from engine's active_phase_profile if available
    phase_name = "Unknown"
    if _engine.active_phase_profile and state.active_phase_id:
        try:
            phase_name = _engine.active_phase_profile.phases[state.active_phase_id].name
        except (KeyError, AttributeError, TypeError):
            phase_name = "Unknown"
    
    phase_state = PhaseState(
        current_phase_id=state.active_phase_id or "unknown",
        phase_index=state.phase_index,
        total_phases=state.total_phases,
        phase_name=phase_name,
        phase_profile=state.phase_profile_name or "single_profile",
        progress=progress,
    )
    
    # Build speaker status (use state.current_speaker if available, otherwise "silence")
    current_speaker = getattr(state, 'current_speaker', 'silence') or 'silence'
    speaker_status = SpeakerStatus(
        speaker=current_speaker,
        timestamp=datetime.now().timestamp(),
        phase_id=state.active_phase_id,
    )
    
    # Build history from available data
    history = []
    # conversation_history doesn't exist in SystemState, so we start with empty list
    # In the future, we can populate this from analytics or a separate history store
    conversation_history = getattr(state, 'conversation_history', [])
    
    for i, turn_data in enumerate(conversation_history[-20:]):
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
    
    # DEBUG: Log state info for diagnostics
    import sys
    timestamp = datetime.now().isoformat()
    debug_line = f"[API GET /state] {timestamp} | speaker={current_speaker} | processing={is_processing} | turn_id={state.turn_id} | machine={state.state_machine} | human_speaking={state.is_human_speaking}"
    print(debug_line, file=sys.stderr, flush=True)
    
    return ConversationState(
        phase=phase_state,
        speaker=speaker_status,
        turn_id=state.turn_id,
        history=history,
        is_processing=is_processing,
    )


# ==================== HELPER FUNCTIONS ====================


def _build_phase_progress(state, engine=None) -> list:
    """Build phase progress array from state.
    
    Args:
        state: SystemState instance
        engine: ConversationEngine instance (for access to active_phase_profile)
    
    Returns:
        List of PhaseProgress objects
    """
    # Handle missing engine or phase profile gracefully
    try:
        if not engine or not hasattr(engine, 'active_phase_profile') or not engine.active_phase_profile:
            return []
        
        profile = engine.active_phase_profile
        
        # Safety check: ensure phases attribute exists and is a dict
        phases_dict = getattr(profile, 'phases', None)
        if not phases_dict or not isinstance(phases_dict, dict):
            return []
        
        progress = []
        for phase_id, phase_prof in phases_dict.items():
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
            
            # Get phase name safely
            phase_name = phase_id.replace("_", " ").title()
            if hasattr(phase_prof, 'name') and isinstance(phase_prof.name, str):
                phase_name = phase_prof.name
            
            progress.append(
                PhaseProgress(
                    id=phase_id,
                    name=phase_name,
                    status=status,
                    duration_sec=duration_sec,
                )
            )
        
        return progress
    except (AttributeError, TypeError, KeyError):
        # If anything goes wrong, just return empty progress
        return []


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


# ==================== DEBUG ENDPOINTS ====================


@app.get(
    "/api/debug/memory",
    summary="DEBUG: Get raw conversation memory state",
    tags=["Debug"],
)
async def debug_conversation_memory():
    """DEBUG endpoint: Returns raw state of conversation memory for troubleshooting.
    
    This is a development/debug endpoint only. Shows exactly what's stored in memory.
    """
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        messages_raw = _engine.conversation_memory.get_messages()
    except AttributeError:
        messages_raw = []
    
    return {
        "total_raw_messages": len(messages_raw),
        "messages_raw": messages_raw,
        "engine_turn_id": _engine.state.turn_id,
        "engine_active_phase": _engine.state.active_phase_id,
        "engine_speaker": getattr(_engine.state, 'current_speaker', 'unknown'),
    }


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


# ============================================================================
# PHASE 4: INTERACTIVE CONTROL ENDPOINTS
# ============================================================================


@app.post("/api/conversation/text-input", response_model=dict)
def handle_text_input(input_data: TextInput):
    """
    Process user text input through the engine.
    Simulates ASR output and injects into conversation.
    """
    global _engine
    
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # Create ASR_FINAL_TRANSCRIPT event from text
        event = Event(
            type="ASR_FINAL_TRANSCRIPT",
            payload={"text": input_data.text}
        )
        
        # Inject into engine's event queue
        _engine.event_queue.append(event)
        
        # Process one turn
        _engine.process_turn(
            override_source="text_input"
        )
        
        # Get updated state
        state = _engine.get_state()
        return {
            "status": "processed",
            "message": f"Processed text input: {input_data.text[:50]}...",
            "state": state
        }
    except Exception as e:
        logger.error(f"Text input error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/engine/command", response_model=EngineCommandResponse)
def handle_engine_command(cmd: EngineCommandRequest):
    """
    Control engine state with commands: start, stop, pause, resume.
    """
    global _engine
    
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        command = cmd.command.lower()
        timestamp = datetime.now().isoformat()
        
        if command == "start":
            _engine.is_paused = False
            return EngineCommandResponse(
                status="started",
                message="Engine started",
                timestamp=timestamp
            )
        elif command == "stop":
            _engine.is_paused = True
            _engine.conversation_memory.clear()
            return EngineCommandResponse(
                status="stopped",
                message="Engine stopped and memory cleared",
                timestamp=timestamp
            )
        elif command == "pause":
            _engine.is_paused = True
            return EngineCommandResponse(
                status="paused",
                message="Engine paused",
                timestamp=timestamp
            )
        elif command == "resume":
            _engine.is_paused = False
            return EngineCommandResponse(
                status="resumed",
                message="Engine resumed",
                timestamp=timestamp
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown command: {command}. Use: start, stop, pause, resume"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Engine command error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/start", response_model=dict)
def trigger_ai_start():
    """
    Trigger AI to start the conversation automatically.
    Used for AI-authority mode.
    """
    global _engine
    
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        timestamp = datetime.now().isoformat()
        
        # Resume engine if paused
        if _engine.is_paused:
            _engine.is_paused = False
        
        # Signal that AI should start (implementation depends on engine)
        logger.info("AI auto-start triggered")
        
        return {
            "status": "started",
            "message": "AI conversation started automatically",
            "timestamp": timestamp
        }
    except Exception as e:
        logger.error(f"Auto-start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/conversation/reset", response_model=ResetResponse)
def reset_conversation(reset_req: ConversationReset):
    """
    Reset conversation state: clear memory and optionally reset phase.
    """
    global _engine
    
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        timestamp = datetime.now().isoformat()
        
        # Clear conversation memory
        _engine.conversation_memory.clear()
        
        # Reset phase if requested
        phase_reset = False
        if not reset_req.keep_profile:
            _engine.active_phase_profile = 0
            phase_reset = True
        
        # Reset pause state
        _engine.is_paused = False
        
        return ResetResponse(
            status="reset",
            message="Conversation reset successfully",
            conversation_memory_cleared=True,
            phase_reset=phase_reset,
            timestamp=timestamp
        )
    except Exception as e:
        logger.error(f"Reset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TESTING ENDPOINTS ====================


@app.post(
    "/api/test/phase-transition",
    response_model=dict,
    summary="[TEST] Simulate a phase transition",
    tags=["Testing"],
)
async def test_phase_transition(phase_name: str = "Phase 2"):
    """[TESTING ONLY] Simulate a phase transition for UI testing.
    
    This endpoint is for testing the phase change detector in the frontend.
    It transitions to a new phase and updates the state.
    
    Args:
        phase_name: Name of the phase to transition to
    
    Returns:
        Status message with new phase info
    """
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Get current state
    state = _engine.state
    
    # Save current phase's messages before transitioning
    if state.active_phase_id:
        current_messages = _engine.conversation_memory.get_messages()
        current_messages = [m for m in current_messages if m.get("role") != "system"]
        if state.active_phase_id not in state.message_history_by_phase:
            state.message_history_by_phase[state.active_phase_id] = []
        state.message_history_by_phase[state.active_phase_id].extend(current_messages)
        
        # Only mark as completed if not already in the list (prevent duplicates)
        if state.active_phase_id not in state.phases_completed:
            state.phases_completed.append(state.active_phase_id)
        
        # CRITICAL: Deduplicate the entire list (remove any accumulated duplicates)
        # Use dict.fromkeys to preserve order while removing duplicates
        state.phases_completed = list(dict.fromkeys(state.phases_completed))
    
    # Transition to new phase
    new_phase_id = phase_name.lower().replace(" ", "_")
    state.active_phase_id = new_phase_id
    state.current_phase_id = new_phase_id  # Keep these in sync
    
    # Get the actual phase profile to get the proper name
    actual_phase_name = phase_name
    if _engine.active_phase_profile and new_phase_id in _engine.active_phase_profile.phases:
        phase_profile = _engine.active_phase_profile.phases[new_phase_id]
        actual_phase_name = phase_profile.name
    
    state.active_phase_name = actual_phase_name
    
    # Calculate phase_index: position in the actual phase list (if available)
    if _engine.active_phase_profile:
        phase_ids = list(_engine.active_phase_profile.phases.keys())
        state.phase_index = phase_ids.index(new_phase_id) if new_phase_id in phase_ids else len(phase_ids) - 1
    else:
        # Fallback: count of completed + 1 (for current)
        state.phase_index = len(state.phases_completed)
    
    # DO NOT clear conversation_memory - messages are preserved in message_history_by_phase
    # and the /api/chat endpoint reconstructs the full history from all phases
    # _engine.conversation_memory.clear()  # REMOVED: Preserve chat history across phases
    
    return {
        "success": True,
        "message": f"Transitioned to phase: {actual_phase_name}",
        "phase_id": new_phase_id,
        "phase_name": actual_phase_name,
        "phase_index": state.phase_index,
        "phases_completed": state.phases_completed,
    }


@app.get(
    "/api/test/phases-status",
    response_model=dict,
    summary="[TEST] Get current phase status",
    tags=["Testing"],
)
async def test_phases_status():
    """[TESTING ONLY] Get current phase status for debugging.
    
    Returns detailed phase state information.
    """
    if not _engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    state = _engine.state
    
    # Get available phases from profile
    available_phases = []
    if _engine.active_phase_profile:
        available_phases = list(_engine.active_phase_profile.phases.keys())
    
    return {
        "active_phase_id": state.active_phase_id,
        "active_phase_name": getattr(state, "active_phase_name", None),
        "phase_index": state.phase_index,
        "total_phases": state.total_phases,
        "phases_completed": state.phases_completed,
        "available_phases": available_phases,
        "message_history_keys": list(state.message_history_by_phase.keys()),
        "phase_change_log": [
            f"{pid}: {len(msgs)} messages"
            for pid, msgs in state.message_history_by_phase.items()
        ],
    }


# ==================== DOCUMENTATION ====================


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
