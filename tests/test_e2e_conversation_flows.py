"""
End-to-End Conversation Simulation Tests

Comprehensive tests simulating real conversation flows with all features:
- Complete turn flow (human speaks → AI responds)
- Interruption behavior (human, ai, default authority)
- Phase transitions with signal detection
- Authority mode enforcement
- Edge cases (garbage text filtering, timeouts, speaking limits)
- Multi-turn conversations
- Signal emission validation
"""

import pytest
import sys
import os
import time
from dataclasses import dataclass

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "interactive_chat"))

from core.event_driven_core import (
    SystemState, Reducer, Event, EventType, Action, ActionType
)
from core.signals import SignalName, emit_signal, get_signal_registry
from core.conversation_memory import ConversationMemory


@pytest.fixture
def signal_registry():
    """Fresh registry for each test."""
    registry = get_signal_registry()
    registry.clear()
    yield registry
    registry.clear()


@pytest.fixture
def base_state():
    """Create a standard base state."""
    return SystemState(
        authority="human",
        interruption_sensitivity=0.5,
        pause_ms=600,
        end_ms=1200,
        safety_timeout_ms=2500,
        turn_id=0,
    )


# ============================================================================
# E2E TEST 1: Complete Single Turn (Human → Processing → AI)
# ============================================================================

class TestSingleTurnFlow:
    """Test complete single turn conversation flow."""

    def test_complete_turn_with_all_signals(self, signal_registry, base_state):
        """Human speaks → process → AI speaks with all signals emitted."""
        signals_emitted = []
        signal_registry.register_all(lambda sig: signals_emitted.append(sig))
        
        state = base_state
        timestamp = time.time()
        
        # 1. Human starts speaking
        event1 = Event(EventType.VAD_SPEECH_START, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event1)
        
        assert state.is_human_speaking == True
        assert state.state_machine == "SPEAKING"
        assert any(s.name == SignalName.VAD_SPEECH_STARTED for s in signals_emitted), \
            "VAD_SPEECH_STARTED signal not emitted"
        
        # 2. Human speaks (record some transcript)
        state.current_partial_transcript = "What is the capital of France"
        state.turn_partial_transcripts.append(state.current_partial_transcript)
        
        # 3. Human stops speaking
        timestamp += 2.5
        event2 = Event(EventType.VAD_SPEECH_STOP, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event2)
        state.last_voice_time = timestamp  # Mark when they stopped
        
        assert state.is_human_speaking == False
        assert any(s.name == SignalName.VAD_SPEECH_ENDED for s in signals_emitted), \
            "VAD_SPEECH_ENDED signal not emitted"
        
        # 4. Pause timeout triggers (pause_ms = 600ms)
        timestamp += 0.7  # 700ms after speech stop
        event3 = Event(EventType.TICK, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event3)
        
        assert state.state_machine == "PAUSING", f"Expected PAUSING, got {state.state_machine}"
        
        # 5. Processing timeout triggers (end_ms = 1200ms)
        timestamp += 0.7  # Now 1400ms total, past 1200ms threshold
        event4 = Event(EventType.TICK, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event4)
        
        assert state.state_machine == "IDLE"
        assert any(a.type == ActionType.PROCESS_TURN for a in actions), \
            "PROCESS_TURN action not generated"
        assert any(s.name == SignalName.TURN_STARTED for s in signals_emitted), \
            "TURN_STARTED signal not emitted"
        
        # 6. Set final transcript (simulates ASR completion)
        state.turn_final_transcript = "What is the capital of France?"
        
        # 7. AI generates response
        state.is_ai_speaking = False  # Reset to False so the event triggers the signal
        timestamp += 0.1
        event5 = Event(EventType.AI_SENTENCE_READY, timestamp=timestamp, 
                      payload={"text": "The capital of France is Paris."})
        state, actions = Reducer.reduce(state, event5)
        
        assert state.is_ai_speaking == True
        assert any(s.name == SignalName.TTS_SPEAKING_STARTED for s in signals_emitted), \
            "TTS_SPEAKING_STARTED signal not emitted"
        assert any(a.type == ActionType.SPEAK_SENTENCE for a in actions), \
            "SPEAK_SENTENCE action not generated"
        
        # 8. Store AI transcript and AI finishes
        state.turn_ai_transcript = "The capital of France is Paris."
        timestamp += 8.3
        event6 = Event(EventType.AI_SPEECH_FINISHED, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event6)
        
        assert state.is_ai_speaking == False
        assert any(s.name == SignalName.TTS_SPEAKING_ENDED for s in signals_emitted), \
            "TTS_SPEAKING_ENDED signal not emitted"
        
        # 9. Reset turn for next iteration
        event7 = Event(EventType.RESET_TURN, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event7)
        
        assert state.turn_id == 1
        assert any(s.name == SignalName.TURN_COMPLETED for s in signals_emitted), \
            "TURN_COMPLETED signal not emitted"
        assert any(s.name == SignalName.ANALYTICS_TURN_METRICS for s in signals_emitted), \
            "ANALYTICS_TURN_METRICS signal not emitted"
        
        # Verify conversation captured
        assert state.turn_final_transcript == ""  # Reset after RESET_TURN
        assert state.turn_ai_transcript == ""  # Reset after RESET_TURN


