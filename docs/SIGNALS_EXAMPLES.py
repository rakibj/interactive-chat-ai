"""
Example: Common Signal Listener Patterns

This file demonstrates ready-to-use patterns for integrating with the signals system.
Copy and adapt these examples to your use case.
"""

from core.signals import get_signal_registry, Signal
import json
import time
from typing import Callable


# =============================================================================
# PATTERN 1: Analytics Export
# =============================================================================

class AnalyticsExporter:
    """Export turn metrics to external database."""
    
    def __init__(self, database_connection):
        self.db = database_connection
        self.registry = get_signal_registry()
        self.registry.register("analytics.turn_metrics_updated", self.on_turn_complete)
    
    def on_turn_complete(self, signal: Signal):
        """Called when a turn completes."""
        metrics = signal.payload
        
        # Transform payload to database schema
        row = {
            "turn_id": metrics["turn_id"],
            "timestamp": metrics["timestamp"],
            "human_transcript": metrics["final_transcript"],
            "ai_transcript": metrics["ai_transcript"],
            "total_latency_ms": metrics["total_latency_ms"],
            "interrupts_accepted": metrics["interrupt_accepts"],
            "end_reason": metrics["end_reason"],
        }
        
        # Insert into database (or queue for batch)
        self.db.insert("conversation_turns", row)


# =============================================================================
# PATTERN 2: Real-Time Webhooks
# =============================================================================

