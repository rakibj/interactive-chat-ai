"""Standalone signal consumer for logging and observation (non-core functionality).

This module demonstrates how to extend the system with signal listeners
without coupling to core event-driven logic.

The consumer is registered optionally and can be removed without affecting
core behavior (signals remain optional).
"""
import json
from typing import Any, Dict
from datetime import datetime


def handle_signal(signal: Any) -> None:
    """
    Log a signal emission to stdout without affecting core logic.
    
    Only logs custom.* signals defined in profile signals dict.
    Ignores all other signals to reduce noise.
    
    Args:
        signal: Signal object with name, payload, and context
    """
    # Signal object has name, payload, context attributes
    signal_name = getattr(signal, 'name', 'unknown')
    
    # Filter: only print custom signals (profile-defined signals from config)
    # Skip all other signals (exam.*, conversation.*, analytics.*, llm.*)
    if not signal_name.startswith('custom.'):
        return
    
    signal_payload = getattr(signal, 'payload', {})
    signal_context = getattr(signal, 'context', {})
    
    # Format timestamp
    timestamp = datetime.now().isoformat()
    
    # Pretty-print the signal with emoji marker
    print(f"\n📡 CUSTOM SIGNAL [{timestamp}]")
    print(f"   Name:    {signal_name}")
    if signal_payload:
        print(f"   Payload: {json.dumps(signal_payload, indent=14)}")
    if signal_context:
        print(f"   Context: {json.dumps(signal_context, indent=14)}")
