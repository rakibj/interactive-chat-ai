"""
Standalone Headless Test Examples (No pytest required)
========================================================

This file demonstrates how to write headless tests for the event-driven architecture.
Run with: python tests/test_headless_standalone.py

All tests use only pure functions and mock data—no audio hardware, TTS, or network calls.
"""

import numpy as np
import time
import sys
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "interactive_chat"))

from core.event_driven_core import (
    SystemState, Reducer, Event, EventType, ActionType
)


# ============================================================================
# TEST RESULTS TRACKING
# ============================================================================

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def pass_test(self, name, message=""):
        self.passed += 1
        self.tests.append(("✅", name, message))
        print(f"✅ {name}")
        if message:
            print(f"   {message}")
    
    def fail_test(self, name, error):
        self.failed += 1
        self.tests.append(("❌", name, str(error)))
        print(f"❌ {name}")
        print(f"   Error: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"📊 TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total:  {total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"{'='*70}\n")
        return self.failed == 0


results = TestResults()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def assert_equal(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"Expected {expected}, got {actual}. {msg}")

def assert_true(condition, msg=""):
    if not condition:
        raise AssertionError(f"Assertion failed: {msg}")

def assert_false(condition, msg=""):
    if condition:
        raise AssertionError(f"Assertion should be false: {msg}")

def assert_has_action(actions, action_type, msg=""):
    if not any(a.type == action_type for a in actions):
        raise AssertionError(f"Expected action {action_type.name} not found. {msg}")

def assert_no_action(actions, action_type, msg=""):
    if any(a.type == action_type for a in actions):
        raise AssertionError(f"Unexpected action {action_type.name} found. {msg}")


# ============================================================================
# LEVEL 1: UNIT TESTS - Pure Reducer Logic
# ============================================================================

def test_idle_to_speaking():
    """VAD_SPEECH_START transitions IDLE → SPEAKING"""
    try:
        state = SystemState(state_machine="IDLE")
        state, actions = Reducer.reduce(
            state,
            Event(EventType.VAD_SPEECH_START, timestamp=time.time())
        )
        
        assert_equal(state.state_machine, "SPEAKING")
        assert_true(state.is_human_speaking)
        assert_has_action(actions, ActionType.LOG)
        
        results.pass_test("IDLE → SPEAKING on VAD_SPEECH_START")
    except Exception as e:
        results.fail_test("IDLE → SPEAKING on VAD_SPEECH_START", e)


def test_speaking_to_pausing():
    """Silence triggers SPEAKING → PAUSING transition"""
    try:
        state = SystemState(
            state_machine="SPEAKING",
            is_human_speaking=False,
            last_voice_time=time.time() - 0.7,  # 700ms ago
            pause_ms=600
        )
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=time.time())
        )
        
        assert_equal(state.state_machine, "PAUSING")
        
        results.pass_test("SPEAKING → PAUSING on silence")
    except Exception as e:
        results.fail_test("SPEAKING → PAUSING on silence", e)


def test_pausing_to_idle():
    """Extended silence triggers PAUSING → IDLE with PROCESS_TURN"""
    try:
        state = SystemState(
            state_machine="PAUSING",
            is_human_speaking=False,
            last_voice_time=time.time(),
            end_ms=1200,
            authority="human"
        )
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.last_voice_time + 1.3)
        )
        
        assert_equal(state.state_machine, "IDLE")
        assert_has_action(actions, ActionType.PROCESS_TURN)
        
        results.pass_test("PAUSING → IDLE with PROCESS_TURN on extended silence")
    except Exception as e:
        results.fail_test("PAUSING → IDLE on extended silence", e)


def test_human_authority_always_listens():
    """Human authority keeps mic open during AI speech"""
    try:
        state = SystemState(
            authority="human",
            is_ai_speaking=True
        )
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={
                "frame": np.random.randn(512),
                "is_speech": True
            })
        )
        
        assert_true(len(state.turn_audio_buffer) > 0, "Audio should be buffered")
        
        results.pass_test("Human authority listens during AI speech")
    except Exception as e:
        results.fail_test("Human authority listens during AI speech", e)


def test_ai_authority_mutes_mic():
    """AI authority mutes mic while AI is speaking"""
    try:
        state = SystemState(
            authority="ai",
            is_ai_speaking=True
        )
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={
                "frame": np.random.randn(512),
                "is_speech": True
            })
        )
        
        assert_false(len(state.turn_audio_buffer) > 0, "Audio should NOT be buffered")
        assert_no_action(actions, ActionType.INTERRUPT_AI)
        
        results.pass_test("AI authority mutes mic during AI speech")
    except Exception as e:
        results.fail_test("AI authority mutes mic during AI speech", e)


