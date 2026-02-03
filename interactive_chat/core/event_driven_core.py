from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict, Tuple
import time
from .signals import emit_signal, SignalName

class EventType(Enum):
    """Enumeration of all system events."""
    VAD_SPEECH_START = "VAD_SPEECH_START"
    VAD_SPEECH_STOP = "VAD_SPEECH_STOP"
    AUDIO_FRAME = "AUDIO_FRAME"
    ASR_PARTIAL_TRANSCRIPT = "ASR_PARTIAL_TRANSCRIPT"
    AI_SENTENCE_READY = "AI_SENTENCE_READY"
    AI_SPEECH_FINISHED = "AI_SPEECH_FINISHED"
    TICK = "TICK"
    RESET_TURN = "RESET_TURN"
    PHASE_TRANSITION = "PHASE_TRANSITION"  # Request phase transition

class ActionType(Enum):
    """Enumeration of all side-effect actions."""
    LOG = "LOG"
    INTERRUPT_AI = "INTERRUPT_AI"
    PROCESS_TURN = "PROCESS_TURN"
    PLAY_ACK = "PLAY_ACK"
    SPEAK_SENTENCE = "SPEAK_SENTENCE"
    LOG_TURN = "LOG_TURN"  # Analytics logging
    TRANSITION_PHASE = "TRANSITION_PHASE"  # Execute phase transition

@dataclass(frozen=True)
class Event:
    """Base class for all events in the system."""
    type: EventType
    timestamp: float = field(default_factory=time.time)
    source: str = "system"
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Action:
    """Side effects triggered by the reducer."""
    type: ActionType
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemState:
    """Single source of truth for the system state."""
    # Conversation status
    is_ai_speaking: bool = False
    is_human_speaking: bool = False
    
    # AI Speech Queue (Internal to state)
    ai_speech_queue: List[str] = field(default_factory=list)
    
    # Timing
    turn_start_time: Optional[float] = None
    last_voice_time: Optional[float] = None
    
    # Audio & Transcription
    turn_audio_buffer: List[Any] = field(default_factory=list)
    current_partial_transcript: str = ""
    
    # Configuration (from active profile)
    authority: str = "human"
    pause_ms: int = 600
    end_ms: int = 1200
    safety_timeout_ms: int = 2500
    interruption_sensitivity: float = 0.5
    human_speaking_limit_sec: Optional[int] = None
    
    # Phase Management (for PhaseProfile support)
    current_phase_id: Optional[str] = None  # Current phase in PhaseProfile (None if standalone)
    phase_profile_name: Optional[str] = None  # Active PhaseProfile name (None if standalone)
    
    # Phase Observation Tracking (NEW)
    active_phase_id: Optional[str] = None              # Current phase ID
    phase_index: int = 0                               # 0-based index in phase list
    total_phases: int = 0                              # Total phases in PhaseProfile
    phases_completed: List[str] = field(default_factory=list)  # ["greeting", "part1"]
    phase_progress: Dict[str, Dict] = field(default_factory=dict)  # {"greeting": {"status": "completed", "duration_sec": 45.2}}
    last_phase_transition_reason: Optional[str] = None # Signal that triggered transition
    
    # Speaker Tracking (NEW)
    current_speaker: str = "silence"  # "human", "ai", "silence"
    previous_speaker: str = "silence"
    
    # Logic State
    human_speaking_limit_ack_sent: bool = False
    force_ended: bool = False
    last_interrupt_time: float = 0
    
    # History
    turn_id: int = 0
    state_machine: str = "IDLE"  # IDLE, SPEAKING, PAUSING
    
    # Turn Metrics (for analytics logging)
    turn_interrupt_attempts: int = 0
    turn_interrupt_accepts: int = 0
    turn_partial_transcripts: List[str] = field(default_factory=list)
    turn_final_transcript: str = ""
    turn_ai_transcript: str = ""
    turn_end_reason: str = ""  # silence, safety_timeout, limit_exceeded
    turn_transcription_ms: float = 0.0
    turn_llm_generation_ms: float = 0.0
    turn_total_latency_ms: float = 0.0
    turn_confidence_score: float = 1.0

