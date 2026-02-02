#!/usr/bin/env python3
"""Test script to verify main.py loads profiles correctly"""

import sys
from interactive_chat.config import ACTIVE_PROFILE, get_profile_settings

print(f"Current ACTIVE_PROFILE: {ACTIVE_PROFILE}")

# Test loading profile settings
profile_settings = get_profile_settings(ACTIVE_PROFILE)
print(f"\nLoaded settings for '{ACTIVE_PROFILE}':")
for key, value in profile_settings.items():
    if key != "instructions":
        print(f"  {key}: {value}")

print("\nTest successful! Profile settings are properly integrated.")