def test_ai_authority_blocks_interruptions():
    """AI authority never allows interruptions"""
    try:
        state = SystemState(
            authority="ai",
            is_ai_speaking=True,
            interruption_sensitivity=1.0  # Max sensitivity
        )
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={"is_speech": True})
        )
        
        assert_no_action(actions, ActionType.INTERRUPT_AI)
        
        results.pass_test("AI authority blocks interruptions")
    except Exception as e:
        results.fail_test("AI authority blocks interruptions", e)


def test_human_authority_interrupts():
    """Human authority allows interruptions"""
    try:
        state = SystemState(
            authority="human",
            is_ai_speaking=True,
            interruption_sensitivity=0.5
        )
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={"is_speech": True})
        )
        
        assert_has_action(actions, ActionType.INTERRUPT_AI)
        assert_false(state.is_ai_speaking)
        assert_equal(len(state.ai_speech_queue), 0, "Queue should be cleared")
        
        results.pass_test("Human authority interrupts AI speech")
    except Exception as e:
        results.fail_test("Human authority interrupts AI speech", e)


def test_speak_sentence_action():
    """AI_SENTENCE_READY generates SPEAK_SENTENCE action"""
    try:
        state = SystemState()
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AI_SENTENCE_READY, payload={"text": "Hello there!"})
        )
        
        assert_true(state.is_ai_speaking)
        assert_has_action(actions, ActionType.SPEAK_SENTENCE)
        
        results.pass_test("AI_SENTENCE_READY generates SPEAK_SENTENCE")
    except Exception as e:
        results.fail_test("AI_SENTENCE_READY generates SPEAK_SENTENCE", e)


def test_interrupt_clears_queue():
    """Interruption clears AI speech queue"""
    try:
        state = SystemState(
            authority="human",
            is_ai_speaking=True,
            interruption_sensitivity=1.0
        )
        
        # Queue up multiple sentences
        state.ai_speech_queue = ["sentence 1", "sentence 2", "sentence 3"]
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.AUDIO_FRAME, payload={"is_speech": True})
        )
        
        assert_has_action(actions, ActionType.INTERRUPT_AI)
        assert_equal(len(state.ai_speech_queue), 0)
        assert_false(state.is_ai_speaking)
        
        results.pass_test("Interruption clears AI speech queue")
    except Exception as e:
        results.fail_test("Interruption clears AI speech queue", e)


# ============================================================================
# LEVEL 2: INTEGRATION TESTS - Event Sequences
# ============================================================================

def test_complete_user_turn():
    """Full flow: speak → silence → turn processing"""
    try:
        state = SystemState(authority="human", pause_ms=600, end_ms=1200)
        
        # User starts speaking
        start_time = time.time()
        state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_START, timestamp=start_time))
        assert_equal(state.state_machine, "SPEAKING")
        
        # Simulate some audio frames
        state, _ = Reducer.reduce(state, Event(
            EventType.AUDIO_FRAME,
            payload={"frame": np.zeros(512), "is_speech": True},
            timestamp=start_time + 0.05
        ))
        
        # User stops speaking
        state.last_voice_time = start_time + 0.1
        state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_STOP, timestamp=start_time + 0.1))
        
        # First TICK: should transition SPEAKING -> PAUSING (after pause_ms)
        state, _ = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.last_voice_time + 0.7)
        )
        assert_equal(state.state_machine, "PAUSING")
        
        # Second TICK: should transition PAUSING -> IDLE (after end_ms) with PROCESS_TURN
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.last_voice_time + 1.5)
        )
        
        # Should have transitioned to IDLE and generated PROCESS_TURN
        assert_equal(state.state_machine, "IDLE")
        has_process = any(a.type == ActionType.PROCESS_TURN for a in actions)
        assert_true(has_process, "PROCESS_TURN not generated")
        
        results.pass_test("Complete user turn flow")
    except Exception as e:
        results.fail_test("Complete user turn flow", e)


def test_interrupt_during_ai_response():
    """User interrupts AI response"""
    try:
        state = SystemState(authority="human", interruption_sensitivity=0.5)
        
        # AI starts responding
        state, _ = Reducer.reduce(state, Event(
            EventType.AI_SENTENCE_READY,
            payload={"text": "The quick brown fox..."}
        ))
        assert_true(state.is_ai_speaking)
        
        # User interrupts
        state, actions = Reducer.reduce(state, Event(
            EventType.AUDIO_FRAME,
            payload={"is_speech": True}
        ))
        
        assert_has_action(actions, ActionType.INTERRUPT_AI)
        assert_false(state.is_ai_speaking)
        
        results.pass_test("Interrupt during AI response")
    except Exception as e:
        results.fail_test("Interrupt during AI response", e)


