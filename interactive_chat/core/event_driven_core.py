from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict, Tuple
import time

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

class ActionType(Enum):
    """Enumeration of all side-effect actions."""
    LOG = "LOG"
    INTERRUPT_AI = "INTERRUPT_AI"
    PROCESS_TURN = "PROCESS_TURN"
    PLAY_ACK = "PLAY_ACK"
    SPEAK_SENTENCE = "SPEAK_SENTENCE"  # New

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
    
    # Logic State
    human_speaking_limit_ack_sent: bool = False
    force_ended: bool = False
    last_interrupt_time: float = 0
    
    # History
    turn_id: int = 0
    state_machine: str = "IDLE"  # IDLE, SPEAKING, PAUSING

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
                
            if state.state_machine == "IDLE":
                state.state_machine = "SPEAKING"
                actions.append(Action(ActionType.LOG, {"message": "🟢 Speech started"}))
            elif state.state_machine == "PAUSING":
                state.state_machine = "SPEAKING"
                actions.append(Action(ActionType.LOG, {"message": "🟢 Speech resumed"}))
            
        elif event.type == EventType.VAD_SPEECH_STOP:
            if Reducer._is_mic_muted(state):
                return state, actions
            state.is_human_speaking = False
            
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
                    if should_int:
                        state.last_interrupt_time = event.timestamp
                        state.is_ai_speaking = False
                        state.ai_speech_queue.clear()
                        actions.append(Action(ActionType.INTERRUPT_AI, {"reason": reason}))
                        actions.append(Action(ActionType.LOG, {"message": f"⚡ INTERRUPT: {reason}"}))
                    # Add a log for why it DIDN'T interrupt if we want to be very verbose, 
                    # but let's stick to state changes for now.

        elif event.type == EventType.ASR_PARTIAL_TRANSCRIPT:
            if Reducer._is_mic_muted(state):
                return state, actions
                
            text = event.payload.get("text", "")
            state.current_partial_transcript = text
            if text:
                actions.append(Action(ActionType.LOG, {"message": f"📝 ASR Partial: '{text}'"}))
            
        elif event.type == EventType.AI_SENTENCE_READY:
            text = event.payload.get("text")
            if text:
                actions.append(Action(ActionType.LOG, {"message": f"🤖 AI Sentence ready: {text[:30]}..."}))
                if not state.is_ai_speaking:
                    state.is_ai_speaking = True
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

        elif event.type == EventType.RESET_TURN:
            actions.append(Action(ActionType.LOG, {"message": "🔄 Resetting for next turn"}))
            state.turn_audio_buffer.clear()
            state.current_partial_transcript = ""
            state.turn_start_time = None
            state.last_voice_time = None
            state.human_speaking_limit_ack_sent = False
            state.force_ended = False
            state.turn_id += 1
            
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
                actions.append(Action(ActionType.LOG, {"message": f"📍 Processing Turn (Reason: safety_timeout)"}))
                actions.append(Action(ActionType.PROCESS_TURN, {"reason": "safety_timeout"}))
                state.state_machine = "IDLE" # Reset machine for next turn
            
            # Normal turn end (Confidence based - simplified for now)
            elif elapsed_ms >= state.end_ms:
                actions.append(Action(ActionType.LOG, {"message": f"📍 Processing Turn (Reason: silence)"}))
                actions.append(Action(ActionType.PROCESS_TURN, {"reason": "silence"}))
                state.state_machine = "IDLE"

        # 3. Human Speaking Limit
        if state.turn_start_time and state.human_speaking_limit_sec and not state.human_speaking_limit_ack_sent:
            duration = now - state.turn_start_time
            if duration > state.human_speaking_limit_sec:
                state.human_speaking_limit_ack_sent = True
                actions.append(Action(ActionType.PLAY_ACK, {"reason": "limit_exceeded"}))
                # In event-driven, we might force a turn end or just play ack
                if state.state_machine == "PAUSING":
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