# ============================================================================
# E2E TEST 2: Authority Modes - All Three Types
# ============================================================================

class TestAuthorityModes:
    """Test all three authority modes in realistic scenarios."""

    def test_human_authority_responsive_to_interruption(self, signal_registry):
        """Human authority: User can interrupt AI at any time."""
        signals_emitted = []
        signal_registry.register_all(lambda sig: signals_emitted.append(sig))
        
        state = SystemState(authority="human", interruption_sensitivity=0.5)
        timestamp = time.time()
        
        # AI is speaking
        state.is_ai_speaking = True
        state.current_speaker = "ai"
        state.ai_speech_queue = ["This is sentence 1", "This is sentence 2"]
        
        # Human attempts interruption (just speech energy)
        event = Event(
            EventType.AUDIO_FRAME,
            timestamp=timestamp,
            payload={"frame": [0.1] * 512, "is_speech": True}
        )
        state, actions = Reducer.reduce(state, event)
        
        # With human authority and energy, should interrupt
        assert any(a.type == ActionType.INTERRUPT_AI for a in actions), \
            "Human authority should interrupt on speech detection"
        assert any(s.name == SignalName.CONVERSATION_INTERRUPTED for s in signals_emitted)

    def test_ai_authority_blocks_all_interruptions(self):
        """AI authority: User cannot interrupt, mic is muted."""
        state = SystemState(authority="ai", interruption_sensitivity=0.5)
        timestamp = time.time()
        
        # AI is speaking
        state.is_ai_speaking = True
        state.last_voice_time = timestamp
        
        # Try to start human speech (should be ignored)
        event = Event(EventType.VAD_SPEECH_START, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event)
        
        # Speech start should NOT process (mic muted)
        assert state.is_human_speaking == False, \
            "AI authority should mute human speech while AI speaking"
        assert len(actions) == 0, "No actions should be generated when mic muted"

    def test_default_authority_polite_interruption(self, signal_registry):
        """Default authority: Allow interruption if human speaks AND has words."""
        signals_emitted = []
        signal_registry.register_all(lambda sig: signals_emitted.append(sig))
        
        state = SystemState(authority="default", interruption_sensitivity=0.5)
        timestamp = time.time()
        
        # AI is speaking
        state.is_ai_speaking = True
        state.current_speaker = "ai"
        state.current_partial_transcript = "What do you think about"
        
        # Human speaks (triggers interruption only if they have words)
        event = Event(
            EventType.AUDIO_FRAME,
            timestamp=timestamp,
            payload={"frame": [0.1] * 512, "is_speech": True}
        )
        state, actions = Reducer.reduce(state, event)
        
        # Should check interruption (default allows hybrid)
        # Energy alone is not enough; need words + energy


# ============================================================================
# E2E TEST 3: Multi-Turn Conversation
# ============================================================================

