# Code Review Report

**Date:** 2026-03-07
**Scope:** Full codebase review — `interactive_chat/` package
**Reviewer:** Claude Code

---

## Executive Summary

The codebase has a solid high-level design: a pure event-driven reducer at the core, a clean signals pub/sub layer, and well-separated interfaces for ASR/LLM/TTS. The main concerns are (1) thread-safety — mutable state is shared across many threads without locks, (2) meaningful code duplication between `main.py` and `llm.py`, (3) several bugs that silently produce wrong behavior, and (4) structural issues in `main.py` that make it very large and hard to maintain. Issues are ranked **High / Medium / Low** by impact.

---

## High Priority

### H1 — `SystemState` mutated in-place violates the reducer contract
**File:** `core/event_driven_core.py`, `main.py`

`SystemState` is a plain mutable `@dataclass`. The `Reducer.reduce()` method mutates it directly and returns the same object. This means the "old state" and "new state" are the same reference, making it impossible to compare before/after, roll back, or safely read from another thread while the reducer is running. The frozen `Event` and `Action` types suggest immutability was intended throughout.

**Action:** Either document that the reducer mutates in-place by design and ensure only one thread ever calls it, or switch `SystemState` to produce copies (`dataclasses.replace(state, field=new_value)`).

---

### H2 — No lock on `SystemState` — concurrent mutation from multiple threads
**Files:** `main.py`

`self.state` is read and written from at least five concurrent threads:
- Audio producer (`_audio_producer`)
- ASR worker (`_start_asr_worker`)
- TTS worker (`_tts_worker`)
- LLM response thread (`_generate_ai_turn`, `_process_turn_async`)
- Main event loop (`run()`)
- FastAPI request handlers (via `_engine.state`)

There is no lock, mutex, or queue mediating access. Fields like `is_ai_speaking`, `turn_audio_buffer`, `ai_speech_queue`, and `current_speaker` are written and read from different threads, creating race conditions.

**Action:** Introduce a `threading.Lock` (or use the event queue as the single mutation point) so all state writes go through one thread. The API endpoints should take a snapshot copy under lock rather than read live state.

---

### H3 — `get_asr()` factory ignores `TURN_END_ASR_MODE` config
**File:** `interfaces/asr.py:203`, `config.py:33`

`HybridASR.__init__()` always instantiates `WhisperLocalASR` regardless of the `TURN_END_ASR_MODE` setting (`"local"` or `"cloud"`). The config option is imported in `asr.py` but never consulted in the factory. Setting `TURN_END_ASR_MODE = "cloud"` in `config.py` has no effect.

**Action:** Change `HybridASR.__init__` to check `TURN_END_ASR_MODE` and instantiate `WhisperCloudASR` when `"cloud"` is set.

```python
# asr.py — HybridASR.__init__
self.turnend = WhisperCloudASR() if TURN_END_ASR_MODE == "cloud" else WhisperLocalASR()
```

---

### H4 — Broken absolute imports inside the package
**File:** `main.py:277`, `main.py:443`

Two import statements use absolute paths that work only when running from the project root, not when the package is installed or run via `python -m interactive_chat`:

- `main.py:277` — `from utils.audio import float32_to_int16` inside `_audio_producer`
- `main.py:443` — `from core.analytics import TurnAnalytics` inside `_handle_action`

These should be relative imports:

```python
from .utils.audio import float32_to_int16
from .core.analytics import TurnAnalytics
```

**Action:** Fix both imports and move them to the top of the file.

---

### H5 — Duplicate signal parsing logic
**Files:** `main.py:836–920`, `interfaces/llm.py:38–144`

`main.py` contains `_extract_signals()` + `_parse_signal_json()`, and `llm.py` contains `extract_signals_from_response()` + `_parse_signal_block_json()`. Both implement the same three-strategy JSON parsing approach with nearly identical code. The two copies can diverge.

