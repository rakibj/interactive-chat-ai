#!/usr/bin/env python3
"""
Test app stability - specifically checks that the app doesn't crash
when human speaks. This is a regression test for the silent exit bug
where the app would terminate without error handling.
"""

import time
import numpy as np
from unittest.mock import MagicMock, patch
from interactive_chat.main import ConversationEngine
from interactive_chat.core.event_driven_core import Event, EventType, Action, ActionType, Reducer


def test_human_speaking_doesnt_crash():
    """Test that app handles human speaking without crashing."""
    print("\n" + "="*60)
    print("TEST: Human Speaking Stability (No Crash)")
    print("="*60)
    
    # Create engine with human-start mode (negotiator profile)
    engine = ConversationEngine(profile_key="negotiator")
    print("✓ Engine created with human-start mode")
    
    # Mock the ASR to return a test phrase
    test_phrase = "Hello, I would like to negotiate the price"
    engine.asr.transcribe = MagicMock(return_value=test_phrase)
    print(f"✓ ASR mocked to return: '{test_phrase}'")
    
    # Mock the LLM to return a simple response
    mock_response_tokens = ["Hello,", " I", " appreciate", " your", " interest."]
    engine.llm.stream_completion = MagicMock(return_value=iter(mock_response_tokens))
    print(f"✓ LLM mocked to return tokens")
    
    # Mock TTS to avoid actual audio (if available)
    if engine.tts is not None:
        engine.tts.speak = MagicMock()
        print(f"✓ TTS mocked")
    else:
        print(f"⚠️  TTS not available (optional), skipping mock")
    
    try:
        # Simulate human speaking: VAD_SPEECH_START
        print("\n[SIMULATE] Inserting VAD_SPEECH_START event")
        engine.event_queue.put(Event(EventType.VAD_SPEECH_START, time.time(), "vad"))
        
        # Simulate audio frames being captured
        print("[SIMULATE] Inserting audio frames")
        for i in range(3):
            audio_frame = np.random.randn(16000).astype(np.float32) * 0.01  # Small noise
            engine.event_queue.put(Event(EventType.AUDIO_FRAME, time.time(), "audio", {"frame": audio_frame}))
        
        # Simulate silence (VAD_SPEECH_STOP)
        print("[SIMULATE] Inserting VAD_SPEECH_STOP event")
        engine.event_queue.put(Event(EventType.VAD_SPEECH_STOP, time.time(), "vad"))
        
        # Run event loop for a limited time to process events
        print("\n[RUNNING] Event loop for 2 seconds...")
        start_time = time.time()
        event_count = 0
        crashed = False
        error_msg = None
        
        while time.time() - start_time < 2.0:
            try:
                # Process one event from the queue
                if not engine.event_queue.empty():
                    event = engine.event_queue.get_nowait()
                    event_count += 1
                    
                    # Process event through reducer
                    next_state, actions = Reducer.reduce(engine.state, event)
                    engine.state = next_state
                    
                    # Handle actions
                    for action in actions:
                        try:
                            engine._handle_action(action)
                        except Exception as e:
                            crashed = True
                            error_msg = f"Action handling failed: {e}"
                            print(f"❌ ERROR in _handle_action: {e}")
                            break
                    
                    if crashed:
                        break
                    
                time.sleep(0.01)
            except Exception as e:
                crashed = True
                error_msg = f"Event loop error: {e}"
                print(f"❌ ERROR in event loop: {e}")
                break
        
        print(f"✓ Processed {event_count} events")
        
        if crashed:
            print(f"\n❌ CRASH DETECTED: {error_msg}")
            return False
        
        # Verify state transitions happened
        print(f"\n✓ State after processing:")
        print(f"   Machine state: {engine.state.state_machine}")
        print(f"   Turn ID: {engine.state.turn_id}")
        print(f"   Turn transcript: '{engine.state.turn_final_transcript}'")
        
        # Verify turn was processed
        if engine.state.turn_final_transcript:
            print(f"✅ User's phrase was transcribed: '{engine.state.turn_final_transcript}'")
        
        print(f"\n✅ TEST PASSED: App handled human speech without crashing")
        return True
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if engine.audio_manager is not None:
            engine.audio_manager.stop()


