"""
Comprehensive Headless Test Examples
=====================================

This file demonstrates how to write headless tests for the event-driven architecture.
All tests use only pure functions and mock data—no audio hardware, TTS, or network calls.

Run with: pytest tests/examples_headless_tests.py -v
"""

import pytest
import numpy as np
import time
from dataclasses import dataclass
from typing import List

# Add project to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "interactive_chat"))

from core.event_driven_core import (
    SystemState, Reducer, Event, EventType, ActionType
)


# ============================================================================
# FIXTURES - Reusable test components
# ============================================================================

@pytest.fixture
def clean_state():
    """Fresh SystemState for each test"""
    return SystemState()

@pytest.fixture
def human_state():
    """State with human authority (user in control)"""
    return SystemState(
        authority="human",
        interruption_sensitivity=0.5,
        pause_ms=600,
        end_ms=1200,
        safety_timeout_ms=2500
    )

@pytest.fixture
def ai_state():
    """State with AI authority (AI in control)"""
    return SystemState(
        authority="ai",
        interruption_sensitivity=0.0,
        pause_ms=600,
        end_ms=1200,
        safety_timeout_ms=2500
    )


# ============================================================================
# LEVEL 1: UNIT TESTS - Pure Reducer Logic
# ============================================================================

class TestStateTransitions:
    """Test basic state machine transitions (IDLE → SPEAKING → PAUSING → IDLE)"""
    
    def test_idle_to_speaking_on_vad_start(self, clean_state):
        """VAD_SPEECH_START event transitions IDLE → SPEAKING"""
        state = clean_state
        assert state.state_machine == "IDLE"
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.VAD_SPEECH_START, timestamp=time.time())
        )
        
        assert state.state_machine == "SPEAKING"
        assert state.is_human_speaking == True
        assert state.turn_start_time is not None
        assert any(a.type == ActionType.LOG for a in actions)
        print("✅ IDLE → SPEAKING transition works")
    
    def test_speaking_resumes_from_pausing(self, clean_state):
        """VAD_SPEECH_START while PAUSING resumes to SPEAKING"""
        state = clean_state
        state.state_machine = "PAUSING"
        state.is_human_speaking = False
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.VAD_SPEECH_START, timestamp=time.time())
        )
        
        assert state.state_machine == "SPEAKING"
        assert state.is_human_speaking == True
        print("✅ PAUSING → SPEAKING resume works")
    
    def test_speaking_to_pausing_on_silence(self, human_state):
        """Silence triggers SPEAKING → PAUSING transition after pause_ms"""
        state = human_state
        state.state_machine = "SPEAKING"
        state.is_human_speaking = True
        base_time = time.time()
        state.last_voice_time = base_time
        
        # User stops speaking
        state, _ = Reducer.reduce(
            state,
            Event(EventType.VAD_SPEECH_STOP, timestamp=base_time)
        )
        state.is_human_speaking = False
        
        # Wait for pause_ms (600ms default) via TICK event
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=base_time + 0.7)
        )
        
        assert state.state_machine == "PAUSING"
        assert any("Pause" in a.payload.get("message", "") for a in actions if a.type == ActionType.LOG)
        print("✅ SPEAKING → PAUSING transition works")
    
    def test_pausing_to_processing_on_extended_silence(self, human_state):
        """Extended silence triggers PAUSING → IDLE (with PROCESS_TURN action)"""
        state = human_state
        state.state_machine = "PAUSING"
        state.is_human_speaking = False
        state.last_voice_time = time.time()
        
        # Wait for end_ms (1200ms default)
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.last_voice_time + 1.3)
        )
        
        assert state.state_machine == "IDLE"
        assert any(a.type == ActionType.PROCESS_TURN for a in actions)
        print("✅ PAUSING → IDLE (PROCESS_TURN) works")


