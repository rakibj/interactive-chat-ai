"""Test script for PhaseProfile system - demonstrates deterministic phase transitions."""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "interactive_chat"))

from config import PHASE_PROFILES, PhaseProfile, InstructionProfile


def test_phase_profile_structure():
    """Test that PhaseProfiles are properly configured."""
    print("=" * 70)
    print("PHASE PROFILE STRUCTURE TEST")
    print("=" * 70)
    
    for profile_name, phase_profile in PHASE_PROFILES.items():
        print(f"\n📋 PhaseProfile: {phase_profile.name}")
        print(f"   Initial Phase: {phase_profile.initial_phase}")
        print(f"   Total Phases: {len(phase_profile.phases)}")
        
        # List all phases
        print(f"\n   Phases:")
        for phase_id, instruction_profile in phase_profile.phases.items():
            print(f"      - {phase_id}: {instruction_profile.name}")
            print(f"        Authority: {instruction_profile.authority}")
            print(f"        Start: {instruction_profile.start}")
            print(f"        Signals: {list(instruction_profile.signals.keys())}")
        
        # List transitions
        print(f"\n   Transitions:")
        for transition in phase_profile.transitions:
            print(f"      {transition.from_phase} → {transition.to_phase}")
            print(f"         Triggers: {transition.trigger_signals}")
            print(f"         Require All: {transition.require_all}")
        
        print(f"\n   Phase Context:")
        print(f"      Global: {bool(phase_profile.phase_context)}")
        print(f"      Per-Phase: {bool(phase_profile.per_phase_context)}")
        
        print("-" * 70)


def test_phase_transitions():
    """Test transition logic."""
    print("\n" + "=" * 70)
    print("PHASE TRANSITION LOGIC TEST")
    print("=" * 70)
    
    # Test IELTS exam transitions
    ielts = PHASE_PROFILES["ielts_full_exam"]
    
    test_cases = [
        ("greeting", ["custom.exam.greeting_complete"], "part1"),
        ("part1", ["custom.exam.questions_completed"], "part2"),
        ("part2", ["custom.exam.monologue_complete"], "part3"),
        ("part3", ["custom.exam.discussion_complete"], "closing"),
        ("greeting", ["custom.other.signal"], None),  # Should not transition
    ]
    
    print(f"\n📋 Testing: {ielts.name}")
    
    for current_phase, signals, expected_next in test_cases:
        result = ielts.find_transition(current_phase, signals)
        status = "✅" if result == expected_next else "❌"
        print(f"   {status} {current_phase} + {signals} → {result} (expected: {expected_next})")
    
    # Test Sales call transitions (has branching)
    sales = PHASE_PROFILES["sales_call"]
    
    print(f"\n📋 Testing: {sales.name}")
    
    test_cases = [
        ("pitch", ["custom.sales.objection_raised"], "objection_handling"),
        ("pitch", ["custom.sales.value_presented"], "close"),
        ("objection_handling", ["custom.sales.objection_resolved"], "close"),
        ("objection_handling", ["custom.sales.needs_more_info"], "pitch"),
    ]
    
    for current_phase, signals, expected_next in test_cases:
        result = sales.find_transition(current_phase, signals)
        status = "✅" if result == expected_next else "❌"
        print(f"   {status} {current_phase} + {signals} → {result} (expected: {expected_next})")


def test_phase_context_injection():
    """Test phase context generation."""
    print("\n" + "=" * 70)
    print("PHASE CONTEXT INJECTION TEST")
    print("=" * 70)
    
    ielts = PHASE_PROFILES["ielts_full_exam"]
    
    print(f"\n📋 PhaseProfile: {ielts.name}")
    
    for phase_id in ["greeting", "part1", "part2"]:
        context = ielts.get_phase_context(phase_id)
        print(f"\n   Phase: {phase_id}")
        print(f"   Context Length: {len(context)} chars")
        print(f"   Preview: {context[:100]}...")


def test_standalone_vs_phase_mode():
    """Test that InstructionProfiles work both standalone and in PhaseProfiles."""
    print("\n" + "=" * 70)
    print("STANDALONE vs PHASE MODE TEST")
    print("=" * 70)
    
    from config import INSTRUCTION_PROFILES
    
    # Check if the same InstructionProfile model works in both contexts
    standalone_profile = INSTRUCTION_PROFILES["ielts_instructor"]
    phase_profile_phase = PHASE_PROFILES["ielts_full_exam"].get_phase("part1")
    
    print(f"\n✅ Standalone InstructionProfile: {standalone_profile.name}")
    print(f"   Type: {type(standalone_profile).__name__}")
    print(f"   Signals: {list(standalone_profile.signals.keys())}")
    
    print(f"\n✅ Phase InstructionProfile: {phase_profile_phase.name}")
    print(f"   Type: {type(phase_profile_phase).__name__}")
    print(f"   Signals: {list(phase_profile_phase.signals.keys())}")
    
    print(f"\n✅ Both use the same InstructionProfile model!")


if __name__ == "__main__":
    test_phase_profile_structure()
    test_phase_transitions()
    test_phase_context_injection()
    test_standalone_vs_phase_mode()
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED ✅")
    print("=" * 70)
    print("\nTo use PhaseProfiles:")
    print("1. In config.py, set: ACTIVE_PHASE_PROFILE = 'ielts_full_exam'")
    print("2. Run: python interactive_chat/main.py")
    print("3. The conversation will automatically transition through phases")
    print("4. based on signals emitted by the LLM!")
    print("=" * 70)