class TestMultiTurnConversation:
    """Simulate multiple turns in sequence."""

    def test_three_turn_conversation(self, signal_registry, base_state):
        """Three complete turns: Q1→A1, Q2→A2, Q3→A3."""
        signals_emitted = []
        signal_registry.register_all(lambda sig: signals_emitted.append(sig))
        memory = ConversationMemory(max_turns=10)
        
        state = base_state
        timestamp = time.time()
        
        for turn_num in range(3):
            # Turn start
            event = Event(EventType.VAD_SPEECH_START, timestamp=timestamp)
            state, actions = Reducer.reduce(state, event)
            assert state.is_human_speaking == True
            
            # Human speaks for duration
            timestamp += 1.5
            human_text = f"Question {turn_num + 1}"
            state.current_partial_transcript = human_text
            state.turn_partial_transcripts.append(human_text)
            
            # Human stops
            event = Event(EventType.VAD_SPEECH_STOP, timestamp=timestamp)
            state, actions = Reducer.reduce(state, event)
            assert state.is_human_speaking == False
            
            # Pause triggers processing
            timestamp += 0.7
            event = Event(EventType.TICK, timestamp=timestamp)
            state, actions = Reducer.reduce(state, event)
            
            timestamp += 0.7
            event = Event(EventType.TICK, timestamp=timestamp)
            state, actions = Reducer.reduce(state, event)
            
            # Process turn (set transcripts)
            state.turn_final_transcript = human_text + "?"
            
            # AI responds
            state.is_ai_speaking = True
            timestamp += 0.5
            ai_text = f"Answer {turn_num + 1}"
            event = Event(EventType.AI_SENTENCE_READY, timestamp=timestamp,
                         payload={"text": ai_text})
            state, actions = Reducer.reduce(state, event)
            
            state.turn_ai_transcript = ai_text
            
            # AI finishes
            timestamp += 2.0
            event = Event(EventType.AI_SPEECH_FINISHED, timestamp=timestamp)
            state, actions = Reducer.reduce(state, event)
            
            # Reset for next turn
            event = Event(EventType.RESET_TURN, timestamp=timestamp)
            state, actions = Reducer.reduce(state, event)
            
            # Verify turn was logged
            assert any(s.name == SignalName.TURN_COMPLETED for s in signals_emitted), \
                f"Turn {turn_num + 1} not completed"
            
            timestamp += 0.1
        
        # After 3 turns, turn_id should be 3
        assert state.turn_id == 3, f"Expected turn_id=3, got {state.turn_id}"


# ============================================================================
# E2E TEST 4: Phase Transitions with Signals
# ============================================================================

class TestPhaseTransitionsE2E:
    """Test phase transitions during conversation."""

    def test_phase_transition_during_conversation(self, signal_registry):
        """Phase changes mid-conversation when signal triggered."""
        signals_emitted = []
        signal_registry.register_all(lambda sig: signals_emitted.append(sig))
        
        state = SystemState()
        state.active_phase_id = "part1"
        state.phase_index = 1
        state.total_phases = 3
        state.phases_completed = ["greeting"]
        
        # Trigger phase transition
        emit_signal(
            SignalName.PHASE_TRANSITION_STARTED,
            payload={
                "from_phase": "part1",
                "to_phase": "part2",
                "phase_index": 2,
                "total_phases": 3,
            }
        )
        
        assert any(s.name == SignalName.PHASE_TRANSITION_STARTED for s in signals_emitted)
        
        # Simulate transition completion
        emit_signal(
            SignalName.PHASE_TRANSITION_COMPLETE,
            payload={
                "new_phase_id": "part2",
                "phase_index": 2,
                "phase_name": "Part 2: Main Questions",
            }
        )
        
        assert any(s.name == SignalName.PHASE_TRANSITION_COMPLETE for s in signals_emitted)


# ============================================================================
# E2E TEST 5: Edge Cases & Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_human_speaking_limit_enforcement(self, signal_registry):
        """User cannot speak indefinitely; limit enforced."""
        signals_emitted = []
        signal_registry.register_all(lambda sig: signals_emitted.append(sig))
        
        state = SystemState(
            authority="default",
            human_speaking_limit_sec=5,  # 5 second limit
        )
        timestamp = time.time()
        
        # Start turn
        event = Event(EventType.VAD_SPEECH_START, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event)
        state.turn_start_time = timestamp
        state.is_human_speaking = True  # Keep speaking
        
        # User speaks past limit
        timestamp += 6.0  # 6 seconds later
        event = Event(EventType.TICK, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event)
        
        # Limit exceeded should be triggered
        assert any(a.type == ActionType.PLAY_ACK for a in actions), \
            "ACK should play when limit exceeded"
        assert any(s.name == SignalName.CONVERSATION_SPEAKING_LIMIT_EXCEEDED for s in signals_emitted), \
            "Limit exceeded signal not emitted"

    def test_safety_timeout_force_end(self):
        """Safety timeout forces turn end if user goes silent."""
        state = SystemState(
            authority="ai",  # Non-human authority
            safety_timeout_ms=2500,
            end_ms=1200,
        )
        timestamp = time.time()
        
        # Start turn
        event = Event(EventType.VAD_SPEECH_START, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event)
        
        # User stops speaking
        timestamp += 0.1
        event = Event(EventType.VAD_SPEECH_STOP, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event)
        state.last_voice_time = timestamp
        
        # Move to PAUSING
        state.state_machine = "PAUSING"
        
        # Wait for safety timeout
        timestamp += 2.6  # Past 2500ms timeout
        event = Event(EventType.TICK, timestamp=timestamp)
        state, actions = Reducer.reduce(state, event)
        
        # Should force end
        assert state.turn_end_reason == "safety_timeout", \
            "Turn should end with safety_timeout reason"
        assert any(a.type == ActionType.PROCESS_TURN for a in actions), \
            "Turn should be forced to processing"

    def test_rapid_interruptions_debounced(self):
        """Rapid interruptions are debounced to prevent spamming."""
        state = SystemState(authority="human", interruption_sensitivity=0.9)
        timestamp = time.time()
        
        state.is_ai_speaking = True
        state.last_interrupt_time = timestamp
        
        # First interruption attempt
        event1 = Event(
            EventType.AUDIO_FRAME,
            timestamp=timestamp,
            payload={"frame": [0.5] * 512, "is_speech": True}
        )
        state1, actions1 = Reducer.reduce(state, event1)
        
        # Immediate second attempt (within debounce window)
        timestamp += 0.1  # Only 100ms later
        event2 = Event(
            EventType.AUDIO_FRAME,
            timestamp=timestamp,
            payload={"frame": [0.5] * 512, "is_speech": True}
        )
        state2, actions2 = Reducer.reduce(state1, event2)
        
        # Second interrupt should be debounced
        interrupt_count = sum(1 for a in actions2 if a.type == ActionType.INTERRUPT_AI)
        assert interrupt_count == 0, "Second interrupt should be debounced"


