# Signals Architecture Reference

## Overview

The Interactive Chat AI system implements a **generic, extensible signaling system** where:

- **Signals describe observations**, they do not act
- **Core engine remains deterministic** and unaware of listeners
- **Side effects are decoupled** from the core logic
- **External developers can listen and react** without modifying core code
- **System works even if no one listens** (signals are completely optional)

## Core Principles (Non-Negotiable)

1. ✅ Signals describe, they do not act
2. ✅ Signals never mutate core state directly
3. ✅ Signals never cause side effects directly
4. ✅ Signals are optional and ignorable
5. ✅ The engine emits signals; consumers decide what to do

**If any of these break, determinism is compromised.**

---

## What Is a Signal?

A **Signal** is a named, structured observation about what just happened or what seems to be true, emitted by the system or the LLM.

### Examples of Signals

```
- conversation.user_confused
- conversation.turn_complete
- conversation.interrupted
- conversation.speaking_limit_exceeded
- llm.generation_start
- llm.generation_complete
- llm.generation_error
- llm.signal_received
- analytics.turn_metrics_updated
- custom.acme_ready_for_export
```

### What Signals Are NOT

Signals are **not**:

- **Actions** (send_mail, end_turn, play_sound)
- **Commands** (next_phase, force_end)
- **Bookkeeping** (increment_counter, update_state)
- **Control flow** (if/else, routing)

Those belong to **Actions**, which are separate from signals.

---

## Signal Naming Convention

All signals use a **namespaced string format**:

```
<domain>.<state_or_observation>
```

### Examples

```
conversation.user_confused
intake.user_data_collected
sales.lead_qualified
custom.my_app_event
```

This avoids collisions and enables extension.

---

## Signal Event Shape (Canonical)

All signals are emitted with a consistent structure:

```python
{
    "type": "SIGNAL_EMITTED",
    "name": "conversation.turn_complete",
    "payload": {
        "turn_id": 3,
        "duration_ms": 2500,
        "human_transcript": "...",
        "ai_transcript": "..."
    },
    "context": {
        "source": "reducer",
        "turn_id": 3,
        "authority": "default"
    }
}
```

### Fields

| Field     | Type   | Description                                                 |
| --------- | ------ | ----------------------------------------------------------- |
| `type`    | string | Always `"SIGNAL_EMITTED"` (canonical event type)            |
| `name`    | string | Signal identifier (e.g., `"conversation.turn_complete"`)    |
| `payload` | dict   | Signal-specific data (arbitrary JSON)                       |
| `context` | dict   | Metadata: `source`, `turn_id`, `timestamp`, etc. (optional) |

---

## All Emitted Signals

### Conversation Domain

#### `conversation.interrupted`

**Emitted when**: AI speech is interrupted by user

**Source**: `event_driven_core.py` Reducer, AUDIO_FRAME event

**Payload**:

```python
{
    "reason": "speech_detected",  # or "energy_spike", "confidence_high"
    "turn_id": 3,
    "authority": "default"  # or "human", "ai"
}
```

**Use Case**: Log interruptions, analyze conversation flow, trigger UI feedback

---

#### `conversation.speaking_limit_exceeded`

**Emitted when**: User's speaking duration exceeds configured limit

**Source**: `event_driven_core.py` Reducer, TICK event

**Payload**:

```python
{
    "limit_sec": 45,
    "actual_duration_sec": 47.3,
    "turn_id": 5
}
```

**Use Case**: Analytics, adaptive timeout tuning, conversation metrics

---

#### `conversation.user_confused` (Future)

**Intended for**: LLM confidence signals indicating user confusion

**Payload** (planned):

```python
{
    "confidence": 0.85,
    "indicators": ["repeated_questions", "clarification_requests"]
}
```

---

### LLM Domain

#### `llm.generation_start`

**Emitted when**: LLM begins streaming response

**Source**: `interfaces/llm.py` LocalLLM/CloudLLM.stream_completion()

**Payload**:

