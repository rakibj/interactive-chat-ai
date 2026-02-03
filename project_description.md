# Interactive Chat AI - Project Summary

## Overview

A real-time voice conversation system with configurable AI personas, advanced interruption handling, and multi-modal ASR/TTS capabilities. Built for natural, low-latency human-AI voice interactions with sophisticated turn-taking logic.

## Technology Stack

### Core Dependencies

- **Python 3.10+** - Primary language
- **PyTorch** - VAD model inference
- **NumPy** - Audio processing
- **sounddevice** - Real-time audio I/O
- **Pydantic** - Configuration validation

### Speech Recognition (ASR)

- **Vosk** - Low-latency streaming ASR for real-time partial transcripts
- **Faster-Whisper** - High-accuracy local transcription (distil-small.en)
- **OpenAI Whisper API** - Cloud-based transcription (configurable)

### Text-to-Speech (TTS)

- **Pocket-TTS** - Neural voice synthesis (6 voices: alba, marius, javert, jean, fantine, cosette)
- **PowerShell TTS** - Windows fallback

### Voice Activity Detection (VAD)

- **Silero VAD** - PyTorch-based speech detection

### Language Models (LLM)

- **Local**: llama.cpp (GGUF models)
- **Cloud**: OpenAI, Groq, DeepSeek APIs

## Architecture

### Project Structure

```
interactive-chat-ai/
├── interactive_chat/
│   ├── main.py                 # Event dispatcher loop
│   ├── config.py               # Centralized configuration
│   ├── core/
│   │   ├── event_driven_core.py # Core state, events, and reducer
│   │   ├── audio_manager.py    # Audio I/O and VAD
│   │   ├── conversation_memory.py   # Chat history
│   │   └── analytics.py        # Telemetry
│   └── interfaces/
│       ├── asr.py              # ASR implementations
│       ├── llm.py              # LLM implementations
│       └── tts.py              # TTS implementations
├── models/                     # Local model storage
└── test_*.py                   # Test scripts
```

## Core Components

### 1. ConversationEngine (`main.py`)

**Purpose**: Orchestration engine based on an Event-Driven dispatcher loop.

**Key Responsibilities**:

- Running the Main Event Loop
- Executing Side-Effects (`Action`s)
- Coordinating asynchronous turn processing (transcription -> LLM -> TTS)
- Graceful shutdown management

**The Event Loop**:

```python
while not shutdown:
    event = event_queue.get()
    state, actions = Reducer.reduce(state, event)
    for action in actions:
        _handle_action(action)
```

### 2. Event-Driven Core (`core/event_driven_core.py`)

**Purpose**: Centralized business logic and state management.

**Components**:

- **SystemState**: Single source of truth (dataclass)
- **Event**: Standardized inputs (VAD, Audio, ASR, AI Status, TICK timer)
- **Action**: Deterministic side-effect triggers (Interrupt, ProcessTurn, Log)
- **Reducer**: Pure function for state transitions with explicit TICK event handler

**TICK Event Handler**:

- Drives state machine advancement without external input
- Advances time-based state transitions (e.g., PAUSING → IDLE)
- Enables safety timeout logic to function correctly
- Called continuously by main event loop to ensure responsive timing

### 2. AudioManager (`core/audio_manager.py`)

**Purpose**: Low-level audio I/O and speech detection.

**Key Methods**:

- `get_audio_chunk()`: Returns 512-sample frames at 16kHz
- `detect_speech(frame)`: Silero VAD inference (returns bool + RMS energy)
- `is_sustained_speech(energy_history)`: Energy-based speech confirmation

**VAD Configuration**:

- Threshold: 0.5 (Silero probability)
- Energy floor: 0.015 (RMS)
- Frame size: 512 samples (32ms @ 16kHz)

### 3. TurnTaker (`core/turn_taker.py`)

**Status**: ⚠️ **DEPRECATED** - Logic moved to Reducer.reduce() in event_driven_core.py

**Purpose**: State machine for turn-taking decisions.

**States**:

- `SILENCE`: No speech detected
- `SPEAKING`: Active speech
- `PAUSING`: Brief silence during speech
- `ENDING`: Extended silence, ready to end turn

**Timeouts** (configurable per profile):

- `pause_ms`: Max pause before state change (default: 600ms)
- `end_ms`: Silence duration to end turn (default: 1200ms)
- `safety_timeout_ms`: Force turn end (default: 2500ms)

**Confidence Scoring**:

- Uses partial ASR text length as heuristic
- Threshold: 1.2 (configurable)
- Prevents premature turn endings

**Migration Note**: This module is kept for backward compatibility but is no longer used. All state machine logic is now centralized in the event-driven core Reducer.

### 4. InterruptionManager (`core/interruption_manager.py`)