**Action:** Delete `_extract_signals()` and `_parse_signal_json()` from `main.py`. Call the already-tested `extract_signals_from_response()` from `llm.py` instead, and get signal names with `.keys()`.

---

## Medium Priority

### M1 — `ACTIVE_PHASE_PROFILE` assigned twice in `config.py`
**File:** `config.py:170–171`

```python
ACTIVE_PHASE_PROFILE: Optional[str] = None   # line 170
ACTIVE_PHASE_PROFILE = "name_age_test"         # line 171
```

The `None` default is immediately overwritten on the next line, which is confusing and suggests this is a forgotten cleanup. Developers changing the active profile must delete line 171.

**Action:** Remove the redundant `None` assignment and leave only the active value. Add a comment explaining the toggle pattern.

---

### M2 — `conversation_history` attribute referenced but never defined on `SystemState`
**File:** `server.py:192`

`get_conversation_history()` calls `getattr(state, 'conversation_history', [])` but `SystemState` has no `conversation_history` field. The actual turn data lives in `message_history_by_phase`. This endpoint always returns an empty list in production.

**Action:** Either remove the endpoint (it appears unused), or rewrite it to build the turn list from `message_history_by_phase` and the current `conversation_memory`.

---

### M3 — `EventBuffer._cleanup_old_ids()` called only once, `event_ids` set grows unboundedly
**File:** `api/event_buffer.py:46–48`

`_cleanup_old_ids()` is only invoked when the buffer is exactly at `max_size`. For every batch of `max_size` events added after that, the `event_ids` set retains stale IDs of evicted events, so it can grow to `2 × max_size` without being cleaned. The deduplication check remains correct (stale IDs just cause false-negative dedup hits for long-gone events), but the set is always larger than necessary.

**Action:** Call `_cleanup_old_ids()` on every `add_event` when the buffer is full (i.e., when `len(self.events) >= self.max_size` before appending), not after.

---

### M4 — `time.sleep(0.5)` blocks the action handler in phase transitions
**File:** `main.py:576`

`_transition_to_phase()` calls `time.sleep(0.5)` before generating the AI greeting. This sleep happens on whatever thread invokes `_handle_action()`. If called from the main event loop, it blocks event processing for 500ms. If called from a background thread it is benign but still implicit.

**Action:** Move the delay into `_generate_ai_turn()` or use `threading.Timer` to decouple it.

---

### M5 — `PLAY_ACK` speaks without the interrupt event
**File:** `main.py:404`

`_handle_action(PLAY_ACK)` calls `self.tts.speak(ack)` without passing `interrupt_event=self.human_interrupt_event`. An acknowledgment sound cannot be cut short if the user starts speaking during playback.

**Action:** Pass `interrupt_event=self.human_interrupt_event` consistently.

---

### M6 — `PowerShellTTS` ignores `interrupt_event`
**File:** `interfaces/tts.py:82`

`PowerShellTTS.speak()` accepts an `interrupt_event` parameter but never checks it. The method blocks for the full `subprocess.run` duration (up to the 10s timeout).

**Action:** Either remove the parameter from `PowerShellTTS` (it cannot interrupt a subprocess easily), or split into background start + polling loop and check the event periodically.

---

### M7 — `HybridASR.reset()` does not reset the turn-end ASR
**File:** `interfaces/asr.py:219`

`HybridASR.reset()` only calls `self.realtime.reset()` (Vosk). `self.turnend` (Whisper) has no reset method, which is fine — but if a `WhisperCloudASR` or future stateful `TurnEndASR` is used, it would be silently skipped.

**Action:** Document that `TurnEndASR` is stateless by design, or add an optional `reset()` to the `TurnEndASR` ABC.

---

### M8 — Module-level `_cloud_clients` cache is not thread-safe
**File:** `interfaces/llm.py:348–358`

