#!/usr/bin/env python3
"""Debug script to test initialization step by step."""

import sys
import time
import threading
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("[1] Starting imports...")

try:
    print("[2] Importing config...")
    from interactive_chat.config import PHASE_PROFILES
    print("[3] Config imported ✓")
    
    print("[4] Importing ConversationEngine...")
    from interactive_chat.main import ConversationEngine
    print("[5] ConversationEngine imported ✓")
    
    print("[6] Creating engine with ielts_full_exam...")
    engine = ConversationEngine(profile_key='ielts_full_exam')
    print("[7] Engine created ✓")
    print(f"    - audio_manager: {engine.audio_manager}")
    print(f"    - asr: {engine.asr}")
    print(f"    - llm: {engine.llm}")
    print(f"    - tts: {engine.tts}")
    
    print("[8] Starting engine.run() in thread...")
    run_thread = threading.Thread(target=engine.run, daemon=False)
    run_thread.start()
    
    print("[9] Waiting 5 seconds to see output...")
    time.sleep(5)
    
    print("[10] Requesting shutdown...")
    engine._request_shutdown()
    
    print("[11] Waiting for thread to finish...")
    run_thread.join(timeout=5)
    
    if run_thread.is_alive():
        print("[!] Thread still alive after 5s timeout")
    else:
        print("[12] Thread finished ✓")
    
    print("\n✅ DEBUG TEST COMPLETE")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