**Status**: ⚠️ **DEPRECATED** - Logic moved to Reducer.\_check_interruption() in event_driven_core.py

**Purpose**: Centralized interruption logic with authority modes.

**Authority Modes**:

- **`human`**: User has control, can interrupt immediately
- **`ai`**: AI has control, mic closes during AI speech
- **`default`**: Balanced, allows interruption but polite

**Sensitivity Levels** (0.0 - 1.0):

- **0.0 (Strict)**: Requires transcribed words to interrupt
- **0.5 (Hybrid)**: Energy spike OR words
- **1.0 (Energy-only)**: Sound detection alone triggers interrupt

**Key Methods**:

- `should_interrupt()`: Returns (bool, reason_string)
- `can_listen_continuously()`: Controls mic state
- `is_turn_processing_allowed()`: Safeguard for turn processing

**Debouncing**: 250ms cooldown to prevent rapid re-triggering

**Migration Note**: This module is kept for backward compatibility but is no longer used. All interruption logic is now centralized in the Reducer.

### 5. ASR System (`interfaces/asr.py`)

**Two-Stage Architecture**:

**Stage 1: Real-time Streaming (Vosk)**

- Purpose: Low-latency partial transcripts for interruption detection
- Latency: ~100ms
- Accuracy: Moderate
- Usage: `get_partial()` called in ASR worker thread

**Stage 2: Final Transcription**

- **Local Mode**: Faster-Whisper (distil-small.en)
  - RTF: ~0.3x (3s audio → 900ms transcription)
  - Runs on CPU/GPU
- **Cloud Mode**: OpenAI Whisper API
  - Model: `gpt-4o-mini-transcribe`
  - Faster, more accurate

**Audio Preprocessing**:

- Resampling: 16kHz → 16kHz (Vosk/Whisper native)
- Format: float32 normalized [-1, 1]

### 6. LLM System (`interfaces/llm.py`)

**Implementations**:

**LocalLLM** (llama.cpp):

- GGUF model support
- CPU/GPU inference
- Streaming token generation

**CloudLLM**:

- OpenAI, Groq, DeepSeek APIs
- Streaming via SSE
- Configurable base URLs

**Streaming Architecture**:

- Tokens streamed to `_process_turn()`
- Sentence boundary detection (`.!?`)
- Immediate TTS queueing for low latency

### 7. TTS System (`interfaces/tts.py`)

**PocketTTS** (Primary):

- Neural voice synthesis
- 6 voice options
- Sample rate: 24kHz
- **Interruption Support**: Checks `interrupt_event` every 100ms during playback

**Chunked Playback**:

```python
chunk_size = int(sample_rate * 0.1)  # 100ms chunks
for i in range(0, len(audio), chunk_size):
    if interrupt_event and interrupt_event.is_set():
        stream.stop()
        return  # Immediate stop
    stream.write(chunk)
```

**PowerShellTTS** (Fallback):

- Windows System.Speech API
- No interruption support (blocking call)

### 8. Configuration System (`config.py`)

**InstructionProfile** (Pydantic Model):

```python
class InstructionProfile(BaseModel):
    name: str                           # Display name
    start: str                          # "human" or "ai"
    voice: str                          # TTS voice ID
    max_tokens: int                     # LLM response limit
    temperature: float                  # LLM creativity
    pause_ms: int                       # Turn-taking timeout
    end_ms: int                         # Turn end timeout
    safety_timeout_ms: int              # Force turn end
    interruption_sensitivity: float     # 0.0-1.0
    authority: str                      # "human", "ai", "default"
    human_speaking_limit_sec: Optional[int]  # Max user speech duration
    acknowledgments: List[str]          # Limit exceeded responses
    instructions: str                   # System prompt
```

**Pre-configured Profiles**:

- `negotiator`: Human authority, buyer persona
- `ielts_instructor`: AI authority, speaking test examiner
- `confused_customer`: Human authority, support scenario
- `technical_support`: AI authority, troubleshooting agent
- `language_tutor`: Human authority, conversational practice
- `curious_friend`: Default authority, casual chat

## Key Design Patterns

### 1. Immediate vs. Polite Interruption

**Immediate (Human Authority)**:

- `interrupt_event` passed to `tts.speak()`
- TTS checks event every 100ms
- Stops mid-sentence

**Polite (Default/AI Authority)**:

- `interrupt_event` NOT passed to TTS
- Sentence completes
- Queue cleared after completion

### 2. Multi-threaded Safety

**Race Condition Prevention**:

- `ai_speaking` flag set BEFORE queueing TTS
- Double-checks in `_process_turn()` before/after transcription
- Queue mutex for atomic clearing
- **PLAY_ACK safeguard**: Checks interrupt flag before playing acknowledgment (prevents overlap during user interruption)

**Safeguards**:

