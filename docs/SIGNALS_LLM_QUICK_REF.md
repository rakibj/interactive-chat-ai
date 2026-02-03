# LLM Signals - Quick Reference

## What Are Signals?

Signals are **optional structured observations** that LLM can emit at the end of responses to describe what happened in the conversation.

**Key**: Signals describe, they don't act. They're for external listeners only.

---

## For LLM Developers

### Format

```
<signals>
{
  "signal.name": {
    "param1": value,
    "param2": value
  }
}
</signals>
```

### Examples

**Single signal:**

```
I'd be willing to go down to $400.

<signals>
{"negotiation.counteroffer_made": {"confidence": 0.88, "price": 400}}
</signals>
```

**Multiple signals:**

```
Your name is Alex and email is alex@example.com?

<signals>
{
  "intake.user_data_collected": {"confidence": 0.95, "fields": ["name", "email"]},
  "conversation.answer_complete": {"confidence": 0.89}
}
</signals>
```

**No signals (valid):**

```
That's an interesting point. Tell me more?
```

---

## Profile Signals

### negotiator

- `negotiation.counteroffer_made` - User made a counter-offer
- `negotiation.objection_raised` - User raised an objection
- `conversation.answer_complete` - User completed their turn

### ielts_instructor

- `exam.question_asked` - Examiner asked a question
- `exam.response_received` - Candidate responded
- `exam.fluency_observation` - Observation about fluency
- `conversation.answer_complete` - Candidate completed answer

### confused_customer

- `conversation.user_confused` - Customer expressed confusion
- `customer_service.clarification_needed` - Clarification requested
- `conversation.answer_complete` - Customer completed turn

### technical_support

- `support.issue_identified` - Support identified the issue
- `support.solution_offered` - Solution offered
- `support.escalation_needed` - Escalation required
- `conversation.answer_complete` - Agent completed response

### language_tutor

- `language_learning.vocabulary_introduced` - New vocab introduced
- `language_learning.grammar_note` - Grammar feedback given
- `conversation.answer_complete` - Student completed response

### curious_friend

- `conversation.shared_interest` - Found shared interest
- `conversation.follow_up_question` - Following up naturally
- `conversation.answer_complete` - Friend completed their turn

---

## For System Integrators

### Automatic Signal Emission

When you enable signal emission in LLM:

```python
llm.stream_completion(messages, max_tokens, temperature, emit_signals=True)
```

The system automatically:

1. Emits `llm.generation_start` signal
2. Yields tokens to caller
3. Emits `llm.generation_complete` signal
4. **Extracts signals from response** ← NEW
5. Emits any found signals with their payloads

### Listening to Signals

```python
from core.signals import get_signal_registry

def my_listener(event):
    if event.type != "SIGNAL_EMITTED":
        return

    print(f"Signal: {event.name}")
    print(f"Data: {event.payload}")
    # Your logic here

registry = get_signal_registry()
registry.register_all(my_listener)
```

### Built-in Consumer

Default consumer logs all signals to stdout:

```
[SIGNAL] 2026-02-03T14:17:45.093548
  Name:    negotiation.counteroffer_made
  Payload: {
            "confidence": 0.92,
            "price": 400
}
  Context: {
            "source": "llm_response",
            "backend": "groq"
}
```

---

## Implementation Details

### Files Modified

- `interactive_chat/config.py` - System prompt + profile signals
- `interactive_chat/interfaces/llm.py` - Signal extraction + emission
- `interactive_chat/main.py` - Consumer registration
- `interactive_chat/signals/consumer.py` - NEW consumer implementation
- `interactive_chat/signals/__init__.py` - NEW package

### Signal Extraction

Happens automatically in `stream_completion()`:

1. Full response collected while tokens are yielded
2. `extract_signals_from_response()` searches for `<signals>...</signals>` block
3. JSON parsed (malformed JSON silently ignored)
4. Each signal emitted via `emit_signal()`

### Signal Flow

```
LLM Response → stream_completion()
    ↓
Collect response text + yield tokens
    ↓
emit(llm.generation_complete)
    ↓
extract_signals_from_response()
    ↓
For each signal:
    emit(signal_name, payload, context)
    ↓
SignalRegistry dispatches to listeners
    ↓
Each listener called independently
```

---

## Common Patterns

### Pattern 1: Confidence Scoring

```json
{
  "intake.user_data_collected": {
    "confidence": 0.92,
    "fields": ["name", "email"]
  }
}
```

### Pattern 2: Conditional Information

```json
{
  "conversation.answer_complete": {
    "confidence": 0.84,
    "needs_followup": true,
    "topic": "pricing"
  }
}
```

### Pattern 3: Multi-Part Information

```json
{
  "support.issue_identified": {
    "confidence": 0.89,
    "category": "software",
    "severity": "high"
  }
}
```

### Pattern 4: Multiple Signals

```json
{
  "intake.user_data_collected": {
    "confidence": 0.95,
    "fields": ["name", "email"]
  },
  "conversation.answer_complete": {
    "confidence": 0.88
  },
  "conversation.shared_interest": {
    "confidence": 0.72,
    "interest": "photography"
  }
}
```

---

## Testing

Run test suite:

```bash
python test_signal_implementation.py
```

Expected output:

```
TEST 1: Config.py signal descriptions ✅
TEST 2: LLM signal extraction ✅
TEST 3: Signal consumer ✅
TEST 4: Signal registry ✅

ALL TESTS PASSED ✅
```

---

## Troubleshooting

### Signals not emitted?

- Check `emit_signals=True` in LLM call
- Verify LLM response includes `<signals>...</signals>` block
- Ensure JSON is valid (use JSONLint if unsure)

### Listener not called?

- Verify event.type == "SIGNAL_EMITTED"
- Check listener registered with registry
- Ensure no exceptions in listener (will be caught but logged)

### Malformed JSON ignored?

- This is intentional - prevents LLM output issues from crashing core
- Check your JSON syntax in `<signals>` block
- Remove trailing commas, ensure all keys quoted

### Performance impact?

- Negligible - signals are non-blocking
- Listener exceptions isolated, don't affect core
- Optional - can be disabled with `emit_signals=False`

---

## References

- [Signals Architecture Guide](../docs/SIGNALS_REFERENCE.md)
- [Implementation Guide](../docs/SIGNALS_LLM_IMPLEMENTATION.md)
- [Full Summary](../docs/SIGNALS_LLM_IMPLEMENTATION_SUMMARY.md)
- Test: `test_signal_implementation.py`
