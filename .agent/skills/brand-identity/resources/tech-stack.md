# Preferred Tech Stack & Implementation Rules

When generating code or components for this project, you **MUST** strictly adhere to the following technology choices and architectural patterns.

## Core Stack
* **Language:** Python 3.11+ (type hints required)
* **Audio Processing:** NumPy, sounddevice (16kHz, 512-sample frames)
* **VAD:** Silero VAD (PyTorch-based)
* **ASR:** Vosk (streaming), Faster-Whisper (final transcription)
* **TTS:** Pocket-TTS (primary), PowerShell TTS (fallback)
* **LLM:** llama.cpp (local), OpenAI/Groq/DeepSeek APIs (cloud)
* **Configuration:** Pydantic models with validation
* **Logging:** Structured JSONL analytics

## Implementation Guidelines

### 1. Threading Model
* **Main Thread:** Audio processing loop only (16kHz, 512-sample frames)
* **TTS Worker:** Consumes response queue, manages `ai_speaking` flag
* **ASR Worker:** Updates partial transcripts for interruption detection
* **Synchronization:** Use `threading.Event` for interruption signaling, `queue.Queue` for TTS sentences
* **Race Conditions:** Always set flags BEFORE queueing work, double-check state after async operations

### 2. Audio Processing Patterns
* **Frame Size:** 512 samples (32ms @ 16kHz) - matches Silero VAD requirements
* **Format:** float32 normalized [-1, 1]
* **Buffering:** Use `collections.deque` with maxlen for fixed-size audio buffers
* **VAD:** Silero threshold 0.5, energy floor 0.015 RMS
* **Streaming:** Process audio in real-time, never block the audio callback

### 3. State Management
* **Pydantic Models:** All configuration via `BaseModel` subclasses with validators
* **Enums:** Use `Enum` for states (e.g., `TurnState.SPEAKING`, `TurnState.PAUSING`)
* **Immutability:** Configuration objects are read-only after initialization
* **Authority Modes:** `human`, `ai`, `default` - controls interruption and mic behavior

### 4. Code Organization
* **Interfaces:** Abstract base classes in `interfaces/` (ASR, LLM, TTS)
* **Core Logic:** State machines and managers in `core/` (turn_taker, interruption_manager, audio_manager)
* **Configuration:** Centralized in `config.py` with `InstructionProfile` dataclass
* **Analytics:** Structured logging via `core/analytics.py` (JSONL format)

### 5. Naming Conventions
* **Files:** `snake_case.py`
* **Classes:** `PascalCase` (e.g., `AudioManager`, `TurnTaker`)
* **Functions/Methods:** `snake_case()` (e.g., `detect_speech()`, `should_interrupt()`)
* **Constants:** `UPPER_SNAKE_CASE` (e.g., `SAMPLE_RATE`, `FRAME_SIZE`)
* **Private Methods:** `_leading_underscore()` for internal use

### 6. Error Handling
* **Graceful Degradation:** Fall back to PowerShell TTS if Pocket-TTS fails
* **Logging:** Use `print()` with emoji prefixes for user-facing logs (e.g., `🎤`, `🤖`, `⚡`)
* **Validation:** Pydantic catches config errors at startup, not runtime
* **Timeouts:** Always have safety timeouts for turn-taking (default 2500ms)

### 7. Performance Requirements
* **Latency:** Total user → AI response must be under 2500ms
* **Streaming:** LLM tokens streamed sentence-by-sentence to TTS queue
* **Model Loading:** Pre-load all models at startup (VAD, Vosk, Whisper, TTS)
* **Thread Count:** Torch configured for 8 threads max

## Forbidden Patterns
* Do NOT use `asyncio` (conflicts with sounddevice blocking I/O)
* Do NOT use global mutable state (pass state via method arguments or class attributes)
* Do NOT block the audio callback thread (offload work to queues/workers)
* Do NOT use `time.sleep()` in audio processing (breaks real-time guarantees)
* Do NOT hardcode file paths (use `pathlib.Path` with relative imports)

## Testing Patterns
* **Unit Tests:** Mock audio I/O, test state machines in isolation
* **Integration Tests:** Use `MockTTS` with deterministic timing
* **Simulation:** Inject fake audio/transcripts to test interruption logic
* **Analytics:** Validate JSONL output structure and summary calculations