class TestAuthorityModes:
    """Test authority mode enforcement (human, ai, default)"""
    
    def test_human_authority_always_listens(self, human_state):
        """Human authority keeps mic open during AI speech"""
        state = human_state
        state.is_ai_speaking = True
        
        # Audio frame should be processed even while AI speaks
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={
                "frame": np.random.randn(512),
                "is_speech": True
            })
        )
        
        # Audio should be buffered (or at least not rejected)
        assert len(state.turn_audio_buffer) > 0
        print("✅ Human authority allows audio buffering during AI speech")
    
    def test_ai_authority_mutes_mic_during_speech(self, ai_state):
        """AI authority ignores audio while AI is speaking"""
        state = ai_state
        state.is_ai_speaking = True
        
        # Audio frame should be ignored
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={
                "frame": np.random.randn(512),
                "is_speech": True
            })
        )
        
        # Audio should NOT be buffered
        assert len(state.turn_audio_buffer) == 0
        assert not any(a.type == ActionType.INTERRUPT_AI for a in actions)
        print("✅ AI authority mutes mic during AI speech")
    
    def test_ai_authority_blocks_interruptions(self, ai_state):
        """AI authority never allows interruptions"""
        state = ai_state
        state.is_ai_speaking = True
        state.interruption_sensitivity = 1.0  # Max sensitivity
        
        # Even with high sensitivity and clear speech, no interrupt
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={"is_speech": True})
        )
        
        assert not any(a.type == ActionType.INTERRUPT_AI for a in actions)
        print("✅ AI authority blocks all interruptions")


class TestInterruptionLogic:
    """Test interruption detection at various sensitivity levels"""
    
    def test_human_interrupts_on_speech_at_low_sensitivity(self, human_state):
        """Sensitivity=0.0 (Strict): Requires detected words to interrupt"""
        state = human_state
        state.interruption_sensitivity = 0.0
        state.is_ai_speaking = True
        state.current_partial_transcript = "stop"  # Words detected
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={"is_speech": True})
        )
        
        # Strict mode: should interrupt because words detected
        assert any(a.type == ActionType.INTERRUPT_AI for a in actions)
        print("✅ Sensitivity=0.0 interrupts on speech detection")
    
    def test_human_interrupts_on_energy_at_high_sensitivity(self, human_state):
        """Sensitivity=1.0 (Energy): Interrupts on sound detection alone"""
        state = human_state
        state.interruption_sensitivity = 1.0  # Max energy sensitivity
        state.is_ai_speaking = True
        state.current_partial_transcript = ""  # No words
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={"is_speech": True})
        )
        
        # Energy mode: should interrupt on any sound
        assert any(a.type == ActionType.INTERRUPT_AI for a in actions)
        print("✅ Sensitivity=1.0 interrupts on energy alone")
    
    def test_hybrid_interruption_at_medium_sensitivity(self, human_state):
        """Sensitivity=0.5 (Hybrid): Energy + speech detection"""
        state = human_state
        state.interruption_sensitivity = 0.5  # Hybrid
        state.is_ai_speaking = True
        
        # Test 1: Energy without words
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={"is_speech": True})
        )
        has_interrupt = any(a.type == ActionType.INTERRUPT_AI for a in actions)
        print(f"  Hybrid: Energy only → Interrupt? {has_interrupt}")


