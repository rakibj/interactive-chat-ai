"""
Integration Test: API Response Simulation & Frontend Validation
Tests the complete flow from API to Frontend rendering
"""

import json
from typing import Optional, List, Dict, Any

# ================== SIMULATED API RESPONSES ==================

class SimulatedPhaseProgress:
    """Simulates API PhaseProgress model"""
    def __init__(self, id: str, name: str, status: str, duration_sec: Optional[float] = None):
        self.id = id
        self.name = name
        self.status = status
        self.duration_sec = duration_sec
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "duration_sec": self.duration_sec
        }


class SimulatedPhaseState:
    """Simulates API PhaseState model"""
    def __init__(self, 
                 current_phase_id: str,
                 phase_index: int,
                 total_phases: int,
                 phase_name: str,
                 phase_profile: str,
                 progress: List[Dict[str, Any]]):
        self.current_phase_id = current_phase_id
        self.phase_index = phase_index
        self.total_phases = total_phases
        self.phase_name = phase_name
        self.phase_profile = phase_profile
        self.progress = progress
    
    def to_dict(self):
        return {
            "current_phase_id": self.current_phase_id,
            "phase_index": self.phase_index,
            "total_phases": self.total_phases,
            "phase_name": self.phase_name,
            "phase_profile": self.phase_profile,
            "progress": self.progress
        }


class SimulatedSpeakerStatus:
    """Simulates API SpeakerStatus model"""
    def __init__(self, speaker: str, timestamp: float, phase_id: Optional[str] = None):
        self.speaker = speaker
        self.timestamp = timestamp
        self.phase_id = phase_id
    
    def to_dict(self):
        return {
            "speaker": self.speaker,
            "timestamp": self.timestamp,
            "phase_id": self.phase_id
        }


class SimulatedTurn:
    """Simulates API Turn model"""
    def __init__(self,
                 turn_id: int,
                 speaker: str,
                 transcript: str,
                 timestamp: float,
                 phase_id: str,
                 duration_sec: float,
                 latency_ms: Optional[int] = None,
                 end_reason: Optional[str] = None):
        self.turn_id = turn_id
        self.speaker = speaker
        self.transcript = transcript
        self.timestamp = timestamp
        self.phase_id = phase_id
        self.duration_sec = duration_sec
        self.latency_ms = latency_ms
        self.end_reason = end_reason
    
    def to_dict(self):
        return {
            "turn_id": self.turn_id,
            "speaker": self.speaker,
            "transcript": self.transcript,
            "timestamp": self.timestamp,
            "phase_id": self.phase_id,
            "duration_sec": self.duration_sec,
            "latency_ms": self.latency_ms,
            "end_reason": self.end_reason
        }


class SimulatedConversationState:
    """Simulates API ConversationState model"""
    def __init__(self,
                 phase: Dict[str, Any],
                 speaker: Dict[str, Any],
                 turn_id: int,
                 history: List[Dict[str, Any]],
                 is_processing: bool = False):
        self.phase = phase
        self.speaker = speaker
        self.turn_id = turn_id
        self.history = history
        self.is_processing = is_processing
    
    def to_dict(self):
        return {
            "phase": self.phase,
            "speaker": self.speaker,
            "turn_id": self.turn_id,
            "history": self.history,
            "is_processing": self.is_processing
        }


# ================== TEST SCENARIOS ==================

def create_test_scenario_1():
    """Scenario 1: Single phase, no turns yet"""
    print("\n" + "="*70)
    print("TEST SCENARIO 1: Single Phase, No Turns Yet")
    print("="*70)
    
    progress = [
        SimulatedPhaseProgress("greeting", "Greeting", "active").to_dict(),
        SimulatedPhaseProgress("questions", "Main Questions", "upcoming").to_dict(),
        SimulatedPhaseProgress("closing", "Closing", "upcoming").to_dict(),
    ]
    
    phase_state = SimulatedPhaseState(
        current_phase_id="greeting",
        phase_index=0,
        total_phases=3,
        phase_name="Greeting",
        phase_profile="basic_interview",
        progress=progress
    ).to_dict()
    
    speaker_status = SimulatedSpeakerStatus(
        speaker="silence",
        timestamp=1707052800.0,
        phase_id="greeting"
    ).to_dict()
    
    state = SimulatedConversationState(
        phase=phase_state,
        speaker=speaker_status,
        turn_id=0,
        history=[],
        is_processing=False
    )
    
    return state.to_dict()