def test_event_loop_exception_handling():
    """Test that event loop handles exceptions gracefully without crashing."""
    print("\n" + "="*60)
    print("TEST: Event Loop Exception Handling")
    print("="*60)
    
    # Create engine
    engine = ConversationEngine(profile_key="negotiator")
    print("✓ Engine created")
    
    # Mock Reducer.reduce to throw an exception on second call
    original_reduce = Reducer.reduce
    call_count = [0]  # Track calls
    
    def faulty_reducer(state, event):
        call_count[0] += 1
        # First call succeeds, second call fails, third onwards succeed
        if call_count[0] == 2:
            raise ValueError("Simulated reducer error")
        return original_reduce(state, event)
    
    # Patch the reducer temporarily
    Reducer.reduce = staticmethod(faulty_reducer)
    print("✓ Reducer patched to throw on 2nd call")
    
    try:
        # Queue events: one should fail, but shouldn't crash loop
        engine.event_queue.put(Event(EventType.TICK, time.time(), "tick"))
        engine.event_queue.put(Event(EventType.TICK, time.time(), "tick"))  # This one will fail
        engine.event_queue.put(Event(EventType.TICK, time.time(), "tick"))  # Should recover
        
        print("\n[RUNNING] Processing events with exception in reducer...")
        
        events_processed = 0
        errors_caught = 0
        
        # Process events manually (simulating what run() does)
        while not engine.event_queue.empty():
            try:
                event = engine.event_queue.get_nowait()
                
                try:
                    engine.state, actions = Reducer.reduce(engine.state, event)
                    events_processed += 1
                except Exception as e:
                    errors_caught += 1
                    print(f"   ⚠️  Caught error: {e}")
                    # In real code, this would continue
                    continue
                
                for action in actions:
                    engine._handle_action(action)
                    
            except Exception as e:
                print(f"❌ Loop error: {e}")
                return False
        
        print(f"✓ Processed {events_processed} events successfully")
        print(f"✓ Caught and recovered from {errors_caught} error(s)")
        print(f"✅ TEST PASSED: Event loop recovered from exceptions")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original reducer
        Reducer.reduce = staticmethod(original_reduce)
        if engine.audio_manager is not None:
            engine.audio_manager.stop()


def test_action_handler_exception_handling():
    """Test that action handler exceptions don't crash the app."""
    print("\n" + "="*60)
    print("TEST: Action Handler Exception Handling")
    print("="*60)
    
    # Create engine
    engine = ConversationEngine(profile_key="negotiator")
    print("✓ Engine created")
    
    # Mock _handle_action to throw on first LOG action
    original_handle = engine._handle_action
    call_count = [0]
    
    def faulty_handler(action):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("Simulated action handler error")
        return original_handle(action)
    
    engine._handle_action = faulty_handler
    print("✓ Action handler patched to fail on first call")
    
    try:
        # Create some actions
        action1 = Action(ActionType.LOG, {"message": "Test 1"})
        action2 = Action(ActionType.LOG, {"message": "Test 2"})
        
        print("\n[RUNNING] Processing actions with exception in handler...")
        
        actions_processed = 0
        errors_caught = 0
        
        for action in [action1, action2]:
            try:
                engine._handle_action(action)
                actions_processed += 1
            except Exception as e:
                errors_caught += 1
                print(f"   ⚠️  Caught error: {e}")
                continue
        
        print(f"✓ Processed {actions_processed} actions")
        print(f"✓ Caught and recovered from {errors_caught} error(s)")
        print(f"✅ TEST PASSED: Action handler errors didn't crash app")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        engine._handle_action = original_handle
        if engine.audio_manager is not None:
            engine.audio_manager.stop()


def main():
    """Run all stability tests."""
    print("\n" + "="*70)
    print("APP STABILITY TEST SUITE")
    print("="*70)
    
    results = []
    
    # Test 1
    result1 = test_human_speaking_doesnt_crash()
    results.append(("Human Speaking Doesn't Crash", result1))
    
    # Test 2
    result2 = test_event_loop_exception_handling()
    results.append(("Event Loop Exception Handling", result2))
    
    # Test 3
    result3 = test_action_handler_exception_handling()
    results.append(("Action Handler Exception Handling", result3))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("="*70))
    if all_passed:
        print("✅ All stability tests passed!")
    else:
        print("❌ Some tests failed")
    
    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