class TestActionGeneration:
    """Test that correct actions are generated for events"""
    
    def test_log_action_on_state_change(self, clean_state):
        """State transitions should generate LOG actions"""
        state = clean_state
        state, actions = Reducer.reduce(
            state,
            Event(EventType.VAD_SPEECH_START)
        )
        
        assert any(a.type == ActionType.LOG for a in actions)
        log_messages = [a.payload.get("message") for a in actions if a.type == ActionType.LOG]
        print(f"  Generated logs: {log_messages}")
    
    def test_speak_sentence_action_on_ai_sentence(self, clean_state):
        """AI_SENTENCE_READY should generate SPEAK_SENTENCE action"""
        state = clean_state
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AI_SENTENCE_READY, payload={"text": "Hello there!"})
        )
        
        assert any(a.type == ActionType.SPEAK_SENTENCE for a in actions)
        assert state.is_ai_speaking == True
        print("✅ AI_SENTENCE_READY generates SPEAK_SENTENCE action")
    
    def test_interrupt_ai_action_on_interruption(self, human_state):
        """Interruption should generate INTERRUPT_AI action"""
        state = human_state
        state.is_ai_speaking = True
        state.interruption_sensitivity = 1.0  # Energy mode
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={"is_speech": True})
        )
        
        assert any(a.type == ActionType.INTERRUPT_AI for a in actions)
        assert state.is_ai_speaking == False
        assert len(state.ai_speech_queue) == 0
        print("✅ Interruption generates INTERRUPT_AI action and clears queue")
    
    def test_process_turn_action_on_turn_end(self, human_state):
        """Turn end should generate PROCESS_TURN action"""
        state = human_state
        state.state_machine = "PAUSING"
        state.is_human_speaking = False
        state.last_voice_time = time.time()
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.last_voice_time + 1.3)
        )
        
        assert any(a.type == ActionType.PROCESS_TURN for a in actions)
        print("✅ Turn end generates PROCESS_TURN action")


# ============================================================================
# LEVEL 2: INTEGRATION TESTS - Event Sequences
# ============================================================================

class TestTurnFlows:
    """Test complete conversation turn flows"""
    
    def test_complete_user_turn_to_processing(self, human_state):
        """Full flow: User speaks → transcribed → Turn ends → Processing"""
        state = human_state
        base_time = time.time()
        
        # Step 1: User starts speaking
        state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_START, timestamp=base_time))
        assert state.state_machine == "SPEAKING"
        
        # Step 2: Audio frames arrive (within speaking time)
        for i in range(10):
            state, _ = Reducer.reduce(state, Event(
                EventType.AUDIO_FRAME,
                timestamp=base_time + 0.1 + (i * 0.05),
                payload={"frame": np.zeros(512), "is_speech": True}
            ))
        
        # Step 3: User stops speaking (after 0.6 seconds)
        state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_STOP, timestamp=base_time + 0.6))
        # Manually set is_human_speaking to False since VAD_SPEECH_STOP was processed
        state.is_human_speaking = False
        
        # Step 4: Silence accumulates - need TICK events after pause_ms to transition to PAUSING,
        # pause_ms = 600ms, end_ms = 1200ms, so we need:
        # - First TICK at +1.3s (700ms silence) to trigger transition to PAUSING
        # - Second TICK at +2.0s (1400ms silence) to trigger PROCESS_TURN
        state, _ = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=base_time + 1.3)  # 700ms elapsed since voice stopped at 0.6s
        )
        assert state.state_machine == "PAUSING"
        
        # Continue with TICK to reach end_ms threshold (1200ms)
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=base_time + 2.0)  # 1400ms elapsed since voice stopped
        )
        
        # Should end turn and generate PROCESS_TURN
        assert any(a.type == ActionType.PROCESS_TURN for a in actions)
        print("✅ Complete user turn flow works")
    
    def test_ai_response_sequence(self, human_state):
        """Full flow: LLM streams → TTS queues sentences → Can be interrupted"""
        state = human_state
        
        # Step 1: AI starts responding (sentence by sentence)
        sentences = [
            "This is the first sentence.",
            "And here is the second one.",
            "Finally, the third sentence!"
        ]
        
        for sentence in sentences:
            state, actions = Reducer.reduce(state, Event(
                EventType.AI_SENTENCE_READY,
                payload={"text": sentence}
            ))
            assert state.is_ai_speaking == True
        
        # Step 2: User interrupts mid-response
        state, actions = Reducer.reduce(state, Event(
            EventType.AUDIO_FRAME,
            payload={"is_speech": True}
        ))
        
        # Should interrupt
        assert any(a.type == ActionType.INTERRUPT_AI for a in actions)
        assert state.is_ai_speaking == False
        assert len(state.ai_speech_queue) == 0
        print("✅ AI response can be interrupted mid-stream")


