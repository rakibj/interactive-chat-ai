#!/usr/bin/env python3
"""
Debug script to trace the AI greeting pipeline without needing OpenAI API.
Uses mock LLM to simulate speech generation.
"""
import sys
import os
import time
import threading
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Test AI greeting pipeline with mock LLM."""
    print("\n" + "="*70)
    print("AI GREETING PIPELINE DEBUG - WITH MOCK LLM")
    print("="*70)
    
    from interactive_chat.main import ConversationEngine
    from interactive_chat.server import set_engine
    
    # Create engine
    print("\n[1] Creating engine...")
    engine = ConversationEngine(profile_key="ielts_full_exam")
    set_engine(engine)
    
    # Mock the LLM to simulate speech output
    print("\n[2] Installing mock LLM...")
    
    def mock_stream_completion(**kwargs):
        """Yield fake AI speech tokens."""
        messages = kwargs.get("messages", [])
        print(f"   LLM called with {len(messages)} messages")
        
        # Return a fake greeting
        greeting = "Hello, welcome to the IELTS Speaking Test. My name is the examiner. What is your name?"
        for char in greeting:
            yield char
            time.sleep(0.01)  # Mimic streaming delay
    
    engine.llm = Mock()
    engine.llm.stream_completion = mock_stream_completion
    
    print("   ✅ Mock LLM installed")
    print(f"   Will say: 'Hello, welcome to the IELTS Speaking Test...'")
    
    # Start engine
    print("\n[3] Starting engine...")
    engine_thread = threading.Thread(target=engine.run, daemon=False)
    engine_thread.start()
    
    # Wait for AI greeting
    print("\n[4] Waiting for TTS output (20 second timeout)...")
    print("   Look for 'TTS: Speaking' messages below:")
    print("   " + "-"*60)
    
    start = time.time()
    while time.time() - start < 20:
        if len(engine.conversation_memory.get_messages()) > 0:
            print("   " + "-"*60)
            print("\n   ✅ AI greeting completed!")
            break
        time.sleep(0.1)
    else:
        print("   " + "-"*60)
        print("\n   ⚠️  Timeout - check logs above for errors")
    
    # Show final state
    print("\n[5] Final State:")
    state = engine.state
    print(f"    is_ai_speaking: {state.is_ai_speaking}")
    print(f"    current_speaker: {state.current_speaker}")
    print(f"    Messages: {len(engine.conversation_memory.get_messages())}")
    print(f"    Turn ID: {state.turn_id}")
    
    messages = engine.conversation_memory.get_messages()
    if messages:
        for msg in messages:
            print(f"      {msg['role']}: {msg['content'][:80]}...")
    
    # Shutdown
    print("\n[6] Shutting down...")
    engine._request_shutdown()
    engine_thread.join(timeout=5)
    
    print("\n" + "="*70)
    print("DEBUG COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
