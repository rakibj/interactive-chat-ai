"""
TDD: Phase observation events for demo UI.
These tests define WHAT we need to observe about phases.

Tests verify that:
1. Phase transitions emit observable signals
2. Phase progress is tracked and accessible
3. Speaker changes are detected and emitted
4. Multiple listeners can register independently
"""

import pytest
import sys
import os
from dataclasses import dataclass

# Add project to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "interactive_chat"))

from core.signals import SignalName, Signal, emit_signal, get_signal_registry
from core.event_driven_core import Event, EventType, Action, ActionType, SystemState, Reducer


@dataclass
class PhaseProgressPayload:
    """Payload for phase.progress_updated signal."""
    current_phase_id: str
    phase_index: int  # 0-based
    total_phases: int
    phase_name: str
    phase_profile: str
    progress: list  # [{"id": "greeting", "status": "completed"}, ...]


@pytest.fixture
def signal_registry():
    """Get a fresh signal registry for each test."""
    registry = get_signal_registry()
    registry.clear()
    yield registry
    registry.clear()


def test_phase_transition_emits_phase_started_signal(signal_registry):
    """When entering a new phase, emit phase.transition_started signal."""
    signals_received = []
    signal_registry.register("phase.transition_started", lambda sig: signals_received.append(sig))
    
    # Simulate phase transition
    emit_signal(
        SignalName.PHASE_TRANSITION_STARTED,
        payload={
            "from_phase": "greeting",
            "to_phase": "part1",
            "phase_index": 1,
            "total_phases": 5,
            "trigger_signal": "custom.exam.greeting_complete"
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.name == SignalName.PHASE_TRANSITION_STARTED
    assert sig.payload["to_phase"] == "part1"
    assert sig.payload["phase_index"] == 1
    assert sig.payload["total_phases"] == 5


def test_phase_transition_emits_phase_complete_signal(signal_registry):
    """When phase transition completes, emit phase.transition_complete signal."""
    signals_received = []
    signal_registry.register("phase.transition_complete", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.PHASE_TRANSITION_COMPLETE,
        payload={
            "new_phase_id": "part1",
            "phase_index": 1,
            "total_phases": 5,
            "phase_name": "IELTS - Part 1: Personal Questions",
            "timestamp": 1738515601.234
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.payload["new_phase_id"] == "part1"
    assert sig.payload["phase_name"] == "IELTS - Part 1: Personal Questions"


def test_phase_progress_updated_signal(signal_registry):
    """Emit signal when phase progress tracking updates."""
    signals_received = []
    signal_registry.register("phase.progress_updated", lambda sig: signals_received.append(sig))
    
    progress = [
        {"id": "greeting", "status": "completed", "name": "Greeting"},
        {"id": "part1", "status": "active", "name": "Part 1"},
        {"id": "part2", "status": "upcoming", "name": "Part 2"},
        {"id": "part3", "status": "upcoming", "name": "Part 3"},
        {"id": "closing", "status": "upcoming", "name": "Closing"},
    ]
    
    emit_signal(
        SignalName.PHASE_PROGRESS_UPDATED,
        payload={
            "current_phase_id": "part1",
            "phase_index": 1,
            "total_phases": 5,
            "phase_profile": "ielts_full_exam",
            "progress": progress
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.payload["current_phase_id"] == "part1"
    assert len(sig.payload["progress"]) == 5
    assert sig.payload["progress"][0]["status"] == "completed"
    assert sig.payload["progress"][1]["status"] == "active"


def test_phase_transition_triggered_signal(signal_registry):
    """When phase transition is triggered by a signal, emit event."""
    signals_received = []
    signal_registry.register("phase.transition_triggered", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.PHASE_TRANSITION_TRIGGERED,
        payload={
            "from_phase": "greeting",
            "to_phase": "part1",
            "trigger_signals": ["custom.exam.greeting_complete"],
            "trigger_reason": "all_signals_matched"
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.payload["trigger_signals"] == ["custom.exam.greeting_complete"]


def test_speaker_changed_signal_human_to_ai(signal_registry):
    """When speaker changes from human to AI, emit signal."""
    signals_received = []
    signal_registry.register("conversation.speaker_changed", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.SPEAKER_CHANGED,
        payload={
            "speaker": "ai",
            "previous_speaker": "human",
            "timestamp": 1738515601.234,
            "phase_id": "part1"
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.payload["speaker"] == "ai"
    assert sig.payload["previous_speaker"] == "human"


def test_speaker_changed_signal_ai_to_silence(signal_registry):
    """When speaker changes from AI to silence, emit signal."""
    signals_received = []
    signal_registry.register("conversation.speaker_changed", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.SPEAKER_CHANGED,
        payload={
            "speaker": "silence",
            "previous_speaker": "ai",
            "timestamp": 1738515601.234,
            "phase_id": "part1"
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.payload["speaker"] == "silence"


def test_phase_context_available_in_system_state():
    """SystemState tracks phase metadata for queries."""
    state = SystemState(
        active_phase_id="part1",
        phase_index=1,
        phase_profile_name="ielts_full_exam",
        total_phases=5,
        phases_completed=[],
        current_speaker="silence",
    )
    
    assert state.active_phase_id == "part1"
    assert state.phase_index == 1
    assert state.total_phases == 5
    assert state.phases_completed == []
    assert state.current_speaker == "silence"


def test_multiple_phase_listeners(signal_registry):
    """Multiple listeners can register for phase events independently."""
    listener1_signals = []
    listener2_signals = []
    
    signal_registry.register("phase.transition_complete", lambda sig: listener1_signals.append(sig))
    signal_registry.register("phase.transition_complete", lambda sig: listener2_signals.append(sig))
    
    emit_signal(
        SignalName.PHASE_TRANSITION_COMPLETE,
        payload={"new_phase_id": "part1"}
    )
    
    assert len(listener1_signals) == 1
    assert len(listener2_signals) == 1
    assert listener1_signals[0].payload["new_phase_id"] == "part1"


def test_phase_progress_tracks_completed_and_upcoming_phases(signal_registry):
    """Phase progress signal accurately reflects phase statuses."""
    signals_received = []
    signal_registry.register("phase.progress_updated", lambda sig: signals_received.append(sig))
    
    progress = [
        {"id": "greeting", "status": "completed", "name": "Greeting", "duration_sec": 45.2},
        {"id": "part1", "status": "completed", "name": "Part 1", "duration_sec": 320.5},
        {"id": "part2", "status": "active", "name": "Part 2", "duration_sec": None},
        {"id": "part3", "status": "upcoming", "name": "Part 3", "duration_sec": None},
        {"id": "closing", "status": "upcoming", "name": "Closing", "duration_sec": None},
    ]
    
    emit_signal(
        SignalName.PHASE_PROGRESS_UPDATED,
        payload={
            "current_phase_id": "part2",
            "phase_index": 2,
            "total_phases": 5,
            "phase_profile": "ielts_full_exam",
            "progress": progress
        }
    )
    
    sig = signals_received[0]
    completed_count = sum(1 for p in sig.payload["progress"] if p["status"] == "completed")
    active_count = sum(1 for p in sig.payload["progress"] if p["status"] == "active")
    upcoming_count = sum(1 for p in sig.payload["progress"] if p["status"] == "upcoming")
    
    assert completed_count == 2
    assert active_count == 1
    assert upcoming_count == 2


def test_system_state_speaker_tracking():
    """SystemState properly tracks speaker transitions."""
    state = SystemState()
    
    # Initial state
    assert state.current_speaker == "silence"
    assert state.previous_speaker == "silence"
    
    # Change speaker
    state.previous_speaker = state.current_speaker
    state.current_speaker = "human"
    
    assert state.previous_speaker == "silence"
    assert state.current_speaker == "human"
    
    # Change again
    state.previous_speaker = state.current_speaker
    state.current_speaker = "ai"
    
    assert state.previous_speaker == "human"
    assert state.current_speaker == "ai"
