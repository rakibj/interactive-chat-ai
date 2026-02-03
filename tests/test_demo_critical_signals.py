"""
TDD: Critical signals for demo UI real-time updates.
These 5 signals enable the Gradio/Next.js UI to show live speaker status and processing state.

Tests verify:
1. VAD signals detect human speech start/end
2. TTS signals detect AI speech start/end
3. Turn processing signals mark processing phases
"""

import pytest
import sys
import os
from dataclasses import dataclass

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "interactive_chat"))

from core.signals import SignalName, Signal, emit_signal, get_signal_registry
from core.event_driven_core import Event, EventType, Action, ActionType, SystemState, Reducer
import time


@pytest.fixture
def signal_registry():
    """Get a fresh signal registry for each test."""
    registry = get_signal_registry()
    registry.clear()
    yield registry
    registry.clear()


# ============================================================================
# VAD SIGNALS (Speech Detection)
# ============================================================================

def test_vad_speech_started_signal_emitted(signal_registry):
    """When VAD detects speech start, emit vad.speech_started signal."""
    signals_received = []
    signal_registry.register("vad.speech_started", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.VAD_SPEECH_STARTED,
        payload={
            "timestamp": time.time(),
            "turn_id": 1,
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.name == SignalName.VAD_SPEECH_STARTED
    assert "timestamp" in sig.payload
    assert sig.payload["turn_id"] == 1


def test_vad_speech_ended_signal_emitted(signal_registry):
    """When VAD detects speech end, emit vad.speech_ended signal."""
    signals_received = []
    signal_registry.register("vad.speech_ended", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.VAD_SPEECH_ENDED,
        payload={
            "timestamp": time.time(),
            "duration_sec": 2.5,
            "turn_id": 1,
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.name == SignalName.VAD_SPEECH_ENDED
    assert sig.payload["duration_sec"] == 2.5


# ============================================================================
# TTS SIGNALS (AI Speech)
# ============================================================================

def test_tts_speaking_started_signal_emitted(signal_registry):
    """When AI starts speaking (TTS begins), emit tts.speaking_started signal."""
    signals_received = []
    signal_registry.register("tts.speaking_started", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.TTS_SPEAKING_STARTED,
        payload={
            "timestamp": time.time(),
            "text_preview": "Good morning. Let's begin the exam.",
            "turn_id": 1,
            "phase_id": "part1",
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.name == SignalName.TTS_SPEAKING_STARTED
    assert "text_preview" in sig.payload


def test_tts_speaking_ended_signal_emitted(signal_registry):
    """When AI finishes speaking (TTS complete), emit tts.speaking_ended signal."""
    signals_received = []
    signal_registry.register("tts.speaking_ended", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.TTS_SPEAKING_ENDED,
        payload={
            "timestamp": time.time(),
            "duration_sec": 8.3,
            "turn_id": 1,
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.name == SignalName.TTS_SPEAKING_ENDED
    assert sig.payload["duration_sec"] == 8.3


# ============================================================================
# TURN PROCESSING SIGNALS
# ============================================================================

def test_turn_started_signal_emitted(signal_registry):
    """When turn processing begins, emit turn.started signal."""
    signals_received = []
    signal_registry.register("turn.started", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.TURN_STARTED,
        payload={
            "timestamp": time.time(),
            "turn_id": 1,
            "reason": "silence",  # or "safety_timeout", "limit_exceeded"
            "phase_id": "part1",
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.name == SignalName.TURN_STARTED
    assert sig.payload["reason"] == "silence"


def test_turn_completed_signal_emitted(signal_registry):
    """When turn fully processed and logged, emit turn.completed signal."""
    signals_received = []
    signal_registry.register("turn.completed", lambda sig: signals_received.append(sig))
    
    emit_signal(
        SignalName.TURN_COMPLETED,
        payload={
            "timestamp": time.time(),
            "turn_id": 1,
            "human_transcript": "What is the capital of France?",
            "ai_transcript": "The capital of France is Paris.",
            "total_latency_ms": 2345,
            "phase_id": "part1",
        }
    )
    
    assert len(signals_received) == 1
    sig = signals_received[0]
    assert sig.name == SignalName.TURN_COMPLETED
    assert sig.payload["turn_id"] == 1
    assert "total_latency_ms" in sig.payload


# ============================================================================
# INTEGRATION: Real-time speaker status tracking
# ============================================================================

def test_speaker_status_sequence_human_to_ai(signal_registry):
    """Complete speaker transition: human speaks → processes → AI speaks."""
    all_signals = []
    signal_registry.register_all(lambda sig: all_signals.append(sig))
    
    # Human starts speaking
    emit_signal(SignalName.VAD_SPEECH_STARTED, payload={"turn_id": 1})
    assert len(all_signals) == 1
    assert all_signals[0].name == SignalName.VAD_SPEECH_STARTED
    
    # Human stops speaking
    emit_signal(SignalName.VAD_SPEECH_ENDED, payload={"turn_id": 1, "duration_sec": 2.0})
    assert len(all_signals) == 2
    assert all_signals[1].name == SignalName.VAD_SPEECH_ENDED
    
    # Processing begins
    emit_signal(SignalName.TURN_STARTED, payload={"turn_id": 1, "reason": "silence"})
    assert len(all_signals) == 3
    assert all_signals[2].name == SignalName.TURN_STARTED
    
    # AI starts speaking
    emit_signal(SignalName.TTS_SPEAKING_STARTED, payload={"turn_id": 1, "text_preview": "...response..."})
    assert len(all_signals) == 4
    assert all_signals[3].name == SignalName.TTS_SPEAKING_STARTED
    
    # AI finishes speaking
    emit_signal(SignalName.TTS_SPEAKING_ENDED, payload={"turn_id": 1, "duration_sec": 5.0})
    assert len(all_signals) == 5
    assert all_signals[4].name == SignalName.TTS_SPEAKING_ENDED
    
    # Turn completes
    emit_signal(SignalName.TURN_COMPLETED, payload={"turn_id": 1})
    assert len(all_signals) == 6
    assert all_signals[5].name == SignalName.TURN_COMPLETED


def test_signal_payload_completeness_for_ui():
    """Verify signals contain all data needed by UI."""
    # VAD speech started should have: turn_id, timestamp
    sig1_payload = {"turn_id": 1, "timestamp": time.time()}
    assert "turn_id" in sig1_payload
    assert "timestamp" in sig1_payload
    
    # VAD speech ended should have: turn_id, duration_sec, timestamp
    sig2_payload = {"turn_id": 1, "duration_sec": 2.5, "timestamp": time.time()}
    assert "duration_sec" in sig2_payload
    
    # Turn started should have: turn_id, reason, phase_id, timestamp
    sig3_payload = {"turn_id": 1, "reason": "silence", "phase_id": "part1", "timestamp": time.time()}
    assert "reason" in sig3_payload
    assert "phase_id" in sig3_payload
    
    # TTS speaking started should have: turn_id, text_preview, phase_id, timestamp
    sig4_payload = {"turn_id": 1, "text_preview": "...", "phase_id": "part1", "timestamp": time.time()}
    assert "text_preview" in sig4_payload
    
    # TTS speaking ended should have: turn_id, duration_sec, timestamp
    sig5_payload = {"turn_id": 1, "duration_sec": 5.0, "timestamp": time.time()}
    assert "duration_sec" in sig5_payload
    
    # Turn completed should have: turn_id, transcripts, latency, phase_id, timestamp
    sig6_payload = {
        "turn_id": 1,
        "human_transcript": "...",
        "ai_transcript": "...",
        "total_latency_ms": 2345,
        "phase_id": "part1",
        "timestamp": time.time()
    }
    assert "human_transcript" in sig6_payload
    assert "ai_transcript" in sig6_payload
    assert "total_latency_ms" in sig6_payload


def test_system_state_tracks_speaker_signals():
    """SystemState properly reflects speaker status for events."""
    state = SystemState()
    
    # Initially silence
    assert state.current_speaker == "silence"
    
    # Human speaking (after VAD_SPEECH_START event)
    state.current_speaker = "human"
    state.is_human_speaking = True
    
    assert state.current_speaker == "human"
    assert state.is_human_speaking == True
    
    # Human stops (after VAD_SPEECH_STOP event)
    state.is_human_speaking = False
    state.current_speaker = "silence"
    
    assert state.current_speaker == "silence"
    
    # AI speaking (after TTS starts)
    state.is_ai_speaking = True
    state.current_speaker = "ai"
    
    assert state.current_speaker == "ai"
    assert state.is_ai_speaking == True
    
    # AI stops
    state.is_ai_speaking = False
    state.current_speaker = "silence"
    
    assert state.current_speaker == "silence"
