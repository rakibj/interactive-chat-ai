# Headless Testing - Quick Start Guide

## TL;DR

✅ **YES - Headless testing is fully possible and already working**

The event-driven architecture is perfect for automated testing without audio/TTS/APIs.

---

## Run Tests Right Now

```bash
# No dependencies needed - just Python
cd d:\Work\Projects\AI\interactive-chat-ai
python tests/test_headless_standalone.py
```

**Expected Output:**
```
Total:  16 ✅
Passed: 16 ✅
Failed: 0 ❌
```

---

## What Can Be Tested (Headless)

### ✅ Can Test Without Audio/APIs
- ✅ State machine transitions (IDLE → SPEAKING → PAUSING)
- ✅ Authority mode logic (human, ai, default)
- ✅ Interruption detection
- ✅ Action generation
- ✅ Event processing
- ✅ Profile configurations
- ✅ Timing logic (TICK events)
- ✅ Queue management
- ✅ Edge cases (timeouts, limits)

### ❌ Cannot Test (Need Real Audio/APIs)
- ❌ Actual audio capture/playback
- ❌ ASR transcription accuracy
- ❌ TTS voice quality
- ❌ LLM response generation
- ❌ Network latency
- ❌ System resource usage

---

## Test Structure

```
Tests/
├── test_headless_standalone.py      ← Run this now (no pytest needed)
│   └── 16 tests: 4 levels, all passing ✅
│
├── test_headless_comprehensive.py   ← For pytest (more detailed)
│   └── 40+ tests with fixtures
│
├── HEADLESS_TESTING_GUIDE.md        ← Strategy & patterns
└── HEADLESS_TESTING_SUMMARY.md      ← This document
```

---

## 4-Level Test Pyramid

```
Level 4: Edge Cases (4 tests)
├─ Safety timeout
├─ Human speaking limit
├─ Rapid transitions
└─ ...

Level 3: Profiles (2 tests)
├─ IELTS Instructor (AI authority)
└─ Negotiator (Human authority)

Level 2: Integration (2 tests)
├─ Complete turn flow
└─ Interrupt sequence

Level 1: Unit (8 tests)
├─ State transitions (3)
├─ Authority modes (4)
└─ Actions (1)
```

---

## Quick Test Examples

### Test 1: State Transition
```python
# IDLE → SPEAKING when user starts talking
state = SystemState(state_machine="IDLE")
state, actions = Reducer.reduce(state, Event(EventType.VAD_SPEECH_START))
assert state.state_machine == "SPEAKING"
assert state.is_human_speaking == True
```

### Test 2: Authority Mode
```python
# AI authority: no interruptions
state = SystemState(authority="ai", is_ai_speaking=True)
state, actions = Reducer.reduce(
    state,
    Event(EventType.AUDIO_FRAME, payload={"is_speech": True})
)
# Should NOT interrupt
assert not any(a.type == ActionType.INTERRUPT_AI for a in actions)
```

### Test 3: Complete Turn
```python
# User speaks → pauses → turn ends → processing
state = SystemState(authority="human")

# Speak
state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_START))
assert state.state_machine == "SPEAKING"

# Pause
state, _ = Reducer.reduce(state, Event(EventType.VAD_SPEECH_STOP))

# Wait for end
state, actions = Reducer.reduce(
    state,
    Event(EventType.TICK, timestamp=current_time + 1.5)
)

# Should process
assert any(a.type == ActionType.PROCESS_TURN for a in actions)
```

---

## Coverage Goals

| Level | Tests | Coverage | Time |
|-------|-------|----------|------|
| L1: Unit | 8+ | 70% | 20h |
| L2: Integration | 2+ | 85% | 15h |
| L3: Profiles | 3+ | 90% | 12h |
| L4: Edge Cases | 4+ | 95% | 12h |
| **TOTAL** | **17+** | **95%** | **60h** |

---

## How to Expand

### Add Unit Test
```python
def test_my_feature():
    state = SystemState(...)
    state, actions = Reducer.reduce(state, Event(...))
    # Assertions here
    assert_something(state)
    assert_action_generated(actions)
```

### Add Integration Test
```python
def test_user_flow():
    state = SystemState(...)
    
    # Step 1
    state, _ = Reducer.reduce(state, Event(...))
    
    # Step 2
    state, actions = Reducer.reduce(state, Event(...))
    
    # Verify final state
    assert state.state_machine == "IDLE"
```