```python
if not interruption_manager.is_turn_processing_allowed(ai_speaking):
    print("🛑 SAFEGUARD: Rejecting turn")
    return

# PLAY_ACK acknowledgment
if self.human_interrupt_event.is_set():
    return  # Don't play if user interrupted
```

### 3. Human Speaking Limit

**Use Case**: Prevent monologues in AI-authority modes (e.g., IELTS test).

**Mechanism**:

- Timer starts on speech detection
- Checked every second
- On exceed: AI speaks acknowledgment, forces turn end
- Acknowledgment selected randomly from profile list

### 4. Conversation Memory

**Sliding Window**:

- Max 24 turns (configurable)
- FIFO eviction
- Preserves system prompt

**Format**:

```python
[
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
]
```

## Critical Timing Metrics

### Latency Breakdown (Typical Turn)

1. **Speech End Detection**: 600-1200ms (pause/end timeout)
2. **Whisper Transcription**: 800-1000ms (RTF ~0.3x)
3. **LLM First Token**: 200-500ms
4. **TTS Queueing**: <10ms
5. **Total User → AI Response**: 1500-2500ms

### Performance Optimizations

- Sentence-level streaming (not word-level)
- Parallel ASR worker for partial updates
- Pre-loaded models (VAD, Vosk, Whisper, TTS)
- Torch thread configuration (8 threads)

## Testing Infrastructure

### Headless Testing Framework

**Purpose**: Event-driven architecture enables comprehensive testing without audio/API dependencies.

### Test Files (Execution-Ready)

#### 1. `test_headless_standalone.py` ⭐

**Status**: ✅ 16/16 tests passing
**Type**: Pure Python (no dependencies beyond numpy)
**Coverage**:

- State machine transitions (IDLE → SPEAKING → PAUSING → IDLE)
- Interruption scenarios (human/ai/default authority)
- Authority-specific behavior (immediate, polite, blocked interrupts)
- Safety timeouts and force-end logic
- Profile-specific timing (IELTS instructor, negotiator, etc.)
- Human speaking limit enforcement

**Key Tests**:

- `test_idle_to_speaking_on_vad_start`: VAD triggers state change
- `test_complete_user_turn_flow`: Full speak → pause → process cycle
- `test_human_authority_interrupts_ai_speech`: Immediate interruption
- `test_ai_authority_blocks_interruptions`: Interruption prevention
- `test_safety_timeout_force_ends_turn`: Timeout mechanism
- `test_human_speaking_limit_exceeded`: Limit enforcement
- Profile-specific: `test_ielts_instructor_profile`, `test_negotiator_profile`

**Execution**:

```bash
python tests/test_headless_standalone.py
# Output: 16 ✅ Passed, 0 ❌ Failed
```

#### 2. `test_headless_comprehensive.py`

**Status**: ✅ Created with pytest fixtures
**Type**: pytest-compatible (40+ test patterns)
**Coverage**: Extended test library with reusable fixtures for future expansion

**Fixture Support**:

- `clean_state`: Fresh SystemState for each test
- `human_state`: Pre-configured human authority state
- `ai_state`: Pre-configured AI authority state

**Available as Template** for adding 30-50 additional tests targeting 85%+ code coverage.

### Legacy Test Files

#### 3. `test_voices_automated.py`

**Purpose**: Verify voice/persona configurations.

- Mocks user input
- Tests all profiles
- Validates TTS output

#### 4. `test_interruptions_simulated.py`

**Purpose**: Unit tests for `InterruptionManager` logic.

- Tests Human/AI authority modes
- Validates sensitivity thresholds
- No real audio required

#### 5. `test_interruption_actuation.py`

**Purpose**: Integration test for TTS stopping.

- Simulates threading model
- MockTTS with deterministic timing
- Verifies queue clearing
- Tests Immediate vs. Polite modes

## Environment Variables

```bash
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
```

## Common Workflows

### Adding a New Profile

1. Define `InstructionProfile` in `config.py`
2. Set authority mode (`human`, `ai`, `default`)
3. Tune sensitivity (0.0 = strict, 0.6 = hybrid, 1.0 = energy-only)
4. Configure timeouts for persona (fast/slow speaker)
5. Update `ACTIVE_PROFILE` to test

### Debugging Interruptions

1. Check `authority` setting in profile
2. Verify `interruption_sensitivity` (0.6+ recommended for immediate)
3. Look for `⚡ INTERRUPT:` logs
4. Inspect `ai_speaking` flag state
5. Confirm `interrupt_event` passed to TTS

### Switching ASR/LLM Backends

**ASR**:

```python
TURN_END_ASR_MODE = "cloud"  # or "local"
```

**LLM**:

```python
LLM_BACKEND = "groq"  # or "local", "openai", "deepseek"
```

## Turn Analytics System

### Purpose

Structured logging for conversation behavior to enable data-driven tuning of interruption sensitivity, pause thresholds, and confidence scores.