def create_test_scenario_2():
    """Scenario 2: Multi-phase with completed phases and turns"""
    print("\n" + "="*70)
    print("TEST SCENARIO 2: Multi-Phase with History")
    print("="*70)
    
    progress = [
        SimulatedPhaseProgress("greeting", "Greeting", "completed", 5.2).to_dict(),
        SimulatedPhaseProgress("part1", "Part 1 - Personal", "completed", 12.5).to_dict(),
        SimulatedPhaseProgress("part2", "Part 2 - Extended", "active", 3.1).to_dict(),
        SimulatedPhaseProgress("part3", "Part 3 - Discussion", "upcoming").to_dict(),
        SimulatedPhaseProgress("closing", "Closing", "upcoming").to_dict(),
    ]
    
    phase_state = SimulatedPhaseState(
        current_phase_id="part2",
        phase_index=2,
        total_phases=5,
        phase_name="Part 2 - Extended Monologue",
        phase_profile="ielts_speaking_full",
        progress=progress
    ).to_dict()
    
    speaker_status = SimulatedSpeakerStatus(
        speaker="human",
        timestamp=1707052825.5,
        phase_id="part2"
    ).to_dict()
    
    history = [
        SimulatedTurn(
            turn_id=0,
            speaker="ai",
            transcript="Good morning. Let me start this speaking test. First, I'll ask you some questions about yourself.",
            timestamp=1707052800.0,
            phase_id="greeting",
            duration_sec=5.2,
            latency_ms=1200,
            end_reason="silence"
        ).to_dict(),
        SimulatedTurn(
            turn_id=1,
            speaker="human",
            transcript="Hello. Thank you for explaining that. I'm ready.",
            timestamp=1707052805.2,
            phase_id="greeting",
            duration_sec=3.5,
            latency_ms=850,
            end_reason="silence"
        ).to_dict(),
        SimulatedTurn(
            turn_id=2,
            speaker="ai",
            transcript="Tell me, where are you from and what do you do?",
            timestamp=1707052808.7,
            phase_id="part1",
            duration_sec=2.3,
            latency_ms=950,
            end_reason="silence"
        ).to_dict(),
        SimulatedTurn(
            turn_id=3,
            speaker="human",
            transcript="I'm from Beijing, China. I work as a software engineer for a tech company. I've been working there for about 3 years and really enjoy the challenges.",
            timestamp=1707052811.0,
            phase_id="part1",
            duration_sec=10.2,
            latency_ms=2100,
            end_reason="silence"
        ).to_dict(),
        SimulatedTurn(
            turn_id=4,
            speaker="ai",
            transcript="That's interesting. Now, I'd like you to speak for about 2 minutes on this topic. Describe a place you have visited that was important to you.",
            timestamp=1707052821.2,
            phase_id="part2",
            duration_sec=3.5,
            latency_ms=1100,
            end_reason="silence"
        ).to_dict(),
    ]
    
    state = SimulatedConversationState(
        phase=phase_state,
        speaker=speaker_status,
        turn_id=5,
        history=history,
        is_processing=True
    )
    
    return state.to_dict()


def create_test_scenario_3():
    """Scenario 3: Edge case - empty phase profile (NO PHASES)"""
    print("\n" + "="*70)
    print("TEST SCENARIO 3: Empty Phase Profile (API Issue)")
    print("="*70)
    
    phase_state = SimulatedPhaseState(
        current_phase_id="unknown",
        phase_index=0,
        total_phases=0,
        phase_name="Unknown",
        phase_profile="single_profile",
        progress=[]  # <-- EMPTY! This is the problem
    ).to_dict()
    
    speaker_status = SimulatedSpeakerStatus(
        speaker="silence",
        timestamp=1707052800.0,
        phase_id=None
    ).to_dict()
    
    state = SimulatedConversationState(
        phase=phase_state,
        speaker=speaker_status,
        turn_id=0,
        history=[],
        is_processing=False
    )
    
    return state.to_dict()


# ================== FRONTEND VALIDATION ==================