```python
{
    "model": "qwen2.5-3b",  # or llama-3.1-70b, gpt-4o-mini, etc.
    "backend": "local"  # or "groq", "openai", "deepseek"
}
```

**Use Case**: Performance monitoring, latency tracking, debugging

---

#### `llm.generation_complete`

**Emitted when**: LLM finishes streaming response

**Source**: `interfaces/llm.py` LocalLLM/CloudLLM.stream_completion()

**Payload**:

```python
{
    "tokens_generated": 80,
    "backend": "groq"
}
```

**Use Case**: Token counting, cost tracking, performance analytics

---

#### `llm.generation_error`

**Emitted when**: LLM encounters an error during generation

**Source**: `interfaces/llm.py` LocalLLM/CloudLLM.stream_completion() exception handler

**Payload**:

```python
{
    "error": "Connection timeout",
    "backend": "openai"
}
```

**Use Case**: Error logging, fallback triggering, alerting

---

#### `llm.signal_received`

**Emitted when**: LLM response contains a `<signals>` block (future feature)

**Source**: `interfaces/llm.py` (post-processing of LLM output)

**Payload**:

```python
{
    "signal_name": "intake.user_data_collected",
    "signal_payload": {
        "confidence": 0.92,
        "fields": ["email", "name"]
    }
}
```

**Use Case**: Structured output handling, form extraction, workflow automation

---

### Analytics Domain

#### `analytics.turn_metrics_updated`

**Emitted when**: A turn completes and metrics are logged

**Source**: `event_driven_core.py` Reducer, RESET_TURN event

**Payload**:

```python
{
    "turn_id": 7,
    "timestamp": 1738515601.234,
    "interrupt_attempts": 2,
    "interrupt_accepts": 1,
    "partial_transcripts": ["what's", "what's your", "what's your best"],
    "final_transcript": "What's your best price?",
    "ai_transcript": "I can offer $79 per month.",
    "end_reason": "silence",  # or "safety_timeout", "limit_exceeded"
    "transcription_ms": 903.9,
    "llm_generation_ms": 366.7,
    "total_latency_ms": 1270.6,
    "confidence_score": 0.95
}
```

**Use Case**: Turn analytics, performance tuning, conversation replay, dashboards

---

#### `analytics.session_summary` (Future)

**Intended for**: End-of-session aggregated metrics

**Payload** (planned):

```python
{
    "session_id": "session_20260202_230800",
    "total_turns": 15,
    "session_duration_sec": 287.5,
    "avg_total_latency_ms": 1270.6,
    "interrupt_acceptance_rate": 0.75
}
```

---

### Custom Domain

#### `custom.*`

**Any developer can emit custom signals**:

```python
from core.signals import emit_signal

emit_signal(
    "custom.acme_ready_for_export",
    payload={"invoice_id": 12345, "amount": 500.00},
    context={"source": "custom_plugin"}
)
```

**Use Case**: Plugins, integrations, domain-specific observability

---

## Signal Sources

### 1. LLM (Soft Structured Output)

The LLM can optionally emit signals within its response:

```
Thanks, I have everything I need now.

<signals>
{
  "intake.user_data_collected": {
    "confidence": 0.9,
    "fields": ["email", "name"]
  }
}
</signals>
```

**Important**:

- LLM is **invited, not forced** to emit signals
- Malformed signals are **silently ignored**
- Missing signals are **fine** (no error)
- The main response text is unaffected

### 2. Heuristics / Engine Logic

Signals can come from:

- **Timers** (safety timeout, speaking limit)
- **Counters** (interruption attempts)
- **ASR/VAD logic** (speech detection, confidence)
- **State transitions** (turn complete, speaking limit exceeded)

Example:

```python
emit_signal(
    name="conversation.speaking_limit_exceeded",
    payload={"limit_sec": 45, "actual_duration_sec": 47.3}
)
```

**All sources are equivalent** — the engine doesn't care where a signal originated.

---

## Signal Emission (Engine Implementation)