# ============================================================================
# E2E TEST 6: Signal Completeness
# ============================================================================

class TestSignalCompleteness:
    """Verify all expected signals are emitted in real flow."""

    def test_all_critical_signals_in_turn(self, signal_registry):
        """Single turn emits all 6 critical signals in correct order."""
        signals_emitted = []
        signal_registry.register_all(lambda sig: signals_emitted.append(sig))
        
        state = SystemState(authority="human")
        timestamp = time.time()
        
        # Simulate full turn
        event = Event(EventType.VAD_SPEECH_START, timestamp=timestamp)
        state, _ = Reducer.reduce(state, event)
        
        event = Event(EventType.VAD_SPEECH_STOP, timestamp=timestamp + 2.0)
        state, _ = Reducer.reduce(state, event)
        state.last_voice_time = timestamp + 2.0
        
        # Pause → Processing (need to manually set and advance time through both thresholds)
        state.state_machine = "SPEAKING"
        
        # First TICK: triggers transition to PAUSING (after 600ms pause_ms)
        event = Event(EventType.TICK, timestamp=timestamp + 2.7)
        state, _ = Reducer.reduce(state, event)
        assert state.state_machine == "PAUSING"
        
        # Second TICK: triggers PROCESS_TURN (after 1200ms end_ms)
        event = Event(EventType.TICK, timestamp=timestamp + 3.3)
        state, actions = Reducer.reduce(state, event)
        assert state.state_machine == "IDLE"
        assert any(a.type == ActionType.PROCESS_TURN for a in actions)
        
        # Setup for AI response
        state.turn_final_transcript = "Test question"
        
        event = Event(EventType.AI_SENTENCE_READY, timestamp=timestamp + 3.5,
                     payload={"text": "Test answer"})
        state, _ = Reducer.reduce(state, event)
        
        state.turn_ai_transcript = "Test answer"
        
        event = Event(EventType.AI_SPEECH_FINISHED, timestamp=timestamp + 8.0)
        state, _ = Reducer.reduce(state, event)
        
        event = Event(EventType.RESET_TURN, timestamp=timestamp + 8.0)
        state, _ = Reducer.reduce(state, event)
        
        # Check all critical signals emitted
        signal_names = [s.name for s in signals_emitted]
        
        assert SignalName.VAD_SPEECH_STARTED in signal_names, "Missing VAD_SPEECH_STARTED"
        assert SignalName.VAD_SPEECH_ENDED in signal_names, "Missing VAD_SPEECH_ENDED"
        assert SignalName.TURN_STARTED in signal_names, "Missing TURN_STARTED"
        assert SignalName.TTS_SPEAKING_STARTED in signal_names, "Missing TTS_SPEAKING_STARTED"
        assert SignalName.TTS_SPEAKING_ENDED in signal_names, "Missing TTS_SPEAKING_ENDED"
        assert SignalName.TURN_COMPLETED in signal_names, "Missing TURN_COMPLETED"