class WebhookIntegration:
    """Send signals to external webhook endpoint."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.registry = get_signal_registry()
        # Listen to specific signals
        self.registry.register("conversation.interrupted", self.on_interrupted)
        self.registry.register("conversation.speaking_limit_exceeded", self.on_limit_exceeded)
    
    def on_interrupted(self, signal: Signal):
        """Alert when user interrupts AI."""
        import requests
        payload = {
            "event": "interruption",
            "reason": signal.payload.get("reason"),
            "timestamp": time.time(),
        }
        # Send async to avoid blocking main loop
        requests.post(self.webhook_url, json=payload, timeout=2)
    
    def on_limit_exceeded(self, signal: Signal):
        """Alert when speaking limit exceeded."""
        import requests
        payload = {
            "event": "speaking_limit_exceeded",
            "limit_sec": signal.payload.get("limit_sec"),
            "duration_sec": signal.payload.get("actual_duration_sec"),
        }
        requests.post(self.webhook_url, json=payload, timeout=2)


# =============================================================================
# PATTERN 3: Conversation Transcript Logger
# =============================================================================

class TranscriptLogger:
    """Build and save conversation transcripts."""
    
    def __init__(self, output_file: str):
        self.output_file = output_file
        self.transcript = []
        self.registry = get_signal_registry()
        self.registry.register("analytics.turn_metrics_updated", self.on_turn_complete)
    
    def on_turn_complete(self, signal: Signal):
        """Log turn to transcript file."""
        metrics = signal.payload
        
        # Build turn record
        turn = {
            "turn_id": metrics["turn_id"],
            "human": metrics["final_transcript"],
            "ai": metrics["ai_transcript"],
            "duration_ms": metrics["total_latency_ms"],
        }
        
        self.transcript.append(turn)
        
        # Save incrementally to avoid data loss
        with open(self.output_file, "w") as f:
            json.dump(self.transcript, f, indent=2)


# =============================================================================
# PATTERN 4: Adaptive Configuration Tuning
# =============================================================================

class AdaptiveTuner:
    """Automatically adjust settings based on conversation metrics."""
    
    def __init__(self, config):
        self.config = config
        self.registry = get_signal_registry()
        self.registry.register_all(self.on_any_signal)
        
        self.interrupt_stats = {"blocked": 0, "accepted": 0}
    
    def on_any_signal(self, signal: Signal):
        """Monitor all signals and adjust config."""
        
        if signal.name == "analytics.turn_metrics_updated":
            metrics = signal.payload
            
            # Track interruption patterns
            self.interrupt_stats["accepted"] += metrics["interrupt_accepts"]
            self.interrupt_stats["blocked"] += (
                metrics["interrupt_attempts"] - metrics["interrupt_accepts"]
            )
            
            # Adaptive tuning: if many interrupts are blocked, reduce sensitivity
            if self.interrupt_stats["blocked"] > 10:
                new_sensitivity = max(0.0, self.config.INTERRUPTION_SENSITIVITY - 0.1)
                print(f"[TUNER] Reducing sensitivity from {self.config.INTERRUPTION_SENSITIVITY} to {new_sensitivity}")
                self.config.INTERRUPTION_SENSITIVITY = new_sensitivity
                self.interrupt_stats["blocked"] = 0  # Reset counter
            
            # If very quick turnaround, user is engaged - increase timeout
            if metrics["total_latency_ms"] < 500:
                new_timeout = min(5000, self.config.SAFETY_TIMEOUT_MS + 200)
                print(f"[TUNER] Increasing timeout to {new_timeout}ms (user engaged)")
                self.config.SAFETY_TIMEOUT_MS = new_timeout


# =============================================================================
# PATTERN 5: Performance Monitoring
# =============================================================================

class PerformanceMonitor:
    """Track and alert on performance issues."""
    
    def __init__(self, latency_threshold_ms: float = 2000):
        self.threshold = latency_threshold_ms
        self.registry = get_signal_registry()
        self.registry.register("llm.generation_start", self.on_llm_start)
        self.registry.register("llm.generation_complete", self.on_llm_complete)
        self.registry.register("analytics.turn_metrics_updated", self.on_turn_complete)
        
        self.slow_turns = []
    
    def on_llm_start(self, signal: Signal):
        """LLM generation started."""
        print(f"[PERF] LLM generation starting ({signal.payload['backend']})")
    
    def on_llm_complete(self, signal: Signal):
        """LLM generation completed."""
        print(f"[PERF] LLM generation complete ({signal.payload['tokens_generated']} tokens)")
    
    def on_turn_complete(self, signal: Signal):
        """Check turn latency."""
        latency = signal.payload["total_latency_ms"]
        
        if latency > self.threshold:
            self.slow_turns.append(signal.payload)
            print(f"[WARN] Slow turn detected: {latency}ms (threshold: {self.threshold}ms)")
            
            # Could alert here, log to monitoring system, etc.
            if len(self.slow_turns) > 5:
                print(f"[ALERT] Multiple slow turns detected! Check system performance.")


# =============================================================================
# PATTERN 6: Rule Engine (Declarative Automation)
# =============================================================================

class SimpleRuleEngine:
    """Execute rules based on signals."""
    
    def __init__(self):
        self.rules = []
        self.registry = get_signal_registry()
        self.registry.register_all(self._on_signal)
    
    def add_rule(self, signal_name: str, condition: Callable, action: Callable):
        """
        Add a rule: "When signal_name occurs AND condition is true, execute action"
        
        Example:
            engine.add_rule(
                "analytics.turn_metrics_updated",
                lambda sig: sig.payload["end_reason"] == "limit_exceeded",
                lambda sig: send_email("User exceeded speaking limit")
            )
        """
        self.rules.append({
            "signal": signal_name,
            "condition": condition,
            "action": action,
        })
    
    def _on_signal(self, signal: Signal):
        """Evaluate all rules for this signal."""
        for rule in self.rules:
            if rule["signal"] == signal.name or rule["signal"] == "*":
                try:
                    if rule["condition"](signal):
                        rule["action"](signal)
                except Exception as e:
                    print(f"[ERROR] Rule execution failed: {e}")


# =============================================================================
# PATTERN 7: Testing Helper
# =============================================================================

class SignalCapture:
    """Capture signals during tests."""
    
    def __init__(self):
        self.signals = []
        self.registry = get_signal_registry()
        self.registry.register_all(lambda sig: self.signals.append(sig))
    
    def get_signals_by_name(self, name: str):
        """Get all signals with given name."""
        return [s for s in self.signals if s.name == name]
    
    def assert_signal_emitted(self, name: str):
        """Assert that signal was emitted."""
        if not any(s.name == name for s in self.signals):
            raise AssertionError(f"Signal '{name}' was not emitted")
    
    def assert_signal_count(self, name: str, count: int):
        """Assert signal emission count."""
        actual = len(self.get_signals_by_name(name))
        if actual != count:
            raise AssertionError(f"Signal '{name}': expected {count}, got {actual}")


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    """Example of setting up multiple listeners."""
    
    # Initialize (in your main.py)
    registry = get_signal_registry()
    
    # 1. Export analytics
    class MockDB:
        def insert(self, table, row):
            print(f"[DB] Inserted into {table}: {row}")
    
    exporter = AnalyticsExporter(MockDB())
    
    # 2. Monitor performance
    monitor = PerformanceMonitor(latency_threshold_ms=1500)
    
    # 3. Create rules
    rule_engine = SimpleRuleEngine()
    rule_engine.add_rule(
        "conversation.interrupted",
        lambda sig: sig.payload.get("reason") == "speech_detected",
        lambda sig: print("[RULE] Speech interrupt detected!")
    )
    rule_engine.add_rule(
        "analytics.turn_metrics_updated",
        lambda sig: sig.payload.get("end_reason") == "limit_exceeded",
        lambda sig: print("[RULE] Speaking limit was exceeded!")
    )
    
    # 4. Test helper
    capture = SignalCapture()
    
    print("Listeners registered:")
    print(f"  Total listeners: {registry.get_listener_count()}")
    print("\nEmit a sample signal...")
    
    # Simulate signal emission
    from core.signals import emit_signal
    
    emit_signal(
        "analytics.turn_metrics_updated",
        payload={
            "turn_id": 1,
            "timestamp": time.time(),
            "final_transcript": "Hello world",
            "ai_transcript": "Hello back!",
            "total_latency_ms": 1200,
            "interrupt_accepts": 0,
            "interrupt_attempts": 0,
            "end_reason": "silence",
        }
    )
    
    print(f"\nCapture test: {len(capture.signals)} signals captured")