class Reducer:
    """Deterministic logic for state transitions."""
    
    @staticmethod
    def _is_mic_muted(state: SystemState) -> bool:
        """Check if microphone should be ignored based on authority and AI speech status."""
        return state.authority == "ai" and state.is_ai_speaking

    @staticmethod
    def reduce(state: SystemState, event: Event) -> Tuple[SystemState, List[Action]]:
        """Process an event and return (updated_state, list_of_actions)."""
        actions = []
        
        # 1. Update Speech Status & Timers
        if event.type == EventType.VAD_SPEECH_START:
            if Reducer._is_mic_muted(state):
                return state, actions
                
            state.is_human_speaking = True
            state.last_voice_time = event.timestamp
            if state.turn_start_time is None:
                state.turn_start_time = event.timestamp
                
            # Update speaker status
            if state.current_speaker != "human":
                state.previous_speaker = state.current_speaker
                state.current_speaker = "human"
                
            if state.state_machine == "IDLE":
                state.state_machine = "SPEAKING"
                actions.append(Action(ActionType.LOG, {"message": "🟢 Speech started"}))
                
                # Emit signal: human started speaking (critical for demo UI)
                emit_signal(
                    SignalName.VAD_SPEECH_STARTED,
                    payload={
                        "timestamp": event.timestamp,
                        "turn_id": state.turn_id,
                    }
                )
            elif state.state_machine == "PAUSING":
                state.state_machine = "SPEAKING"
                actions.append(Action(ActionType.LOG, {"message": "🟢 Speech resumed"}))
                
                # Emit signal: human resumed speaking
                emit_signal(
                    SignalName.VAD_SPEECH_STARTED,
                    payload={
                        "timestamp": event.timestamp,
                        "turn_id": state.turn_id,
                    }
                )
            
        elif event.type == EventType.VAD_SPEECH_STOP:
            if Reducer._is_mic_muted(state):
                return state, actions
            state.is_human_speaking = False
            
            # Emit signal: human stopped speaking (critical for demo UI)
            if state.last_voice_time:
                duration_sec = event.timestamp - state.last_voice_time
                emit_signal(
                    SignalName.VAD_SPEECH_ENDED,
                    payload={
                        "timestamp": event.timestamp,
                        "duration_sec": duration_sec,
                        "turn_id": state.turn_id,
                    }
                )
            
        elif event.type == EventType.AUDIO_FRAME:
            # Check if we should listen
            can_listen = not Reducer._is_mic_muted(state)
            if state.force_ended:
                can_listen = False
                
            if can_listen:
                state.turn_audio_buffer.append(event.payload.get("frame"))
                # If VAD didn't catch it but we got a frame with high energy (simplified for now)
                if event.payload.get("is_speech"):
                    state.last_voice_time = event.timestamp
                    
                # Interruption Check
                if state.is_ai_speaking:
                    should_int, reason = Reducer._check_interruption(state, event)
                    state.turn_interrupt_attempts += 1
                    if should_int:
                        state.turn_interrupt_accepts += 1
                        state.last_interrupt_time = event.timestamp
                        state.is_ai_speaking = False
                        state.ai_speech_queue.clear()
                        actions.append(Action(ActionType.INTERRUPT_AI, {"reason": reason}))
                        actions.append(Action(ActionType.LOG, {"message": f"⚡ INTERRUPT: {reason}"}))
                        
                        # Emit signal for interruption (listeners can react)
                        emit_signal(
                            SignalName.CONVERSATION_INTERRUPTED,
                            payload={
                                "reason": reason,
                                "turn_id": state.turn_id,
                                "authority": state.authority,
                            },
                            context={"source": "reducer"},
                        )

        elif event.type == EventType.ASR_PARTIAL_TRANSCRIPT:
            if Reducer._is_mic_muted(state):
                return state, actions
                
            text = event.payload.get("text", "")
            state.current_partial_transcript = text
            if text:
                state.turn_partial_transcripts.append(text)
                # Suppress ASR partial logs to reduce noise
            
        elif event.type == EventType.AI_SENTENCE_READY:
            text = event.payload.get("text")
            if text:
                # Truncate at 30 chars but stop at signal tags (indicated by '<')
                # If '<' appears within 30 chars, truncate before it
                preview = text[:30]
                signal_pos = preview.find('<')
                if signal_pos != -1:
                    preview = preview[:signal_pos]
                # Only add "..." if there's more text after our preview
                suffix = "..." if len(preview) < len(text) else ""
                actions.append(Action(ActionType.LOG, {"message": f"🤖 AI Sentence ready: {preview}{suffix}"}))
                if not state.is_ai_speaking:
                    state.is_ai_speaking = True
                    
                    # Update speaker status
                    if state.current_speaker != "ai":
                        state.previous_speaker = state.current_speaker
                        state.current_speaker = "ai"
                    
                    # Emit signal: AI started speaking (critical for demo UI)
                    emit_signal(
                        SignalName.TTS_SPEAKING_STARTED,
                        payload={
                            "timestamp": event.timestamp,
                            "text_preview": preview,
                            "turn_id": state.turn_id,
                            "phase_id": state.active_phase_id,
                        }
                    )
                    
                    actions.append(Action(ActionType.SPEAK_SENTENCE, {"text": text}))
                else:
                    state.ai_speech_queue.append(text)
            
        elif event.type == EventType.AI_SPEECH_FINISHED:
            if state.ai_speech_queue:
                next_text = state.ai_speech_queue.pop(0)
                actions.append(Action(ActionType.LOG, {"message": f"🤖 AI speaking next sentence (Queue length: {len(state.ai_speech_queue)})"}))
                actions.append(Action(ActionType.SPEAK_SENTENCE, {"text": next_text}))
            else:
                state.is_ai_speaking = False
                actions.append(Action(ActionType.LOG, {"message": "🎙️ AI finished speaking"}))
                
                # Update speaker status
                if state.current_speaker == "ai":
                    state.previous_speaker = state.current_speaker
                    state.current_speaker = "silence"
                
                # Emit signal: AI finished speaking (critical for demo UI)
                emit_signal(
                    SignalName.TTS_SPEAKING_ENDED,
                    payload={
                        "timestamp": event.timestamp,
                        "turn_id": state.turn_id,
                    }
                )

        elif event.type == EventType.RESET_TURN:
            actions.append(Action(ActionType.LOG, {"message": "🔄 Resetting for next turn"}))
            
            # Log turn analytics if we have a recorded turn
            if state.turn_start_time and state.turn_final_transcript:
                turn_metrics = {
                    "turn_id": state.turn_id,
                    "timestamp": state.turn_start_time,
                    "interrupt_attempts": state.turn_interrupt_attempts,
                    "interrupt_accepts": state.turn_interrupt_accepts,
                    "partial_transcripts": state.turn_partial_transcripts,
                    "final_transcript": state.turn_final_transcript,
                    "ai_transcript": state.turn_ai_transcript,
                    "end_reason": state.turn_end_reason,
                    "transcription_ms": state.turn_transcription_ms,
                    "llm_generation_ms": state.turn_llm_generation_ms,
                    "total_latency_ms": state.turn_total_latency_ms,
                    "confidence_score": state.turn_confidence_score,
                }
                
                actions.append(Action(ActionType.LOG_TURN, turn_metrics))
                
                # Emit signal for turn completion (listeners can react to this)
                emit_signal(
                    SignalName.ANALYTICS_TURN_METRICS,
                    payload=turn_metrics,
                    context={
                        "source": "reducer",
                        "turn_id": state.turn_id,
                    },
                )
                
                # Emit critical signal: turn fully completed (for demo UI)
                emit_signal(
                    SignalName.TURN_COMPLETED,
                    payload={
                        "timestamp": event.timestamp,
                        "turn_id": state.turn_id,
                        "human_transcript": state.turn_final_transcript,
                        "ai_transcript": state.turn_ai_transcript,
                        "total_latency_ms": state.turn_total_latency_ms,
                        "phase_id": state.active_phase_id,
                    }
                )
            
            # Reset turn metrics
            state.turn_audio_buffer.clear()
            state.current_partial_transcript = ""
            state.turn_start_time = None
            state.last_voice_time = None
            state.human_speaking_limit_ack_sent = False
            state.force_ended = False
            state.turn_interrupt_attempts = 0
            state.turn_interrupt_accepts = 0
            state.turn_partial_transcripts = []
            state.turn_final_transcript = ""
            state.turn_ai_transcript = ""
            state.turn_end_reason = ""
            state.turn_transcription_ms = 0.0
            state.turn_llm_generation_ms = 0.0
            state.turn_total_latency_ms = 0.0
            state.turn_confidence_score = 1.0
            state.turn_id += 1
            
        elif event.type == EventType.PHASE_TRANSITION:
            # Handle phase transition request
            next_phase = event.payload.get("next_phase")
            if next_phase:
                state.current_phase_id = next_phase
                actions.append(Action(
                    ActionType.TRANSITION_PHASE,
                    {"next_phase": next_phase}
                ))
                actions.append(Action(
                    ActionType.LOG,
                    {"message": f"🔀 Phase transition to: {next_phase}"}
                ))
            
        elif event.type == EventType.TICK:
            # TICK events fall through to state machine logic below for timeout-driven transitions
            pass
            
        # 2. State Machine Transitions & Turn Management
        now = event.timestamp
        if state.state_machine == "SPEAKING":
            if not state.is_human_speaking:
                elapsed_ms = (now - state.last_voice_time) * 1000 if state.last_voice_time else 0
                if elapsed_ms >= state.pause_ms:
                    state.state_machine = "PAUSING"
                    actions.append(Action(ActionType.LOG, {"message": f"🟡 Pause {int(elapsed_ms)} ms"}))
        
        elif state.state_machine == "PAUSING":
            elapsed_ms = (now - state.last_voice_time) * 1000 if state.last_voice_time else 0
            
            # Change: Authority-aware force end
            if state.authority != "human" and elapsed_ms >= state.safety_timeout_ms:
                state.force_ended = True
                state.turn_end_reason = "safety_timeout"
                actions.append(Action(ActionType.LOG, {"message": f"📍 Processing Turn (Reason: safety_timeout)"}))
                
                # Emit signal: turn processing started (critical for demo UI)
                emit_signal(
                    SignalName.TURN_STARTED,
                    payload={
                        "timestamp": event.timestamp,
                        "turn_id": state.turn_id,
                        "reason": "safety_timeout",
                        "phase_id": state.active_phase_id,
                    }
                )
                
                actions.append(Action(ActionType.PROCESS_TURN, {"reason": "safety_timeout"}))
                state.state_machine = "IDLE" # Reset machine for next turn
            
            # Normal turn end (Confidence based - simplified for now)
            elif elapsed_ms >= state.end_ms:
                state.turn_end_reason = "silence"
                actions.append(Action(ActionType.LOG, {"message": f"📍 Processing Turn (Reason: silence)"}))
                
                # Emit signal: turn processing started (critical for demo UI)
                emit_signal(
                    SignalName.TURN_STARTED,
                    payload={
                        "timestamp": event.timestamp,
                        "turn_id": state.turn_id,
                        "reason": "silence",
                        "phase_id": state.active_phase_id,
                    }
                )
                
                actions.append(Action(ActionType.PROCESS_TURN, {"reason": "silence"}))
                state.state_machine = "IDLE"

        # 3. Human Speaking Limit
        if state.turn_start_time and state.human_speaking_limit_sec and not state.human_speaking_limit_ack_sent:
            duration = now - state.turn_start_time
            if duration > state.human_speaking_limit_sec:
                state.human_speaking_limit_ack_sent = True
                actions.append(Action(ActionType.PLAY_ACK, {"reason": "limit_exceeded"}))
                
                # Emit signal for speaking limit exceeded
                emit_signal(
                    SignalName.CONVERSATION_SPEAKING_LIMIT_EXCEEDED,
                    payload={
                        "limit_sec": state.human_speaking_limit_sec,
                        "actual_duration_sec": duration,
                        "turn_id": state.turn_id,
                    },
                    context={"source": "reducer"},
                )
                
                # In event-driven, we might force a turn end or just play ack
                if state.state_machine == "PAUSING":
                     state.turn_end_reason = "limit_exceeded"
                     actions.append(Action(ActionType.LOG, {"message": f"📍 Processing Turn (Reason: limit_exceeded)"}))
                     actions.append(Action(ActionType.PROCESS_TURN, {"reason": "limit_exceeded"}))
                     state.state_machine = "IDLE"

        return state, actions

    @staticmethod
    def _check_interruption(state: SystemState, event: Event) -> Tuple[bool, str]:
        """Hybrid interruption logic moved from InterruptionManager."""
        if state.authority == "ai":
            return False, "authority is ai"
            
        now_ms = event.timestamp * 1000
        if now_ms - state.last_interrupt_time <= 250: # Debounce
            return False, "debounce"
            
        words = state.current_partial_transcript
        word_count = len(words.split()) if words else 0
        energy_condition = event.payload.get("is_speech", False)
        
        # 1. Authority Overrides (Human authority should be most responsive)
        if state.authority == "human":
            if word_count >= 1:
                return True, f"speech: {words}"
            if energy_condition:
                return True, "energy trigger (absolute human auth)"

        # 2. General Sensitivity Logic
        if state.interruption_sensitivity >= 0.9:
            return energy_condition, "energy spike"
        elif state.interruption_sensitivity <= 0.1:
            return word_count >= 2, f"speech: {words}"
        else:
            if energy_condition and (word_count >= 2 or state.interruption_sensitivity > 0.5):
                return True, "hybrid trigger"
                    
        return False, ""
