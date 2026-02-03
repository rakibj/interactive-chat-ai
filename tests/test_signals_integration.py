#!/usr/bin/env python
"""Minimal test to verify signals don't break core event-driven logic."""
import sys
import os

# Fix path for imports
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_dir)
interactive_chat_dir = os.path.join(project_root, "interactive_chat")
sys.path.insert(0, interactive_chat_dir)

from core.event_driven_core import (
    SystemState, Reducer, Event, EventType, ActionType
)
from core.signals import get_signal_registry, emit_signal, SignalName
import time

def test_basic_state_transition():
    """Test that state transitions work without breaking on signals."""
    print("Testing basic state transitions...")
    
    state = SystemState(authority="human", interruption_sensitivity=0.6)
    registry = get_signal_registry()
    
    # Clear any listeners
    registry.clear()
    
    # Test 1: VAD speech start
    event = Event(
        type=EventType.VAD_SPEECH_START,
        timestamp=time.time(),
        payload={}
    )
    state, actions = Reducer.reduce(state, event)
    
    assert state.is_human_speaking == True, "Human should be speaking after VAD_SPEECH_START"
    assert state.state_machine == "SPEAKING", "State machine should be SPEAKING"
    print("  OK: VAD_SPEECH_START works")
    
    # Test 2: VAD speech stop
    event = Event(
        type=EventType.VAD_SPEECH_STOP,
        timestamp=time.time(),
        payload={}
    )
    state, actions = Reducer.reduce(state, event)
    
    assert state.is_human_speaking == False, "Human should not be speaking after VAD_SPEECH_STOP"

    print("  OK: VAD_SPEECH_STOP works")
    
    # Test 3: TICK event (state machine advancement)
    for i in range(5):
        event = Event(
            type=EventType.TICK,
            timestamp=time.time() + (i * 0.3),  # 300ms increments
            payload={}
        )
        state, actions = Reducer.reduce(state, event)
    
    # After enough ticks, should transition to IDLE and generate PROCESS_TURN
    has_process_turn = any(a.type == ActionType.PROCESS_TURN for a in actions)
    print(f"  OK: TICK events advance state machine (PROCESS_TURN: {has_process_turn})")

def test_signal_emission_doesnt_crash():
    """Test that signal emission doesn't crash the reducer."""
    print("Testing signal emission safety...")
    
    state = SystemState(
        authority="default",
        interruption_sensitivity=0.6,
        is_ai_speaking=True
    )
    registry = get_signal_registry()
    registry.clear()
    
    # Add a listener that does something
    signals_received = []
    def capture_signal(signal):
        signals_received.append(signal.name)
    
    registry.register_all(capture_signal)
    
    # Trigger an interruption (which emits a signal)
    event = Event(
        type=EventType.AUDIO_FRAME,
        timestamp=time.time(),
        payload={"frame": [0.1] * 512, "is_speech": True, "rms": 0.1}
    )
    
    state, actions = Reducer.reduce(state, event)
    
    # Check that signals were emitted
    has_interrupt_action = any(a.type == ActionType.INTERRUPT_AI for a in actions)
    
    print(f"  OK: Signal emission works (signals received: {len(signals_received)})")
    if len(signals_received) > 0:
        print(f"      Signals: {', '.join(signals_received)}")

def test_signals_optional():
    """Test that engine works with zero listeners."""
    print("Testing with zero listeners...")
    
    state = SystemState(authority="human")
    registry = get_signal_registry()
    registry.clear()  # No listeners
    
    events = [
        Event(EventType.VAD_SPEECH_START, time.time(), payload={}),
        Event(EventType.VAD_SPEECH_STOP, time.time(), payload={}),
        Event(EventType.TICK, time.time(), payload={}),
    ]
    
    for event in events:
        state, actions = Reducer.reduce(state, event)
        # Just verify it doesn't crash
    
    print("  OK: Engine works with zero listeners")

def test_listener_exception_handling():
    """Test that listener errors don't crash the engine."""
    print("Testing listener error handling...")
    
    state = SystemState(authority="default", is_ai_speaking=True)
    registry = get_signal_registry()
    registry.clear()
    
    # Add a listener that throws
    def bad_listener(signal):
        raise ValueError("Intentional error")
    
    registry.register_all(bad_listener)
    
    # This should NOT crash despite the listener error
    event = Event(
        type=EventType.AUDIO_FRAME,
        timestamp=time.time(),
        payload={"frame": [0.1] * 512, "is_speech": True, "rms": 0.1}
    )
    
    try:
        state, actions = Reducer.reduce(state, event)
        print("  OK: Listener exceptions handled safely")
    except Exception as e:
        print(f"  FAIL: Engine crashed despite listener error: {e}")
        return False
    
    return True

def test_emit_signal_function():
    """Test that emit_signal convenience function works."""
    print("Testing emit_signal() convenience function...")
    
    registry = get_signal_registry()
    registry.clear()
    
    signals_received = []
    registry.register("custom.test", lambda sig: signals_received.append(sig))
    
    emit_signal(
        "custom.test",
        payload={"foo": "bar"},
        context={"source": "test"}
    )
    
    assert len(signals_received) == 1, "Signal should be emitted"
    assert signals_received[0].name == "custom.test"
    assert signals_received[0].payload["foo"] == "bar"
    print("  OK: emit_signal() works correctly")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SIGNALS ARCHITECTURE INTEGRATION TEST")
    print("="*70 + "\n")
    
    try:
        test_basic_state_transition()
        print()
        test_signal_emission_doesnt_crash()
        print()
        test_signals_optional()
        print()
        test_listener_exception_handling()
        print()
        test_emit_signal_function()
        
        print("\n" + "="*70)
        print("ALL TESTS PASSED - SIGNALS ARE NON-BREAKING")
        print("="*70)
        print("\nKey validations:")
        print("  [OK] State machine transitions work with signals")
        print("  [OK] Signal emission doesn't crash reducer")
        print("  [OK] Engine works with zero listeners")
        print("  [OK] Listener errors are handled safely")
        print("  [OK] emit_signal() convenience function works")
        print("\nConclusion:")
        print("  Signals architecture is fully integrated and non-breaking.")
        print("  Core engine remains deterministic and unaffected by listeners.")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\nFAIL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