```python
_cloud_clients = {}

def get_llm():
    if LLM_BACKEND not in _cloud_clients:
        _cloud_clients[LLM_BACKEND] = CloudLLM(LLM_BACKEND)
    return _cloud_clients[LLM_BACKEND]
```

Two threads calling `get_llm()` simultaneously for the same backend will both see the key missing and both create a `CloudLLM`, with one overwriting the other. This is a benign race in practice (both clients work), but it is also wasteful.

**Action:** Use `threading.Lock` or initialize the cache at import time.

---

### M9 — `_audio_callback` not protected by `self.lock`
**File:** `core/audio_manager.py:62–66`

`_audio_callback` appends to `self.audio_buffer` (a plain `list`) without acquiring `self.lock`. `get_audio_chunk()` pops from the same list under `self.lock`. These two code paths can interleave on different threads.

**Action:** Acquire `self.lock` inside `_audio_callback`, or replace `audio_buffer` with a `queue.Queue` (which is thread-safe by design).

---

### M10 — Signal stripping regex inconsistency
**Files:** `main.py:411–412`, `main.py:801`

Two different regexes are used for stripping `<signals>` blocks from text:

- `SPEAK_SENTENCE` handler: `r'<signals.*?</signals>'` with `re.DOTALL`
- `_generate_ai_turn` cleanup: `r"<signals>\s*\{.*?\}\s*</signals>"` with `re.DOTALL`

The second pattern requires the block to start with `{`, which would miss a signals block that starts with whitespace or any other character before the JSON. The first pattern is more correct.

**Action:** Define one module-level constant `SIGNALS_BLOCK_RE = re.compile(r'<signals>.*?</signals>', re.DOTALL)` and use it everywhere.

---

## Low Priority

### L1 — Inline imports inside methods
**File:** `main.py` (multiple locations)

`import re`, `import json`, `import traceback`, `import random` appear inside method bodies (`_audio_producer`, `_handle_action`, `_generate_ai_turn`, `_extract_signals`, `_process_turn_async`). Python caches module lookups, so this is harmless but makes imports invisible at file top.

**Action:** Move all imports to the top of `main.py`.

---

### L2 — `_start_stream()` return value silently ignored
**File:** `core/audio_manager.py:68–103`

`_start_stream()` returns `True` on success and `False` (implicitly, via `init_error["error"] is None`) but the return value is never captured in `__init__`. The error state is inferred later from `self.stream is None`.

**Action:** Remove the return value from `_start_stream()` or check it in `__init__` for consistency.

---

### L3 — `SystemState` has two redundant phase ID fields
**File:** `core/event_driven_core.py:70–74`

`current_phase_id` and `active_phase_id` appear to hold the same value. Both are updated together in `_transition_to_phase()` (lines 551–552). The comment says `# Keep these in sync`, confirming the redundancy. This creates risk of divergence.

**Action:** Remove `active_phase_id` and rename all usages to `current_phase_id`, or vice versa.

---

### L4 — `ai_speech_duration_sec` is always `0` in analytics
**File:** `main.py:452`

`TurnAnalytics` is constructed with `ai_speech_duration_sec=0` because TTS duration is not tracked. This field is always logged as zero, making the analytics data misleading.

**Action:** Either capture TTS playback duration in `PocketTTS.speak()` and pass it back, or mark the field as `Optional` and log `None` when unavailable.

---

### L5 — `sentence_count` variable serves no purpose beyond debug logs
**File:** `main.py` (`_generate_ai_turn`, `_process_turn_async`)

`sentence_count` is incremented per emitted sentence and printed at the end, but is never returned, stored, or used for logic.

**Action:** Remove or inline it into the log message (`f"✅ AI turn: {i} sentences"`).

---

### L6 — Single-word ASR hallucination filter may reject valid short responses
**File:** `main.py:945–947`

```python
if len(words) == 1 and len(words[0]) <= 3:
    return
```

This rejects valid single-word responses like "Yes", "No", "OK", "Hi" (3 chars or fewer). "Yes" is 3 characters and would be silently dropped.

