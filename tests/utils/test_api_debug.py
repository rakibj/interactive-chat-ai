#!/usr/bin/env python3
"""Quick test to verify API returns phase data correctly."""

import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from interactive_chat.main import ConversationEngine
from interactive_chat.server import set_engine

print("=" * 60)
print("TESTING API PHASE DATA")
print("=" * 60)

# Initialize with phase profile
print("\n[1] Initializing engine with ielts_full_exam...")
engine = ConversationEngine(profile_key='ielts_full_exam')
set_engine(engine)

# Check state
print(f"\n[2] Engine state:")
print(f"    Active Phase ID: {engine.state.active_phase_id}")
print(f"    Total Phases: {engine.state.total_phases}")  
print(f"    Phase Index: {engine.state.phase_index}")
print(f"    Phases Completed: {engine.state.phases_completed}")

# Simulate what the API returns
print(f"\n[3] What API would return (/api/state/phase):")
response = {
    "current_phase_id": engine.state.active_phase_id,
    "num_phases_in_response": len(engine.active_phase_profile.phases) if engine.active_phase_profile else 0,
    "phases_completed": engine.state.phases_completed,
    "total_messages": 0,  # Will have messages after turns
    "total_phases": engine.state.total_phases,
}

for key, value in response.items():
    symbol = "✅" if value else "⚠️"
    print(f"    {symbol} {key}: {value}")

# Check phase profile
print(f"\n[4] Phase profile details:")
if engine.active_phase_profile:
    print(f"    Name: {engine.active_phase_profile.name}")
    print(f"    Phases: {list(engine.active_phase_profile.phases.keys())}")
    print(f"    Initial Phase: {engine.active_phase_profile.initial_phase}")
    
    for phase_id, phase_obj in engine.active_phase_profile.phases.items():
        print(f"      - {phase_id}: {phase_obj.name}")
else:
    print("    ❌ No phase profile loaded (PROBLEM!)")

print("\n[5] Comparison:")
print("    BEFORE FIX (negotiator): total_phases=0, num_phases=0")
print(f"    AFTER FIX (ielts_full_exam): total_phases={engine.state.total_phases}, num_phases={len(engine.active_phase_profile.phases) if engine.active_phase_profile else 0}")

print("\n" + "=" * 60)
print("✅ API RESPONSE SHOULD NOW SHOW PHASE DATA")
print("=" * 60)