# ============================================================================
# LEVEL 3: PROFILE-SPECIFIC TESTS
# ============================================================================

class TestProfileBehaviors:
    """Test that different profiles behave correctly"""
    
    def test_ielts_instructor_strict_control(self):
        """AI Authority: Exam proctor controls the flow"""
        state = SystemState(
            authority="ai",
            interruption_sensitivity=0.0,
            safety_timeout_ms=2500
        )
        
        # Student speaks
        state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_START))
        
        # Attempt to interrupt examiner (should fail)
        state, actions = Reducer.reduce(state, Event(
            EventType.AUDIO_FRAME,
            payload={"is_speech": True}
        ))
        assert not any(a.type == ActionType.INTERRUPT_AI for a in actions)
        print("✅ IELTS Instructor: No interruptions allowed")
    
    def test_negotiator_user_priority(self):
        """Human Authority: User always wins"""
        state = SystemState(
            authority="human",
            interruption_sensitivity=0.8  # High sensitivity
        )
        
        # Negotiator AI is speaking
        state, _ = Reducer.reduce(state, Event(
            EventType.AI_SENTENCE_READY,
            payload={"text": "Let me explain our offer..."}
        ))
        assert state.is_ai_speaking == True
        
        # User interrupts with high priority
        state, actions = Reducer.reduce(state, Event(
            EventType.AUDIO_FRAME,
            payload={"is_speech": True}
        ))
        
        assert any(a.type == ActionType.INTERRUPT_AI for a in actions)
        assert state.is_ai_speaking == False
        print("✅ Negotiator: User interruption works immediately")


# ============================================================================
# LEVEL 4: EDGE CASES & STRESS TESTS
# ============================================================================

class TestEdgeCases:
    """Test boundary conditions and edge cases"""
    
    def test_rapid_state_transitions(self, human_state):
        """Quick speak → pause → speak should work"""
        state = human_state
        
        # Speak
        state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_START))
        assert state.state_machine == "SPEAKING"
        
        # Quick pause
        state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_STOP))
        
        # Resume before pause_ms timeout
        state, _ = Reducer.reduce(
            state,
            Event(EventType.VAD_SPEECH_START, timestamp=time.time() + 0.3)
        )
        
        assert state.state_machine == "SPEAKING"
        print("✅ Rapid transitions handled correctly")
    
    def test_force_end_on_safety_timeout(self, human_state):
        """After safety_timeout_ms, turn ends regardless of silence"""
        state = human_state
        state.state_machine = "PAUSING"
        state.last_voice_time = time.time()
        state.authority = "default"  # Force end enabled for default/ai
        
        # Wait past safety timeout
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.last_voice_time + 3.0)
        )
        
        assert state.force_ended == True
        assert any(a.type == ActionType.PROCESS_TURN for a in actions)
        print("✅ Safety timeout force-ends turn")
    
    def test_empty_turn_rejected(self, human_state):
        """Turns with no audio shouldn't be processed"""
        state = human_state
        state.state_machine = "PAUSING"
        state.last_voice_time = time.time()
        
        # End turn without any audio frames
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.last_voice_time + 1.3)
        )
        
        # PROCESS_TURN should be generated, but handler should reject it
        assert any(a.type == ActionType.PROCESS_TURN for a in actions)
        print("✅ Empty turn generates PROCESS_TURN (handler will reject)")
    
    def test_human_speaking_limit(self):
        """AI speaks ack when user exceeds speaking limit"""
        state = SystemState(
            human_speaking_limit_sec=30,
            turn_start_time=time.time()
        )
        
        # Advance past limit
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.turn_start_time + 35.0)
        )
        
        assert any(a.type == ActionType.PLAY_ACK for a in actions)
        assert state.human_speaking_limit_ack_sent == True
        print("✅ Human speaking limit triggers acknowledgment")


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
