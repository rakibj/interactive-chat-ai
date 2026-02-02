#!/usr/bin/env python3
"""
Automated Voice Testing Script
------------------------------
Iterates through all configured InstructionProfiles and:
1. Generates a conversation turn (Greeting or Response).
2. Uses the REAL TTS system to speak the text.
3. Allows the user to verify "voices" and "personas" without a mic.
"""
import os
import sys
import time
import argparse
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
# Also include the package directory purely for 'config' imports resolving
sys.path.insert(0, os.path.join(project_root, "interactive_chat"))

from interactive_chat.config import (
    INSTRUCTION_PROFILES,
    InstructionProfile,
    get_system_prompt,
)
# Fix imports to verify specific submodules and avoid ASR dependency
from interactive_chat.interfaces.llm import get_llm
from interactive_chat.interfaces.tts import get_tts

def test_profile(profile_key: str, profile: InstructionProfile, llm):
    """Test a single profile."""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING PROFILE: {profile.name} ({profile_key})")
    print(f"🗣️  Voice: {profile.voice}")
    print(f"🤖 Authority: {profile.authority}")
    print(f"{'='*60}")
    
    # Instantiate TTS specifically for this profile's voice
    try:
        tts = get_tts(voice_name=profile.voice)
    except Exception as e:
        print(f"❌ Failed to load TTS for voice {profile.voice}: {e}")
        return

    system_prompt = get_system_prompt(profile_key)
    
    messages = []
    
    if profile.start == "ai":
        print(f"🎬 Scenario: AI Starts (Greeting)")
        messages = [{"role": "system", "content": system_prompt}]
        # We rely on implicit greeting generation or prompt the LLM to start
        # In main.py, _generate_ai_greeting uses just the system prompt.
        # But stream_completion needs messages.
        # If we send just system prompt, LLM usually continues or greets.
    else:
        print(f"🎬 Scenario: Human Starts (Mock Input)")
        user_msg = "Hello, who are you and what are we doing?"
        print(f"💬 Mock User: '{user_msg}'")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]

    print(f"🧠 Generating response...")
    full_text = ""
    
    try:
        # Stream from LLM
        for token in llm.stream_completion(
            messages=messages,
            max_tokens=profile.max_tokens,
            temperature=profile.temperature
        ):
            print(token, end="", flush=True)
            full_text += token
        print("\n")
        
        if full_text.strip():
            print(f"🔊 Speaking...")
            tts.speak(full_text)
            print("✅ Done.")
        else:
            print("❌ No response generated.")

    except Exception as e:
        print(f"❌ Error during generation/speech: {e}")

    time.sleep(1.0)

def main():
    parser = argparse.ArgumentParser(description="Test voices for profiles.")
    parser.add_argument("--profile", type=str, help="Specific profile key to test (optional)")
    args = parser.parse_args()

    print("🔌 Initializing LLM interface...")
    try:
        llm = get_llm()
    except Exception as e:
        print(f"❌ Failed to initialize LLM: {e}")
        return

    profiles_to_test = INSTRUCTION_PROFILES.items()
    if args.profile:
        if args.profile in INSTRUCTION_PROFILES:
            profiles_to_test = [(args.profile, INSTRUCTION_PROFILES[args.profile])]
        else:
            print(f"❌ Profile '{args.profile}' not found.")
            return

    for key, profile in profiles_to_test:
        try:
            test_profile(key, profile, llm)
            # Pause between profiles
            time.sleep(2.0)
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted.")
            break
        except Exception as e:
            print(f"❌ Error testing profile {key}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