**Action:** Raise the threshold to `<= 2` characters, or replace with a list of known noise tokens (`["uh", "um", "mm"]`).

---

### L7 — `_cloud_clients` cache prevents API key rotation without restart
**File:** `interfaces/llm.py:347–358`

Once a `CloudLLM` is cached, it uses the API key that was set at construction time. If `OPENAI_API_KEY` changes (e.g., in tests or multi-tenant use), the cached client will continue using the old key.

**Action:** Document this limitation or accept a `force_refresh` parameter in `get_llm()`.

---

### L8 — `vad_stability_threshold = 1` comment is misleading
**File:** `main.py:241`

The comment says "Reduce to 1 frame for faster response (32ms)" but `vad_stability_threshold` gates a counter incremented on *state change*, not on every frame. With a threshold of 1, any single transition triggers immediately — the debounce does nothing.

**Action:** Clarify the comment or document that debouncing is intentionally disabled.

---

## Summary Table

| ID | Severity | File | Description |
|----|----------|------|-------------|
| H1 | High | `event_driven_core.py` | Reducer mutates state in-place, breaking immutability contract |
| H2 | High | `main.py` | No lock on `SystemState` — concurrent write races |
| H3 | High | `interfaces/asr.py` | `TURN_END_ASR_MODE="cloud"` config is ignored by factory |
| H4 | High | `main.py` | Two broken absolute imports inside methods |
| H5 | High | `main.py`, `interfaces/llm.py` | Signal parsing logic duplicated in full |
| M1 | Medium | `config.py` | `ACTIVE_PHASE_PROFILE` assigned twice |
| M2 | Medium | `server.py` | `conversation_history` endpoint returns empty list always |
| M3 | Medium | `api/event_buffer.py` | `event_ids` set grows unboundedly |
| M4 | Medium | `main.py` | `time.sleep(0.5)` blocks action handler thread |
| M5 | Medium | `main.py` | ACK playback ignores interrupt event |
| M6 | Medium | `interfaces/tts.py` | `PowerShellTTS` ignores interrupt event |
| M7 | Medium | `interfaces/asr.py` | `HybridASR.reset()` skips turn-end ASR |
| M8 | Medium | `interfaces/llm.py` | Module-level client cache has no thread safety |
| M9 | Medium | `core/audio_manager.py` | Audio callback not protected by lock |
| M10 | Medium | `main.py` | Two different signal-strip regexes used inconsistently |
| L1 | Low | `main.py` | Imports scattered inside methods |
| L2 | Low | `core/audio_manager.py` | `_start_stream()` return value ignored |
| L3 | Low | `core/event_driven_core.py` | `current_phase_id` / `active_phase_id` are redundant duplicates |
| L4 | Low | `main.py` | `ai_speech_duration_sec` always logged as 0 |
| L5 | Low | `main.py` | `sentence_count` variable unused beyond debug print |
| L6 | Low | `main.py` | Short ASR filter drops valid 3-char responses ("Yes", "No") |
| L7 | Low | `interfaces/llm.py` | Cloud LLM client cache prevents API key rotation |
| L8 | Low | `main.py` | `vad_stability_threshold=1` comment claims debounce that isn't active |

---

## Recommended Fix Order

1. **H4** — Fix broken imports first (required for any test/run to work correctly)
2. **H3** — Fix `TURN_END_ASR_MODE` being ignored (affects all cloud users)
3. **H5** + **M10** — Deduplicate signal parsing and unify the strip regex
4. **H2** + **H1** — Add a state mutation lock (start with a coarse lock on the event loop, then refine)
5. **M1** — Clean up `config.py` double assignment
6. **M2** — Fix or remove the broken conversation history endpoint
7. **M3** — Fix `EventBuffer` ID set growth
8. **M5**, **M6** — Pass interrupt events consistently through TTS calls