All signals flow through a single emission path:

```python
# In core/signals.py
def emit_signal(name: str, payload: Dict[str, Any], context: Dict[str, Any]) -> None:
    signal = Signal(name=name, payload=payload, context=context)
    get_signal_registry().emit(signal)
```

### Key Properties

✅ **No consumer logic here**
✅ **No side effects here**
✅ **Deterministic and synchronous**
✅ **Listeners are optional**

---

## Signal Consumption (Decoupled Listeners)

Signals are **fan-out events**. Multiple consumers may listen independently.

### Registry Interface

```python
from core.signals import get_signal_registry

registry = get_signal_registry()

# Listen to specific signal
def on_turn_complete(signal):
    print(f"Turn {signal.context['turn_id']} complete!")
    # React (log, export, webhook, etc.)

registry.register("analytics.turn_metrics_updated", on_turn_complete)

# Listen to ALL signals
def on_any_signal(signal):
    print(f"Signal: {signal.name}")

registry.register_all(on_any_signal)
```

### Possible Consumers

- **Analytics dashboards** (collect metrics)
- **Export integrations** (CRM, Slack, webhooks)
- **Rule engines** (future phase logic)
- **Monitoring/alerting** (detect anomalies)
- **External plugins** (third-party extensions)
- **Testing frameworks** (verify behavior)

**None of these are mandatory.** The system is fully functional with zero listeners.

---

## Actions vs Signals (Critical Separation)

| Aspect             | Signal                           | Action                           |
| ------------------ | -------------------------------- | -------------------------------- |
| **Purpose**        | Observation                      | Side-effect                      |
| **Who Emits**      | LLM / Engine                     | Engine only                      |
| **Causes Effects** | ❌ No                            | ✅ Yes                           |
| **Example**        | `analytics.turn_metrics_updated` | `SPEAK_SENTENCE`, `INTERRUPT_AI` |

### Example Flow

```
1. Turn ends (RESET_TURN event)
2. Reducer emits LOG_TURN action (side effect)
3. Reducer emits analytics.turn_metrics_updated signal (observation)
4. Main loop handles LOG_TURN action (executes side effect)
5. Signal listeners receive signal (can react independently)
```

---

## How Email Fits (Canonical Pattern)

This is the **reference pattern** for all integrations:

```python
# 1. Signal is emitted by engine (automatic, no changes needed)
emit_signal(
    "analytics.turn_metrics_updated",
    payload={...metrics...}
)

# 2. External listener reacts (no core change)
def export_to_crm(signal):
    metrics = signal.payload
    crm.log_turn(metrics)

registry.register("analytics.turn_metrics_updated", export_to_crm)

# 3. Handler sends email / CRM API call
crm.log_turn(metrics)
```

### Why This Architecture

✅ **Core engine doesn't know email exists**
✅ **Core engine doesn't change state**
✅ **Core engine remains deterministic**
✅ **Any developer can add listeners without modifying core**

---

## Making This Generic for All Use Cases

This is **not case-specific** because:

1. **Signals are generic strings** (not enums or hardcoded values)
2. **Payloads are arbitrary JSON** (no schema enforcement in core)
3. **Consumers are external** (listeners are plugins, not core)
4. **No core logic changes required** (add listeners, leave engine alone)

Any developer can:

- Subscribe to signals via `registry.register()`
- Run their own logic in a listener
- Integrate any external system
- Add domain-specific signals via `custom.*` namespace

This is a **platform surface**, not an app hack.

---

## Implementation Details

### Signal Registry (core/signals.py)

```python
class SignalRegistry:
    def register(self, signal_name: str, callback: Callable) -> None:
        """Register listener for specific signal"""

    def register_all(self, callback: Callable) -> None:
        """Register listener for ALL signals"""

    def emit(self, signal: Signal) -> None:
        """Emit to all listeners (non-blocking, errors don't crash core)"""
```

### Error Handling

If a listener throws an exception:

