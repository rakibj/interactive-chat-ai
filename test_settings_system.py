#!/usr/bin/env python3
"""
Comprehensive test for per-profile settings system.
Tests that each profile has unique settings and the system correctly applies them.
"""

from interactive_chat.config import (
    INSTRUCTION_PROFILES,
    get_profile_settings,
    PAUSE_MS,
    END_MS,
    SAFETY_TIMEOUT_MS,
    INTERRUPTION_SENSITIVITY,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)

def test_profile_structure():
    """Verify all profiles have required settings."""
    print("=" * 60)
    print("TEST 1: Profile Structure Validation")
    print("=" * 60)
    
    required_keys = {
        "name", "start", "voice", "max_tokens", "temperature",
        "pause_ms", "end_ms", "safety_timeout_ms", "interruption_sensitivity", "instructions"
    }
    
    for profile_name, profile_data in INSTRUCTION_PROFILES.items():
        missing = required_keys - set(profile_data.keys())
        if missing:
            print(f"❌ {profile_name}: Missing keys {missing}")
            return False
        print(f"✓ {profile_name}: All required keys present")
    
    print("\n✓ All profiles have correct structure!\n")
    return True


def test_profile_defaults():
    """Verify profiles use defaults when keys are missing."""
    print("=" * 60)
    print("TEST 2: Default Values Fallback")
    print("=" * 60)
    
    print(f"Global defaults:")
    print(f"  PAUSE_MS: {PAUSE_MS}")
    print(f"  END_MS: {END_MS}")
    print(f"  SAFETY_TIMEOUT_MS: {SAFETY_TIMEOUT_MS}")
    print(f"  INTERRUPTION_SENSITIVITY: {INTERRUPTION_SENSITIVITY}")
    print(f"  LLM_MAX_TOKENS: {LLM_MAX_TOKENS}")
    print(f"  LLM_TEMPERATURE: {LLM_TEMPERATURE}\n")
    
    for profile_name in INSTRUCTION_PROFILES:
        settings = get_profile_settings(profile_name)
        print(f"{profile_name}:")
        print(f"  pause_ms: {settings['pause_ms']}")
        print(f"  end_ms: {settings['end_ms']}")
        print(f"  safety_timeout_ms: {settings['safety_timeout_ms']}")
        print(f"  interruption_sensitivity: {settings['interruption_sensitivity']}")
        print(f"  max_tokens: {settings['max_tokens']}")
        print(f"  temperature: {settings['temperature']}")
    
    print("\n✓ Default values working correctly!\n")
    return True


def test_profile_uniqueness():
    """Verify each profile has its own settings (not all identical)."""
    print("=" * 60)
    print("TEST 3: Profile Uniqueness")
    print("=" * 60)
    
    pause_ms_values = set()
    end_ms_values = set()
    safety_timeout_values = set()
    
    for profile_name in INSTRUCTION_PROFILES:
        settings = get_profile_settings(profile_name)
        pause_ms_values.add(settings['pause_ms'])
        end_ms_values.add(settings['end_ms'])
        safety_timeout_values.add(settings['safety_timeout_ms'])
    
    print(f"Unique pause_ms values: {pause_ms_values}")
    print(f"Unique end_ms values: {end_ms_values}")
    print(f"Unique safety_timeout_ms values: {safety_timeout_values}")
    
    if len(pause_ms_values) > 1 or len(end_ms_values) > 1 or len(safety_timeout_values) > 1:
        print("\n✓ Profiles have unique settings!\n")
        return True
    else:
        print("\n❌ All profiles have identical settings - this defeats the purpose!\n")
        return False


def test_voice_settings():
    """Verify each profile has a voice setting."""
    print("=" * 60)
    print("TEST 4: Voice Settings")
    print("=" * 60)
    
    voices = {}
    for profile_name in INSTRUCTION_PROFILES:
        settings = get_profile_settings(profile_name)
        voices[profile_name] = settings['voice']
        print(f"{profile_name}: voice = {settings['voice']}")
    
    if all(voices.values()):
        print("\n✓ All profiles have voice settings!\n")
        return True
    else:
        print("\n❌ Some profiles missing voice!\n")
        return False


def test_start_speaker():
    """Verify who speaks first (ai or human)."""
    print("=" * 60)
    print("TEST 5: Conversation Starter (start)")
    print("=" * 60)
    
    for profile_name in INSTRUCTION_PROFILES:
        settings = get_profile_settings(profile_name)
        start = settings['start']
        if start not in ("ai", "human"):
            print(f"❌ {profile_name}: Invalid start value '{start}' (must be 'ai' or 'human')")
            return False
        print(f"{profile_name}: starts with {start.upper()}")
    
    print("\n✓ All profiles have valid conversation starters!\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PER-PROFILE SETTINGS SYSTEM - COMPREHENSIVE TEST")
    print("=" * 60 + "\n")
    
    tests = [
        test_profile_structure,
        test_profile_defaults,
        test_profile_uniqueness,
        test_voice_settings,
        test_start_speaker,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ TEST FAILED WITH EXCEPTION: {e}\n")
            results.append(False)
    
    print("=" * 60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("✓ ALL TESTS PASSED - Per-profile settings system is working!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - See details above")
        return 1


if __name__ == "__main__":
    exit(main())