def validate_api_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate API response structure"""
    print("\n📋 VALIDATING API RESPONSE STRUCTURE")
    print("-" * 70)
    
    issues = []
    warnings = []
    
    # Check top-level fields
    required_fields = ["phase", "speaker", "turn_id", "history", "is_processing"]
    for field in required_fields:
        if field not in state:
            issues.append(f"❌ Missing required field: {field}")
        else:
            print(f"✅ {field}: present")
    
    # Check phase structure
    if "phase" in state:
        phase = state["phase"]
        required_phase_fields = ["current_phase_id", "phase_index", "total_phases", "phase_name", "phase_profile", "progress"]
        for field in required_phase_fields:
            if field not in phase:
                issues.append(f"❌ Missing phase field: {field}")
            else:
                print(f"  ✅ phase.{field}: {phase[field]}")
        
        # Check progress array
        if "progress" in phase:
            progress = phase["progress"]
            if not isinstance(progress, list):
                issues.append(f"❌ phase.progress is not a list (got {type(progress).__name__})")
            elif len(progress) == 0:
                warnings.append(f"⚠️  phase.progress is empty (0 phases)")
            else:
                print(f"  ✅ phase.progress: {len(progress)} phases")
                for i, p in enumerate(progress):
                    required_progress_fields = ["id", "name", "status"]
                    for field in required_progress_fields:
                        if field not in p:
                            issues.append(f"❌ phase.progress[{i}] missing field: {field}")
                    if "status" in p and p["status"] not in ["completed", "active", "upcoming"]:
                        issues.append(f"❌ phase.progress[{i}].status invalid value: {p['status']}")
    
    # Check speaker structure  
    if "speaker" in state:
        speaker = state["speaker"]
        required_speaker_fields = ["speaker", "timestamp"]
        for field in required_speaker_fields:
            if field not in speaker:
                issues.append(f"❌ Missing speaker field: {field}")
        if "speaker" in speaker and speaker["speaker"] not in ["human", "ai", "silence"]:
            issues.append(f"❌ speaker.speaker invalid value: {speaker['speaker']}")
    
    # Check history
    if "history" in state:
        history = state["history"]
        if not isinstance(history, list):
            issues.append(f"❌ history is not a list (got {type(history).__name__})")
        else:
            print(f"✅ history: {len(history)} turns")
            for i, turn in enumerate(history):
                required_turn_fields = ["turn_id", "speaker", "transcript", "timestamp", "phase_id"]
                for field in required_turn_fields:
                    if field not in turn:
                        issues.append(f"❌ history[{i}] missing field: {field}")
    
    print("\n🔍 VALIDATION SUMMARY")
    print("-" * 70)
    if issues:
        print(f"❌ Found {len(issues)} CRITICAL ISSUES:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("✅ NO CRITICAL ISSUES FOUND")
    
    if warnings:
        print(f"\n⚠️  Found {len(warnings)} WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
    else:
        print("✅ NO WARNINGS")
    
    return {
        "valid": len(issues) == 0,
        "critical_issues": issues,
        "warnings": warnings,
        "state": state
    }


def _validate_frontend_rendering(state: Dict[str, Any]) -> None:
    """Validate if frontend code would work with this state"""
    print("\n🎨 TESTING FRONTEND RENDERING")
    print("-" * 70)
    
    try:
        phase = state.get("phase", {})
        progress = phase.get("progress", [])
        
        print(f"Phase Title: {phase.get('current_phase_id', 'N/A')}")
        print(f"Phase Name: {phase.get('phase_name', 'N/A')}")
        print(f"Progress: {phase.get('phase_index', 0)}/{phase.get('total_phases', 0)} phases")
        
        if progress:
            print("\n📍 Phase Tracker Items:")
            for i, p in enumerate(progress):
                status_badge = {
                    'completed': '✅',
                    'active': '🔵',
                    'upcoming': '⭕'
                }.get(p.get('status'), '❓')
                
                duration_text = f" ({p.get('duration_sec'):.1f}s)" if p.get('duration_sec') else ""
                name = p.get('name', p.get('id', 'Unknown'))
                
                print(f"  {status_badge} {name}{duration_text}")
                
                if p.get('status') == 'active':
                    print(f"     ↳ Currently: {p.get('name') or p.get('id')}")
        else:
            print("  ⚠️  NO PHASE PROGRESS ITEMS (frontend will show empty tracker)")
        
        # Test turn rendering
        history = state.get("history", [])
        if history:
            print(f"\n💬 Last Turn (Turn #{history[-1].get('turn_id', '#?')}):")
            last = history[-1]
            icon = {'human': '🎤', 'ai': '🤖', 'silence': '⏸️'}.get(last.get('speaker'), '❓')
            print(f"   {icon} Speaker: {last.get('speaker')}")
            print(f"   ⏱️ Latency: {last.get('latency_ms', 'N/A')}ms")
            print(f"   💬 Text: \"{last.get('transcript')[:60]}...\"" if len(last.get('transcript', '')) > 60 else f"   💬 Text: \"{last.get('transcript', '')}\"")
        else:
            print("\n💬 No turns yet (empty state)")
        
        print("\n✅ FRONTEND RENDERING TEST PASSED")
    
    except Exception as e:
        print(f"\n❌ FRONTEND RENDERING TEST FAILED: {str(e)}")


# ================== RUN TESTS ==================

def run_all_tests():
    """Run all integration tests"""
    print("\n" + "=" * 70)
    print("PHASE VISUALS & TIMELINE - INTEGRATION TEST SUITE")
    print("=" * 70)
    
    scenarios = [
        ("Initial State", create_test_scenario_1()),
        ("Multi-Phase with History", create_test_scenario_2()),
        ("Empty Phase Profile (BUG CASE)", create_test_scenario_3()),
    ]
    
    results = []
    
    for scenario_name, state in scenarios:
        print(f"\n\n{'#' * 70}")
        print(f"# {scenario_name}")
        print(f"{'#' * 70}")
        
        # Validate
        validation = validate_api_response(state)
        results.append({
            "scenario": scenario_name,
            "validation": validation
        })
        
        # Validate frontend rendering
        _validate_frontend_rendering(state)
        
        # Show raw JSON
        print("\n📦 RAW JSON RESPONSE:")
        print("-" * 70)
        print(json.dumps(state, indent=2))
    
    # Summary
    print("\n\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for result in results:
        status = "✅ PASS" if result["validation"]["valid"] else "❌ FAIL"
        print(f"{status} - {result['scenario']}")
        if result["validation"]["critical_issues"]:
            for issue in result["validation"]["critical_issues"]:
                print(f"       {issue}")


if __name__ == "__main__":
    run_all_tests()