- ✅ **Logged but not re-raised**
- ✅ **Other listeners still run**
- ✅ **Core engine unaffected**
- ✅ **Determinism preserved**

```python
# Inside SignalRegistry.emit()
for callback in listeners:
    try:
        callback(signal)
    except Exception as e:
        print(f"⚠️  Listener error: {e}")  # Log only, no raise
```

---

## Emission Points in Code

### Where Signals Are Emitted

1. **core/event_driven_core.py** (Reducer)
   - `RESET_TURN` event → `analytics.turn_metrics_updated`
   - `AUDIO_FRAME` event (interruption) → `conversation.interrupted`
   - `TICK` event (time checks) → `conversation.speaking_limit_exceeded`

2. **interfaces/llm.py** (LLM implementations)
   - Start streaming → `llm.generation_start`
   - Complete streaming → `llm.generation_complete`
   - Exception thrown → `llm.generation_error`
   - Signal block in response → `llm.signal_received`

3. **main.py** (main loop / action handlers)
   - Already receives signals from Reducer
   - Can emit custom signals if needed

---

## Configuration & Settings

### Enable/Disable Signals

Signals are **always emitted by default**. To ignore them:

```python
# Simply don't register any listeners
registry = get_signal_registry()
# Don't call registry.register() → no listeners

# Engine still emits, but nobody cares → determinism unaffected
```

### Listen to All Signals (Monitoring)

```python
def log_all_signals(signal: Signal):
    print(f"[{signal.name}] {signal.payload}")

registry.register_all(log_all_signals)
```

### Filter Signals

```python
def only_analytics(signal: Signal):
    if "analytics" in signal.name:
        print(f"Analytics: {signal.name}")

registry.register_all(only_analytics)
```

---

## Testing with Signals

### Unit Testing

```python
# Test that a signal is emitted (without side effects)
from core.signals import get_signal_registry

registry = get_signal_registry()
signals_received = []

registry.register("analytics.turn_metrics_updated",
    lambda sig: signals_received.append(sig))

# ... run engine code ...

assert len(signals_received) > 0
assert signals_received[0].payload["turn_id"] == 7
```

### Integration Testing

```python
# Mock listener to verify end-to-end behavior
def export_mock(signal):
    mock_crm.calls.append(signal.payload)

registry.register("analytics.turn_metrics_updated", export_mock)

# ... run conversation ...

assert len(mock_crm.calls) == 15  # One per turn
```

---

## Future Enhancements

### Phase 2: LLM Structured Output

```
Signals emitted from LLM response <signals> blocks:
- intake.user_data_collected
- conversation.user_confused
- conversation.clarification_needed
```

### Phase 3: Rule Engine

```python
# Declarative rules that react to signals
rule = Rule(
    when="analytics.turn_metrics_updated",
    if_payload={"end_reason": "limit_exceeded"},
    then="email_admin"
)
```

### Phase 4: Multi-Modal Signals

```
Signal sources expand to:
- Audio analysis (emotion, clarity)
- Facial expressions (if video)
- Conversation flow (turn-taking quality)
```

---

## Common Listener Patterns

### Pattern 1: Analytics Export

```python
def export_turn_to_bigquery(signal: Signal):
    """Export turn metrics to data warehouse"""
    row = {
        "turn_id": signal.context["turn_id"],
        "profile": signal.payload["profile"],
        "metrics": signal.payload,
    }
    bigquery.insert_rows_json(table, [row])

registry.register("analytics.turn_metrics_updated", export_turn_to_bigquery)
```

### Pattern 2: Webhook Integration

```python
def send_to_slack(signal: Signal):
    """Alert Slack on interruptions"""
    if signal.name == "conversation.interrupted":
        reason = signal.payload.get("reason")
        requests.post(SLACK_WEBHOOK, json={
            "text": f"Interruption: {reason}",
            "turn_id": signal.context["turn_id"]
        })

registry.register("conversation.interrupted", send_to_slack)
```

### Pattern 3: Conditional Logic