### Add Profile Test
```python
def test_my_profile():
    state = SystemState(
        authority="human",        # Profile setting
        interruption_sensitivity=0.8,  # Profile setting
        safety_timeout_ms=2500    # Profile setting
    )
    # ... rest of test
```

---

## Files to Read

| File | Purpose | Read Time |
|------|---------|-----------|
| [HEADLESS_TESTING_SUMMARY.md](HEADLESS_TESTING_SUMMARY.md) | Implementation status | 5 min |
| [HEADLESS_TESTING_GUIDE.md](HEADLESS_TESTING_GUIDE.md) | Detailed strategy | 20 min |
| [test_headless_standalone.py](tests/test_headless_standalone.py) | Working code | 15 min |
| [test_headless_comprehensive.py](tests/test_headless_comprehensive.py) | Pytest examples | 15 min |

---

## Next Steps

### Immediate (Today)
1. ✅ Run `python tests/test_headless_standalone.py`
2. ✅ See 16/16 tests pass
3. ✅ Read HEADLESS_TESTING_GUIDE.md

### Short-term (This Week)
1. Add 10-15 more unit tests
2. Reach 30 tests, 75% coverage
3. Set up local test running

### Medium-term (This Month)
1. Add integration + profile tests
2. Reach 50+ tests, 90% coverage
3. Add to CI/CD pipeline

### Long-term (Ongoing)
1. Maintain test suite as code evolves
2. Add regression tests for bugs found
3. Document test patterns for team

---

## Architecture Benefits for Testing

### Pure Function Reducer
```python
# Same input → same output
# No external dependencies
# Perfect for unit testing
state, actions = Reducer.reduce(state, event)
```

### Immutable Events
```python
@dataclass(frozen=True)
class Event:
    type: EventType
    timestamp: float
    payload: Dict[str, Any]
    # Easy to construct, easy to verify
```

### Explicit Actions
```python
@dataclass(frozen=True)
class Action:
    type: ActionType
    payload: Dict[str, Any]
    # Clear what should happen
```

### Isolated State
```python
@dataclass
class SystemState:
    # Single source of truth
    # Easy to inspect after each step
    # No hidden global state
```

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Single test | <1ms | Pure function |
| 16 tests | ~20ms | Batch run |
| 50+ tests | ~50ms | Comprehensive suite |
| 100+ tests | ~100ms | Full coverage |

**vs Real System:**
- Real conversation turn: 1500-2500ms
- Headless test: <1ms
- **Speedup: 1500-2500x faster**

---

## FAQ

**Q: Do I need audio hardware?**  
A: No. Headless tests only use pure functions.

**Q: Do I need TTS/ASR/LLM running?**  
A: No. Those are system under test, not test harness.

**Q: Can I test profiles?**  
A: Yes. Profile tests verify configuration correctness.

**Q: How much coverage can I get?**  
A: 85-95% of event-driven core logic.

**Q: Can I test audio timing?**  
A: Yes, with TICK events (simulated time).

**Q: How long to build full suite?**  
A: ~60 hours to reach 95% coverage.

**Q: Can I use pytest?**  
A: Yes, or just Python (no dependencies needed).

**Q: What about interruption race conditions?**  
A: Testable with sequenced events and state inspection.

**Q: How do I debug a failing test?**  
A: Inspect state before/after each event.

---

## Key Takeaways

1. ✅ **Fully Feasible** - Event-driven design enables headless testing
2. ✅ **Already Working** - 16 tests proven passing
3. ✅ **Scalable** - Can grow to 100+ tests easily
4. ✅ **Fast** - Milliseconds per test
5. ✅ **Reliable** - Deterministic, no flakiness
6. ✅ **Cost-effective** - No infrastructure needed
7. ✅ **Team-friendly** - Easy to understand patterns
8. ✅ **CI/CD-ready** - Perfect for automation

---

## Get Started Now

```bash
# 1. Run existing tests
python tests/test_headless_standalone.py

# 2. Read strategy
cat HEADLESS_TESTING_GUIDE.md

# 3. Create first new test
# (copy test_human_authority_interrupts pattern)

# 4. Run your test
python tests/test_headless_standalone.py
```

That's it! You're now headless testing.

---

Generated: February 3, 2026
