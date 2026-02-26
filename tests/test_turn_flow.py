#!/usr/bin/env python3
"""
Test script to trace turn flow with AI authority.
Simulates API calls to understand what's happening.
"""
import sys
import os
import time
import threading
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Test turn flow."""
    print("\n" + "="*70)
    print("TURN FLOW TEST - AI Authority Mode")
    print("="*70)
    
    from interactive_chat.main import ConversationEngine
    from interactive_chat.server import set_engine
    
    # Create engine with IELTS profile (AI authority, start="ai")
    print("\n[1] Creating ConversationEngine with ielts_full_exam profile...")
    engine = ConversationEngine(profile_key="ielts_full_exam")
    set_engine(engine)
    
    # Check initial state
    state = engine.state
    print(f"\n[2] Initial State:")
    print(f"    - Authority: {state.authority}")
    print(f"    - Start mode: {engine.profile_settings.get('start', 'unknown')}")
    print(f"    - State machine: {state.state_machine}")
    print(f"    - Is AI speaking: {state.is_ai_speaking}")
    print(f"    - Current speaker: {getattr(state, 'current_speaker', 'N/A')}")
    print(f"    - Human speaking: {state.is_human_speaking}")
    
    # Start engine in background
    print(f"\n[3] Starting engine in background thread...")
    engine_thread = threading.Thread(target=engine.run, daemon=False)
    engine_thread.start()
    
    # Wait for initial AI greeting
    print(f"\n[4] Waiting for AI greeting (10 seconds timeout)...")
    start_wait = time.time()
    while time.time() - start_wait < 10:
        # Poll state every 100ms
        state = engine.state
        
        # Check if state changed
        if len(engine.conversation_memory.get_messages()) > 0:
            messages = engine.conversation_memory.get_messages()
            print(f"\n    ✅ AI has generated response!")
            print(f"    - Messages in memory: {len(messages)}")
            for i, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]  # First 100 chars
                print(f"      [{i}] {role}: {content}...")
            break
        
        time.sleep(0.1)
    else:
        print(f"\n    ⚠️  Timeout waiting for AI greeting")
        state = engine.state
        print(f"    - Current speaker: {getattr(state, 'current_speaker', 'N/A')}")
        print(f"    - State machine: {state.state_machine}")
        print(f"    - Messages: {len(engine.conversation_memory.get_messages())}")
    
    # Check menu after greeting
    print(f"\n[5] State after greeting:")
    state = engine.state
    print(f"    - State machine: {state.state_machine}")
    print(f"    - Is AI speaking: {state.is_ai_speaking}")
    print(f"    - Turn ID: {state.turn_id}")
    print(f"    - Phase: {state.active_phase_id}")
    
    # Simulate human speaking
    print(f"\n[6] Simulating human input via event...")
    from interactive_chat.core.event_driven_core import Event, EventType
    
    # Override gating to allow audio processing in test
    engine._audio_producer_override_gating = True
    print(f"    ✅ Audio producer gating override enabled")
    
    # Add a user message directly to simulate speech recognition
    engine.conversation_memory.add_message("user", "My name is John.")
    print(f"    ✅ Added user message to memory")
    
    # Manually trigger turn processing to simulate what would normally happen
    print(f"\n[7] Checking if PROCESS_TURN would be triggered...")
    print(f"    - Queue depth: {engine.event_queue.qsize()}")
    print(f"    - Turn audio buffer size: {len(state.turn_audio_buffer)}")
    
    print(f"\n[8] Waiting for AI response (10 seconds timeout)...")
    start_wait = time.time()
    initial_msg_count = len(engine.conversation_memory.get_messages())
    
    while time.time() - start_wait < 10:
        messages = engine.conversation_memory.get_messages()
        if len(messages) > initial_msg_count:
            print(f"\n    ✅ AI has responded!")
            for msg in messages[initial_msg_count:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]
                print(f"      {role}: {content}...")
            break
        time.sleep(0.1)
    else:
        print(f"\n    ⚠️  Timeout waiting for AI response")
    
    # Final state
    print(f"\n[9] Final State:")
    state = engine.state
    print(f"    - Messages in memory: {len(engine.conversation_memory.get_messages())}")
    print(f"    - Turn ID: {state.turn_id}")
    print(f"    - State machine: {state.state_machine}")
    print(f"    - Current speaker: {getattr(state, 'current_speaker', 'N/A')}")
    
    # Shutdown
    print(f"\n[10] Shutting down...")
    engine._request_shutdown()
    engine_thread.join(timeout=5)
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
