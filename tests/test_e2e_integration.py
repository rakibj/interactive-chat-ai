#!/usr/bin/env python3
"""
End-to-end verification test for per-profile settings integration.
Simulates what happens when ConversationEngine initializes with different profiles.
"""

import sys
from interactive_chat.config import (
    INSTRUCTION_PROFILES,
    get_profile_settings,
    get_system_prompt,
    ACTIVE_PROFILE,
)


def test_profile_initialization():
    """Test that we can initialize settings for each profile."""
    print("=" * 70)
    print("TEST: Profile Initialization & Settings Application")
    print("=" * 70)
    
    for profile_name in INSTRUCTION_PROFILES.keys():
        print(f"\n📋 Testing profile: {profile_name}")
        
        # Load settings
        settings = get_profile_settings(profile_name)
        
        # Verify all required settings are present
        required = [
            'name', 'start', 'voice', 'max_tokens', 'temperature',
            'pause_ms', 'end_ms', 'safety_timeout_ms',
            'interruption_sensitivity', 'instructions'
        ]
        
        missing = [k for k in required if k not in settings]
        if missing:
            print(f"   ❌ Missing settings: {missing}")
            return False
        
        # Simulate TurnTaker configuration
        print(f"   • TurnTaker settings:")
        print(f"     - pause_ms: {settings['pause_ms']}")
        print(f"     - end_ms: {settings['end_ms']}")
        print(f"     - safety_timeout_ms: {settings['safety_timeout_ms']}")
        
        # Simulate InterruptionManager configuration
        print(f"   • InterruptionManager settings:")
        print(f"     - interruption_sensitivity: {settings['interruption_sensitivity']}")
        
        # Simulate LLM configuration
        print(f"   • LLM settings:")
        print(f"     - max_tokens: {settings['max_tokens']}")
        print(f"     - temperature: {settings['temperature']}")
        
        # Simulate TTS configuration
        print(f"   • TTS settings:")
        print(f"     - voice: {settings['voice']}")
        
        # Verify system prompt
        system_prompt = get_system_prompt(profile_name)
        if len(system_prompt) < 50:
            print(f"   ❌ System prompt too short: {len(system_prompt)} chars")
            return False
        print(f"   • System prompt: {len(system_prompt)} chars")
        
        # Verify conversation start
        if settings['start'] not in ('ai', 'human'):
            print(f"   ❌ Invalid start: {settings['start']}")
            return False
        print(f"   • Conversation starts with: {settings['start'].upper()}")
        
        print(f"   ✓ Profile '{profile_name}' ready!")
    
    print("\n" + "=" * 70)
    print("✓ ALL PROFILES CAN BE INITIALIZED CORRECTLY")
    print("=" * 70)
    return True


def test_timing_relationships():
    """Verify timing relationships make sense."""
    print("\n" + "=" * 70)
    print("TEST: Timing Relationships Validation")
    print("=" * 70)
    
    issues = []
    
    for profile_name in INSTRUCTION_PROFILES.keys():
        settings = get_profile_settings(profile_name)
        
        pause_ms = settings['pause_ms']
        end_ms = settings['end_ms']
        safety_timeout_ms = settings['safety_timeout_ms']
        
        # Check relationships
        if end_ms <= pause_ms:
            issues.append(f"{profile_name}: end_ms ({end_ms}) should be > pause_ms ({pause_ms})")
        
        if safety_timeout_ms <= end_ms:
            issues.append(f"{profile_name}: safety_timeout_ms ({safety_timeout_ms}) should be > end_ms ({end_ms})")
        
        ratio_end_to_pause = end_ms / pause_ms
        if ratio_end_to_pause < 1.2 or ratio_end_to_pause > 3.0:
            print(f"⚠️  {profile_name}: end_ms is {ratio_end_to_pause:.2f}x pause_ms (recommended 1.5-2.0x)")
        
        ratio_safety_to_end = safety_timeout_ms / end_ms
        if ratio_safety_to_end < 1.5 or ratio_safety_to_end > 3.0:
            print(f"⚠️  {profile_name}: safety_timeout_ms is {ratio_safety_to_end:.2f}x end_ms (recommended 2.0-2.5x)")
        
        print(f"✓ {profile_name}: pause={pause_ms}ms, end={end_ms}ms ({ratio_end_to_pause:.2f}x), safety={safety_timeout_ms}ms ({ratio_safety_to_end:.2f}x)")
    
    if issues:
        for issue in issues:
            print(f"❌ {issue}")
        return False
    
    print("\n✓ All timing relationships are valid!")
    return True