# ============================================================================
# LEVEL 3: PROFILE-SPECIFIC TESTS
# ============================================================================

def test_ielts_instructor_ai_authority():
    """IELTS Instructor profile: AI controls flow"""
    try:
        state = SystemState(
            authority="ai",
            interruption_sensitivity=0.0,
            safety_timeout_ms=2500
        )
        
        # Student tries to interrupt
        state.is_ai_speaking = True
        
        state, actions = Reducer.reduce(state, Event(
            EventType.AUDIO_FRAME,
            payload={"is_speech": True}
        ))
        
        assert_no_action(actions, ActionType.INTERRUPT_AI)
        
        results.pass_test("IELTS Instructor enforces AI authority")
    except Exception as e:
        results.fail_test("IELTS Instructor enforces AI authority", e)


def test_negotiator_human_authority():
    """Negotiator profile: User can interrupt"""
    try:
        state = SystemState(
            authority="human",
            interruption_sensitivity=0.8
        )
        
        state.is_ai_speaking = True
        
        state, actions = Reducer.reduce(state, Event(
            EventType.AUDIO_FRAME,
            payload={"is_speech": True}
        ))
        
        assert_has_action(actions, ActionType.INTERRUPT_AI)
        
        results.pass_test("Negotiator allows human interruption")
    except Exception as e:
        results.fail_test("Negotiator allows human interruption", e)


# ============================================================================
# LEVEL 4: EDGE CASES
# ============================================================================

def test_safety_timeout_force_ends():
    """Safety timeout forces turn end"""
    try:
        state = SystemState(
            authority="default",
            state_machine="PAUSING",
            last_voice_time=time.time(),
            safety_timeout_ms=2500
        )
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.last_voice_time + 3.0)
        )
        
        assert_true(state.force_ended)
        assert_has_action(actions, ActionType.PROCESS_TURN)
        
        results.pass_test("Safety timeout force-ends turn")
    except Exception as e:
        results.fail_test("Safety timeout force-ends turn", e)


def test_human_speaking_limit():
    """Human speaking limit triggers acknowledgment"""
    try:
        state = SystemState(
            human_speaking_limit_sec=30,
            turn_start_time=time.time()
        )
        
        state, actions = Reducer.reduce(
            state,
            Event(EventType.TICK, timestamp=state.turn_start_time + 35.0)
        )
        
        assert_has_action(actions, ActionType.PLAY_ACK)
        assert_true(state.human_speaking_limit_ack_sent)
        
        results.pass_test("Human speaking limit triggers acknowledgment")
    except Exception as e:
        results.fail_test("Human speaking limit triggers acknowledgment", e)


def test_rapid_state_transitions():
    """Quick speak → pause → speak"""
    try:
        state = SystemState()
        
        # Speak
        state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_START))
        assert_equal(state.state_machine, "SPEAKING")
        
        # Pause
        state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_STOP))
        
        # Resume quickly
        state, _ = Reducer.reduce(
            state,
            Event(EventType.VAD_SPEECH_START, timestamp=time.time() + 0.3)
        )
        
        assert_equal(state.state_machine, "SPEAKING")
        
        results.pass_test("Rapid state transitions")
    except Exception as e:
        results.fail_test("Rapid state transitions", e)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all headless tests"""
    print("\n" + "="*70)
    print("🧪 HEADLESS UNIT TEST SUITE")
    print("="*70 + "\n")
    
    print("📍 LEVEL 1: State Transitions")
    print("-" * 70)
    test_idle_to_speaking()
    test_speaking_to_pausing()
    test_pausing_to_idle()
    
    print("\n📍 LEVEL 1: Authority Modes")
    print("-" * 70)
    test_human_authority_always_listens()
    test_ai_authority_mutes_mic()
    test_ai_authority_blocks_interruptions()
    test_human_authority_interrupts()
    
    print("\n📍 LEVEL 1: Action Generation")
    print("-" * 70)
    test_speak_sentence_action()
    test_interrupt_clears_queue()
    
    print("\n📍 LEVEL 2: Integration Tests")
    print("-" * 70)
    test_complete_user_turn()
    test_interrupt_during_ai_response()
    
    print("\n📍 LEVEL 3: Profile-Specific")
    print("-" * 70)
    test_ielts_instructor_ai_authority()
    test_negotiator_human_authority()
    
    print("\n📍 LEVEL 4: Edge Cases")
    print("-" * 70)
    test_safety_timeout_force_ends()
    test_human_speaking_limit()
    test_rapid_state_transitions()
    
    return results.summary()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
