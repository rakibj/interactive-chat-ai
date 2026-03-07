# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands use `uv run` as the package manager.

**Run the application:**
```bash
uv run python -m interactive_chat.main
uv run python interactive_chat/run_with_profile.py  # interactive profile selector
```

**Run tests:**
```bash
uv run pytest tests/ -v                            # all tests
uv run pytest tests/test_headless_*.py tests/test_signal*.py -v  # unit tests only
uv run pytest tests/test_phase*.py -v              # phase tests only
uv run pytest tests/test_api_endpoints.py -v       # API tests only
uv run pytest tests/test_file.py::TestClass::test_name -v  # single test
uv run pytest tests/ --cov=interactive_chat --cov-report=term-missing  # with coverage
```

**Run live integration tests (starts real servers):**
```bash
uv run python tests/test_integration_api_live.py
uv run python tests/test_integration_phase_api_live.py
```

**Lint:**
```bash
uv run ruff check .
uv run ruff format .
```

## Architecture

### Core Event-Driven Loop

The system is a **pure event-driven state machine**. The flow is:

```
AudioManager → Events → Reducer.reduce(state, event) → (new_state, actions) → Action Handlers
```

- **`core/event_driven_core.py`**: Defines `SystemState` (single source of truth), `Event`/`EventType`, `Action`/`ActionType`, and the `Reducer` class with a pure `reduce(state, event) -> (state, [actions])` function. The reducer is side-effect-free.
- **`main.py`**: `ConversationEngine` — runs the event loop, dispatches events to the Reducer, and executes the returned `Action` objects (speak, interrupt, log, etc.).

### Configuration & Profiles

`config.py` is the single source of configuration truth. Key concepts:

- **`InstructionProfile`** (Pydantic): A single-phase conversation persona with turn-taking params (`pause_ms`, `end_ms`, `authority`), TTS voice, LLM settings, and optional `signals` dict.
- **`PhaseProfile`** (Pydantic): A multi-phase conversation container. Holds multiple `InstructionProfile`s, a `transitions` list, and an `initial_phase`. Phase transitions are signal-driven.
- **`ACTIVE_PROFILE`** / **`ACTIVE_PHASE_PROFILE`**: Module-level vars that select which profile/phase-profile is active at startup.
- `authority` controls mic behavior: `"human"` = open mic always, `"ai"` = mic closed when AI is speaking.

### Signals Architecture

Signals are **observations only** — they never mutate state or cause side effects directly.

- **`core/signals.py`**: Defines `SignalName` enum, `Signal` dataclass, `SignalRegistry` (a pub/sub listener registry), and `emit_signal()`.
- **`interfaces/llm.py`**: The LLM can embed a `<signals>` JSON block at the end of its response. `extract_signals_from_response()` parses this and emits the signals.
- **`signals/consumer.py`**: Example signal consumer that logs `custom.*` signals only.
- Phase transitions are triggered by signals: `PhaseProfile.find_transition(current_phase, emitted_signals)` checks if any emitted signal matches a `PhaseTransition.trigger_signals` list.

### API Layer

- **`server.py`**: FastAPI app with REST endpoints (`/api/state`, `/api/chat`, `/api/reset`, etc.) and WebSocket streaming (`/ws/{session_id}`). Serves the demo dashboard.
- **`api/session_manager.py`**: Manages multi-client WebSocket sessions with TTL (30min) and per-IP limits.
- **`api/event_buffer.py`**: Per-session ring buffer for WebSocket event delivery.
- **`api/models.py`**: All Pydantic request/response models.
- `server.set_engine(engine)` registers the `ConversationEngine` instance with the API.

### Interfaces

All three interfaces are abstract base classes with swappable implementations:

- **`interfaces/asr.py`**: `VoskASR` (streaming partials, low-latency) + `WhisperLocalASR` / `WhisperCloudASR` (turn-end transcription). `TURN_END_ASR_MODE` in config selects cloud vs local.
- **`interfaces/llm.py`**: `LocalLLM` (llama.cpp), `GroqLLM`, `DeepSeekLLM`, `OpenAILLM`. Selected by `LLM_BACKEND` in config.
- **`interfaces/tts.py`**: `PocketTTS` (neural, 6 voices) or `PowerShellTTS` (Windows fallback). Selected by `TTS_MODE` in config.

### Test Setup

`tests/conftest.py` mocks `sounddevice`, `torch`, and some utilities globally so hardware-dependent code can be imported in CI without audio devices. When adding new tests, do not import hardware modules directly — rely on the mocks already set up in `conftest.py`.

Tests in `tests/utils/` are standalone debug/utility scripts, not part of the automated pytest suite.
