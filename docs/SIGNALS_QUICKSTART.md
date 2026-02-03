# Signals Architecture - Quick Start Guide

## What Was Added?

A **complete, generic signals system** that lets external code (plugins, integrations, automations) react to system events **without modifying core logic**.

### Key Principle: Signals are Observations

```python
# Core engine NEVER changes state based on signals
# Core engine ALWAYS works even if no listeners exist
# Listeners are completely OPTIONAL and DECOUPLED
```

---

## 5-Minute Setup

### Step 1: Import

```python
from core.signals import get_signal_registry, emit_signal

registry = get_signal_registry()
```

### Step 2: Register Listener

```python
def on_turn_complete(signal):
    print(f"Turn {signal.context['turn_id']} complete!")
    metrics = signal.payload
    # Do something: export, webhook, log, etc.

registry.register("analytics.turn_metrics_updated", on_turn_complete)
```

### Step 3: Done!

Your listener will be called automatically when a turn completes.

---

## All Emitted Signals

| Signal                                 | When                | Source  | Key Payload               |
| -------------------------------------- | ------------------- | ------- | ------------------------- |
| `conversation.interrupted`             | User interrupts AI  | Reducer | `reason`, `turn_id`       |
| `conversation.speaking_limit_exceeded` | User talks too long | Reducer | `limit_sec`, `actual_sec` |
| `llm.generation_start`                 | LLM begins          | LLM     | `model`, `backend`        |
| `llm.generation_complete`              | LLM finishes        | LLM     | `tokens_generated`        |
| `llm.generation_error`                 | LLM fails           | LLM     | `error`                   |
| `analytics.turn_metrics_updated`       | Turn ends           | Reducer | 12+ metrics               |

Plus: `custom.*` for anything you want to emit.

---

## Common Patterns (Copy-Paste Ready)

### Export to Database

```python
def export_to_db(signal):
    db.insert("turns", signal.payload)

registry.register("analytics.turn_metrics_updated", export_to_db)
```

### Send Webhook

```python
import requests

def send_alert(signal):
    requests.post("https://myapp.com/webhook", json=signal.payload)

registry.register("conversation.interrupted", send_alert)
```

### Monitor Performance

```python
def check_latency(signal):
    if signal.payload["total_latency_ms"] > 2000:
        print(f"Slow turn: {signal.payload['total_latency_ms']}ms")

registry.register("analytics.turn_metrics_updated", check_latency)
```

### Listen to Everything

```python
def monitor_all(signal):
    print(f"[{signal.name}] {signal.payload}")

registry.register_all(monitor_all)  # All signals
```

---

## Files to Read

1. **Quick Overview**: [SIGNALS_REFERENCE.md](SIGNALS_REFERENCE.md) (Top section)
2. **Full Details**: [SIGNALS_REFERENCE.md](SIGNALS_REFERENCE.md) (Complete)
3. **Code Examples**: [SIGNALS_EXAMPLES.py](SIGNALS_EXAMPLES.py) (7 ready-to-use patterns)
4. **Implementation**: [SIGNALS_IMPLEMENTATION_SUMMARY.md](SIGNALS_IMPLEMENTATION_SUMMARY.md)

---

## Key Points

✅ **No Breaking Changes**: Existing code continues to work exactly as before

✅ **Zero Overhead**: If you don't register listeners, there's no performance impact

✅ **Error Safe**: Listener errors are caught; core engine unaffected

✅ **Deterministic**: State transitions identical with or without signals

✅ **Extensible**: Add custom signals and listeners for any workflow

---

## What NOT to Do

❌ Don't mutate core state in a listener (it won't affect things)
❌ Don't block in a listener (use threading for long ops)
❌ Don't assume signal ordering (they're independent)
❌ Don't emit signals that control behavior (that's Actions, not Signals)

---

## Troubleshooting

**Listener not being called?**

```python
registry = get_signal_registry()
print(registry.get_listener_count("analytics.turn_metrics_updated"))
```

**Want to test?**

```python
# Run the test suite
python tests/test_signals_integration.py
```

**Still confused?**

```python
# Start here: listen to everything
registry.register_all(lambda sig: print(f"{sig.name}: {sig.payload}"))
# Run conversation, see what signals exist
```

---

## Next: Full Details

Start with [SIGNALS_REFERENCE.md](SIGNALS_REFERENCE.md) for comprehensive guide.

See [SIGNALS_EXAMPLES.py](SIGNALS_EXAMPLES.py) for 7 production-ready patterns.

Then implement your integration!
