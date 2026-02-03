"""
Signals Architecture: Generic, extensible signaling system for the event-driven core.

Signals describe observations about what just happened. They do not act, mutate state,
or cause side effects directly. The engine emits signals; consumers decide what to do.

Core Principles:
- Signals describe, they do not act
- Signals never mutate core state directly
- Signals never cause side effects directly
- Signals are optional and ignorable
- The system works even if no one listens

Signal Naming Convention:
    <domain>.<state_or_observation>

Examples:
    - conversation.user_confused
    - intake.user_data_collected
    - conversation.turn_complete
    - llm.generation_start
    - analytics.turn_metrics_updated
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Callable, List, Optional
import json
from enum import Enum


class SignalName(str, Enum):
    """Canonical signal names emitted by the engine."""
    
    # Conversation domain
    CONVERSATION_USER_CONFUSED = "conversation.user_confused"
    CONVERSATION_TURN_COMPLETE = "conversation.turn_complete"
    CONVERSATION_INTERRUPTED = "conversation.interrupted"
    CONVERSATION_SPEAKING_LIMIT_EXCEEDED = "conversation.speaking_limit_exceeded"
    SPEAKER_CHANGED = "conversation.speaker_changed"
    
    # VAD domain (NEW: Critical for demo UI)
    VAD_SPEECH_STARTED = "vad.speech_started"
    VAD_SPEECH_ENDED = "vad.speech_ended"
    
    # TTS domain (NEW: Critical for demo UI)
    TTS_SPEAKING_STARTED = "tts.speaking_started"
    TTS_SPEAKING_ENDED = "tts.speaking_ended"
    
    # Turn domain (NEW: Critical for demo UI)
    TURN_STARTED = "turn.started"
    TURN_COMPLETED = "turn.completed"
    
    # LLM domain
    LLM_GENERATION_START = "llm.generation_start"
    LLM_GENERATION_COMPLETE = "llm.generation_complete"
    LLM_GENERATION_ERROR = "llm.generation_error"
    LLM_SIGNAL_RECEIVED = "llm.signal_received"
    
    # Analytics domain
    ANALYTICS_TURN_METRICS = "analytics.turn_metrics_updated"
    ANALYTICS_SESSION_SUMMARY = "analytics.session_summary"
    
    # Phase domain
    PHASE_TRANSITION_TRIGGERED = "phase.transition_triggered"
    PHASE_TRANSITION_STARTED = "phase.transition_started"
    PHASE_TRANSITION_COMPLETE = "phase.transition_complete"
    PHASE_PROGRESS_UPDATED = "phase.progress_updated"
    
    # Custom domain (for user extensions)
    CUSTOM_PREFIX = "custom."


@dataclass(frozen=True)
class Signal:
    """
    A Signal is a named, structured observation about what just happened.
    
    Signals are immutable and carry:
    - name: Signal identifier (string or SignalName enum)
    - payload: Arbitrary JSON payload with signal-specific data
    - context: Metadata about where signal came from (source, turn_id, timestamp, etc.)
    """
    
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary for serialization."""
        return {
            "name": self.name,
            "payload": self.payload,
            "context": self.context,
        }
    
    def to_json(self) -> str:
        """Convert signal to JSON string."""
        return json.dumps(self.to_dict())


@dataclass(frozen=True)
class SignalEmittedEvent:
    """
    Event wrapper for signals in the main event loop.
    
    This preserves the canonical event shape:
    {
      "type": "SIGNAL_EMITTED",
      "name": "conversation.user_confused",
      "payload": {...},
      "context": {...}
    }
    """
    
    type: str = "SIGNAL_EMITTED"
    name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def from_signal(signal: Signal) -> "SignalEmittedEvent":
        """Create event from signal."""
        return SignalEmittedEvent(
            type="SIGNAL_EMITTED",
            name=signal.name,
            payload=signal.payload,
            context=signal.context,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "name": self.name,
            "payload": self.payload,
            "context": self.context,
        }


class SignalRegistry:
    """
    Central registry for signal listeners.
    
    Enables decoupled consumption of signals:
    - Listeners register callbacks per signal name
    - emit() broadcasts to all registered listeners
    - No core logic knows about listeners; listeners are optional
    
    Usage:
        registry = SignalRegistry()
        registry.register("conversation.turn_complete", lambda sig: print(sig))
        registry.emit(Signal("conversation.turn_complete", payload={"turn_id": 1}))
    """
    
    def __init__(self):
        """Initialize empty listener registry."""
        self._listeners: Dict[str, List[Callable[[Signal], None]]] = {}
        self._global_listeners: List[Callable[[Signal], None]] = []
    
    def register(self, signal_name: str, callback: Callable[[Signal], None]) -> None:
        """
        Register a listener for a specific signal.
        
        Args:
            signal_name: Signal identifier (e.g., "conversation.turn_complete")
            callback: Function that receives Signal object
        """
        if signal_name not in self._listeners:
            self._listeners[signal_name] = []
        self._listeners[signal_name].append(callback)
    
    def register_all(self, callback: Callable[[Signal], None]) -> None:
        """
        Register a listener for ALL signals (wildcard).
        
        Useful for analytics, logging, or monitoring that wants to see everything.
        
        Args:
            callback: Function that receives Signal object
        """
        self._global_listeners.append(callback)
    
    def emit(self, signal: Signal) -> None:
        """
        Emit a signal to all registered listeners (non-blocking).
        
        Listeners are called synchronously in registration order.
        If any listener raises an exception, it is logged but does not affect
        other listeners or the core engine.
        
        Args:
            signal: Signal to emit
        """
        # Call global listeners first
        for callback in self._global_listeners:
            try:
                callback(signal)
            except Exception as e:
                # Log but do not raise; listener errors must not crash core
                print(f"⚠️  Signal listener error for {signal.name}: {e}")
        
        # Call signal-specific listeners
        if signal.name in self._listeners:
            for callback in self._listeners[signal.name]:
                try:
                    callback(signal)
                except Exception as e:
                    print(f"⚠️  Signal listener error for {signal.name}: {e}")
    
    def get_listener_count(self, signal_name: Optional[str] = None) -> int:
        """
        Get count of registered listeners.
        
        Args:
            signal_name: Specific signal, or None for total count
        
        Returns:
            Number of listeners
        """
        if signal_name:
            return len(self._listeners.get(signal_name, []))
        total = len(self._global_listeners)
        for listeners in self._listeners.values():
            total += len(listeners)
        return total
    
    def clear(self) -> None:
        """Clear all registered listeners (useful for testing)."""
        self._listeners.clear()
        self._global_listeners.clear()


# Global signal registry (singleton)
# Instantiate once at module load; the main engine holds a reference to this
_signal_registry: Optional[SignalRegistry] = None


def get_signal_registry() -> SignalRegistry:
    """Get or create the global signal registry."""
    global _signal_registry
    if _signal_registry is None:
        _signal_registry = SignalRegistry()
    return _signal_registry


def emit_signal(
    name: str,
    payload: Dict[str, Any] = None,
    context: Dict[str, Any] = None,
) -> None:
    """
    Convenience function to emit a signal via the global registry.
    
    Args:
        name: Signal name (e.g., "conversation.turn_complete")
        payload: Signal-specific data (optional)
        context: Metadata like source, turn_id, timestamp (optional)
    """
    signal = Signal(
        name=name,
        payload=payload or {},
        context=context or {},
    )
    get_signal_registry().emit(signal)
