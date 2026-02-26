#!/usr/bin/env python3
"""
Test script to verify turn completion flow by manually injecting VAD events.
This bypasses the VAD detection layer to test the reducer and turn processing logic.
"""
import sys
import os
import time
import threading
import numpy as np
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Test turn completion with manual VAD events."""
    print("\n" + "="*70)
    print("MANUAL VAD TEST - Turn Completion Flow")
    print("="*70)
    
    from interactive_chat.main import ConversationEngine
    from interactive_chat.server import set_engine
    from interactive_chat.core.event_driven_core import Event, EventType
    
    # Create engine
    print("\n[1] Creating engine with ielts_full_exam...")
    engine = ConversationEngine(profile_key="ielts_full_exam")
    set_engine(engine)
    
    # Start engine
    print("\n[2] Starting engine...")
    engine_thread = threading.Thread(target=engine.run, daemon=False)
    engine_thread.start()
    
    # Wait for AI greeting
    print("\n[3] Waiting for AI greeting...")
    time.sleep(5)  # Give time for AI to greet
    
    messages_before = len(engine.conversation_memory.get_messages())
    print(f"    Messages in memory: {messages_before}")
    
    # Manually inject VAD and audio to simulate human response
    print("\n[4] Simulating human speech by injecting VAD events...")
    
    # Inject fake audio frames to turn_audio_buffer
    fake_audio = np.ones(512, dtype=np.float32) * 0.1
    for i in range(10):  # 10 frames = ~320ms of audio
        engine.state.turn_audio_buffer.append(fake_audio)
    
    time.sleep(0.1)
    
    # Trigger VAD_SPEECH_START
    print(f"⬆️ Injecting VAD_SPEECH_START...")
    engine.event_queue.put(Event(EventType.VAD_SPEECH_START, time.time(), "test"))
    time.sleep(0.5)
    
    # Trigger VAD_SPEECH_STOP (after pause_ms + some buffer)
    print(f"⬇️ Injecting VAD_SPEECH_STOP...")
    engine.event_queue.put(Event(EventType.VAD_SPEECH_STOP, time.time(), "test"))
    
    # Wait for turn processing
    print(f"\n[5] Waiting for PROCESS_TURN action (10 seconds timeout)...")
    start_wait = time.time()
    messages_before = len(engine.conversation_memory.get_messages())
    
    while time.time() - start_wait < 10:
        messages = engine.conversation_memory.get_messages()
        if len(messages) > messages_before:
            new_messages = messages[messages_before:]
            print(f"\n    ✅ New response received!")
            for msg in new_messages:
                role = msg.get("role")
                content = msg.get("content", "")[:100]
                print(f"       {role}: {content}...")
            break
        time.sleep(0.1)
    else:
        print(f"\n    ⚠️  No response received (timeout)")
    
    print(f"\n[6] Final State:")
    state = engine.state
    print(f"    - Total messages: {len(engine.conversation_memory.get_messages())}")
    print(f"    - Turn ID: {state.turn_id}")
    print(f"    - State machine: {state.state_machine}")
    print(f"    - Last speaker: {getattr(state, 'current_speaker', 'N/A')}")
    
    # Shutdown
    print(f"\n[7] Shutting down...")
    engine._request_shutdown()
    engine_thread.join(timeout=5)
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