### Components

**`core/analytics.py`**:

- `TurnAnalytics` dataclass: 40+ metrics per turn
- `SessionAnalytics` class: JSONL logging and summary generation

**Metrics Tracked**:

- **Timing**: Human/AI speech duration, silence before turn end
- **Interruptions**: Attempts, accepted/blocked counts, trigger reasons
- **Turn Decisions**: End reason, authority mode, sensitivity value
- **ASR Signals**: Partial transcript lengths, final length, confidence score
- **Latency**: Transcription, LLM generation, total
- **Transcripts**: Full human and AI text with timestamps

### Output Files

**Per-Turn JSONL** (`logs/session_YYYYMMDD_HHMMSS.jsonl`):

```json
{
  "turn_id": 0,
  "human_transcript": "Hey, how's it going?",
  "ai_transcript": "Not bad, just looking at this laptop.",
  "transcript_timestamp": 1738515601.234,
  "interrupt_attempts": 2,
  "interrupts_accepted": 1,
  "end_reason": "silence",
  "total_latency_ms": 1471.0
}
```

**Session Summary** (`logs/session_YYYYMMDD_HHMMSS_summary.json`):

```json
{
  "total_turns": 15,
  "avg_total_latency_ms": 1370.7,
  "interrupt_acceptance_rate": 0.75,
  "end_reason_distribution": { "silence": 10, "safety_timeout": 5 }
}
```

### Analysis Examples

```bash
# View per-turn data
cat logs/session_*.jsonl | jq .

# Extract conversation transcript
cat logs/session_*.jsonl | jq -r '"[\(.turn_id)] Human: \(.human_transcript)\nAI: \(.ai_transcript)\n"'

# Find high-latency turns
cat logs/session_*.jsonl | jq 'select(.total_latency_ms > 2000)'
```

## Authority-Specific Turn Ending Behavior

### Overview

The system implements different turn-ending behaviors based on the active authority mode to ensure appropriate conversation flow control.

### Authority Modes

**Human Authority** (`authority="human"`):

- **Force End**: Disabled (safety timeout never triggers)
- **Turn End**: Only when human stops speaking naturally (silence detection)
- **Mic**: Always on during human turn
- **Speaking Limit**: If configured, speaks acknowledgment once but allows turn to continue
- **Use Case**: User has full control, AI never cuts them off

**Default Authority** (`authority="default"`):

- **Force End**: Enabled (safety timeout active, default 2500ms)
- **Turn End**: Silence detection or safety timeout
- **Mic**: Always on
- **Interruption**: If human interrupts AI, AI stops and says "Go ahead"
- **Use Case**: Balanced conversation, polite interruption handling

**AI Authority** (`authority="ai"`):

- **Force End**: Enabled (safety timeout active)
- **Turn End**: Silence detection or safety timeout
- **Mic**: Off during AI speech (no audio buffering)
- **Interruption**: Not allowed during AI speech
- **Use Case**: AI controls conversation flow (e.g., IELTS examiner)

### Implementation Details

**TurnTaker.should_force_end()**:

```python
def should_force_end(self, authority: str, elapsed_ms: float) -> bool:
    if authority == "human":
        return False  # Never force end
    return elapsed_ms >= self.safety_timeout_ms
```

**Post-Force-End Audio Rejection**:

- After safety timeout triggers, `force_ended` flag is set
- All subsequent audio frames are rejected until turn completes
- Prevents buffer overflow and turn confusion

**"Go Ahead" Fallback (Default Authority)**:

- When human interrupts AI during response generation
- AI response queue is cleared
- "Go ahead" is queued instead
- Allows human to continue smoothly

### Human Speaking Limit

**Purpose**: Prevent monologues in AI-authority modes or provide gentle reminders.

**Behavior**:

1. When limit exceeded, AI speaks random acknowledgment from profile list
2. Acknowledgment is spoken immediately (interrupts user)
3. Buffers are cleared to prevent duplicate turns
4. Flag prevents repeated acknowledgments in same turn
5. Turn continues until user naturally stops (human authority) or timeout (default/ai authority)

**Configuration**:

```python
human_speaking_limit_sec=45  # Seconds, or None to disable
acknowledgments=["Okay.", "Noted.", "Got it."]
```

## Known Limitations

1. **PowerShellTTS**: Cannot interrupt mid-sentence (blocking API)
2. **Vosk Accuracy**: Partial transcripts less accurate than Whisper
3. **Local Whisper**: Slower than cloud (RTF ~0.3x vs 0.1x)
4. **Windows Only**: PowerShellTTS fallback platform-specific

## Future Enhancements

- Multi-language support
- Emotion detection for dynamic responses
- WebRTC for remote conversations
- Voice cloning for custom personas
- Adaptive timeout tuning based on speaking rate
