#!/usr/bin/env python3
"""Quick test to verify app initialization"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    print("✅ Testing imports...")
    from interactive_chat.main import ConversationEngine
    from interactive_chat.config import get_profile_settings
    print("✅ Imports successful")
    
    print("\n✅ Creating ConversationEngine...")
    engine = ConversationEngine(profile_key="negotiator")
    print(f"✅ Engine created: {engine.profile_settings['name']}")
    
    print("\n✅ All systems initialized successfully!")
    print(f"   Profile: {engine.profile_settings['name']}")
    print(f"   Authority: {engine.state.authority}")
    print(f"   Status: Ready to run")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