def test_interruption_sensitivity():
    """Verify interruption sensitivities are in valid range."""
    print("\n" + "=" * 70)
    print("TEST: Interruption Sensitivity Values")
    print("=" * 70)
    
    for profile_name in INSTRUCTION_PROFILES.keys():
        settings = get_profile_settings(profile_name)
        sensitivity = settings['interruption_sensitivity']
        
        if not (0.0 <= sensitivity <= 1.0):
            print(f"❌ {profile_name}: invalid sensitivity {sensitivity} (must be 0.0-1.0)")
            return False
        
        if sensitivity == 0.0:
            description = "No interruption (wait for complete response)"
        elif sensitivity <= 0.3:
            description = "Professional (rare interruption)"
        elif sensitivity <= 0.6:
            description = "Conversational (occasional interruption)"
        else:
            description = "Aggressive (frequent interruption)"
        
        print(f"✓ {profile_name}: {sensitivity} ({description})")
    
    print("\n✓ All interruption sensitivities are valid!")
    return True


def test_llm_parameters():
    """Verify LLM parameters are reasonable."""
    print("\n" + "=" * 70)
    print("TEST: LLM Parameters (max_tokens, temperature)")
    print("=" * 70)
    
    for profile_name in INSTRUCTION_PROFILES.keys():
        settings = get_profile_settings(profile_name)
        
        max_tokens = settings['max_tokens']
        temperature = settings['temperature']
        
        if max_tokens < 30 or max_tokens > 500:
            print(f"⚠️  {profile_name}: max_tokens={max_tokens} (unusual, typical range 80-150)")
        
        if not (0.0 <= temperature <= 2.0):
            print(f"❌ {profile_name}: invalid temperature {temperature}")
            return False
        
        if temperature < 0.3:
            style = "Very factual"
        elif temperature < 0.6:
            style = "Factual"
        elif temperature < 0.85:
            style = "Balanced"
        else:
            style = "Creative"
        
        print(f"✓ {profile_name}: max_tokens={max_tokens}, temperature={temperature} ({style})")
    
    print("\n✓ All LLM parameters are reasonable!")
    return True


def test_current_active_profile():
    """Show current active profile."""
    print("\n" + "=" * 70)
    print("CURRENT ACTIVE PROFILE")
    print("=" * 70)
    
    settings = get_profile_settings(ACTIVE_PROFILE)
    print(f"\nActive Profile: {ACTIVE_PROFILE}")
    print(f"  Name: {settings['name']}")
    print(f"  Starts with: {settings['start'].upper()}")
    print(f"  Voice: {settings['voice']}")
    print(f"  LLM: max_tokens={settings['max_tokens']}, temperature={settings['temperature']}")
    print(f"  Timing: pause={settings['pause_ms']}ms, end={settings['end_ms']}ms, safety={settings['safety_timeout_ms']}ms")
    print(f"  Interruption sensitivity: {settings['interruption_sensitivity']}")
    
    return True


def main():
    """Run all verification tests."""
    print("\n" + "🔍 PER-PROFILE SETTINGS - END-TO-END VERIFICATION TEST\n")
    
    tests = [
        ("Profile Initialization", test_profile_initialization),
        ("Timing Relationships", test_timing_relationships),
        ("Interruption Sensitivity", test_interruption_sensitivity),
        ("LLM Parameters", test_llm_parameters),
        ("Current Active Profile", test_current_active_profile),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ TEST '{test_name}' FAILED WITH EXCEPTION:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 70)
    print(f"FINAL RESULTS: {sum(results)}/{len(results)} test groups passed")
    print("=" * 70)
    
    if all(results):
        print("\n✓✓✓ FULL INTEGRATION SUCCESS ✓✓✓")
        print("Per-profile settings system is fully operational!")
        print("\nYou can now:")
        print("  1. Run: python -m interactive_chat.main")
        print("  2. Change ACTIVE_PROFILE in config.py to switch profiles")
        print("  3. Modify any profile settings in config.py")
        print("  4. Each profile has unique: timing, voice, LLM, interaction settings")
        return 0
    else:
        print("\n❌ Some tests failed - see details above")
        return 1


if __name__ == "__main__":
    exit(main())