```python
def adaptive_tuning(signal: Signal):
    """Adjust interruption sensitivity based on metrics"""
    if signal.name == "analytics.turn_metrics_updated":
        if signal.payload["interrupts_blocked"] > 5:
            print("Sensitivity too high, reducing threshold")
            config.INTERRUPTION_SENSITIVITY -= 0.1

registry.register_all(adaptive_tuning)
```

### Pattern 4: Testing Assertions

```python
def test_interruption_flow():
    """Verify interruption behavior"""
    received_signals = []
    registry.register("conversation.interrupted",
        lambda sig: received_signals.append(sig))

    # Run conversation
    engine.run()

    # Assert signal was emitted
    assert any(s.payload["reason"] == "speech_detected"
               for s in received_signals)
```

---

## Best Practices

### ✅ DO

- Listen to signals for analytics and exports
- Emit custom signals from plugins
- Use signals for monitoring and debugging
- Filter signals in listeners by name or payload
- Log listener errors without raising
- Keep listeners stateless when possible

### ❌ DON'T

- Emit signals from listeners (can loop)
- Mutate core state in listeners
- Block signals in listeners (async if needed)
- Assume signal ordering (events can be concurrent)
- Use signals for control flow (that's Actions)
- Raise exceptions in listeners (catch and log)

---

## Troubleshooting

### Listener Not Called

```python
# Check if listener is registered
registry = get_signal_registry()
count = registry.get_listener_count("analytics.turn_metrics_updated")
print(f"Listeners: {count}")

# Verify signal name matches exactly
# (case-sensitive, use constants when possible)
```

### Listener Causing Slowdown

```python
# Listeners are synchronous; move heavy work to threads
def heavy_export(signal: Signal):
    threading.Thread(target=_do_export, args=(signal,), daemon=True).start()

def _do_export(signal: Signal):
    # Long-running operation doesn't block main loop
    bigquery.insert(...)
```

### Signal Not Appearing

```python
# Verify signal is emitted from core
registry.register_all(lambda sig: print(f"Got: {sig.name}"))

# Run engine and watch output
# If you don't see the signal, check:
# 1. Is listener registered? ✓
# 2. Is that code path executed? ✓ (add debug logs)
# 3. Is signal name spelled correctly? ✓
```

---

## API Reference

### SignalName Enum (core/signals.py)

```python
class SignalName(str, Enum):
    CONVERSATION_INTERRUPTED = "conversation.interrupted"
    CONVERSATION_SPEAKING_LIMIT_EXCEEDED = "conversation.speaking_limit_exceeded"
    LLM_GENERATION_START = "llm.generation_start"
    LLM_GENERATION_COMPLETE = "llm.generation_complete"
    LLM_GENERATION_ERROR = "llm.generation_error"
    ANALYTICS_TURN_METRICS = "analytics.turn_metrics_updated"
```

### Functions

```python
from core.signals import (
    emit_signal,              # Emit signal
    get_signal_registry,      # Get global registry
    Signal,                   # Signal dataclass
    SignalRegistry,           # Registry class
    SignalName                # Signal name enum
)

# Emit
emit_signal("custom.event", payload={...}, context={...})

# Register listener
registry = get_signal_registry()
registry.register("analytics.turn_metrics_updated", my_handler)
registry.register_all(my_universal_handler)

# Emit (via registry)
registry.emit(Signal("custom.event", {...}, {...}))
```

---

## Summary

The **Signals Architecture** provides:

✅ **Decoupled observability** without mutating core state
✅ **Platform surface** for plugins and integrations
✅ **Deterministic core** unaware of listeners
✅ **Zero overhead** if no listeners registered
✅ **Extensible by design** via `custom.*` namespace
✅ **Non-breaking** for existing code

Use signals to:

- Export data to external systems
- Build analytics dashboards
- Trigger webhooks and alerts
- Enable plugins and extensions
- Debug and monitor behavior
- Implement rule engines (future)

**The engine works perfectly without signals. Listeners are completely optional.**
