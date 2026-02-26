#!/usr/bin/env python3
"""Debug version of run_html_app.py with detailed logging."""

import sys
import os

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

print("[DEBUG-1] Script started", flush=True)

import time
import threading
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("[DEBUG-2] Path setup complete", flush=True)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Interactive Chat AI - HTML/CSS Web Demo (Debug)")
    parser.add_argument("--profile", default="ielts_full_exam")
    args = parser.parse_args()
    
    print(f"\n[DEBUG-3] Starting with profile: {args.profile}", flush=True)
    
    try:
        print("[DEBUG-4] Attempting imports...", flush=True)
        from interactive_chat.config import PHASE_PROFILES, INSTRUCTION_PROFILES
        print("[DEBUG-5] Config imported", flush=True)
        
        from interactive_chat.main import ConversationEngine
        print("[DEBUG-6] ConversationEngine imported", flush=True)
        
        print(f"[DEBUG-7] Creating engine...", flush=True)
        engine = ConversationEngine(profile_key=args.profile)
        print(f"[DEBUG-8] ✅ Engine created successfully!", flush=True)
        
        print(f"[DEBUG-9] Engine properties:", flush=True)
        print(f"  - audio_manager: {type(engine.audio_manager).__name__ if engine.audio_manager else 'None'}", flush=True)
        print(f"  - asr: {type(engine.asr).__name__ if engine.asr else 'None'}", flush=True)
        print(f"  - llm: {type(engine.llm).__name__ if engine.llm else 'None'}", flush=True)
        print(f"  - tts: {type(engine.tts).__name__ if engine.tts else 'None'}", flush=True)
        
        print(f"\n[DEBUG-10] Engine.run() is about to be called...", flush=True)
        print(f"[DEBUG-11] This will block in the event loop", flush=True)
        
        engine.run()
        
    except KeyboardInterrupt:
        print(f"\n[DEBUG] Interrupted", flush=True)
        if 'engine' in locals():
            engine._request_shutdown()
        sys.exit(0)
    except Exception as e:
        print(f"\n[DEBUG-ERROR] {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
