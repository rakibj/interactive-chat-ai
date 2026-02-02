#!/usr/bin/env python3
"""Test script to verify profile settings"""

from interactive_chat.config import INSTRUCTION_PROFILES, get_profile_settings

print("=== All Profiles and Settings ===\n")
for key in INSTRUCTION_PROFILES:
    settings = get_profile_settings(key)
    print(f"{key}:")
    print(f"  name: {settings['name']}")
    print(f"  voice: {settings['voice']}")
    print(f"  start: {settings['start']}")
    print(f"  max_tokens: {settings['max_tokens']}")
    print(f"  temperature: {settings['temperature']}")
    print(f"  pause_ms: {settings['pause_ms']}")
    print(f"  end_ms: {settings['end_ms']}")
    print(f"  safety_timeout_ms: {settings['safety_timeout_ms']}")
    print(f"  interruption_sensitivity: {settings['interruption_sensitivity']}")
    print()

print("\nAll profiles loaded successfully!")
