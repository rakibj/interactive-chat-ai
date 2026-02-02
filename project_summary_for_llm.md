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
│   ├── main.py                 # Main orchestration loop
│   ├── config.py               # Centralized configuration
│   ├── core/
│   │   ├── audio_manager.py    # Audio I/O and VAD
│   │   ├── turn_taker.py       # Turn-taking state machine
│   │   ├── interruption_manager.py  # Interruption logic
│   │   └── conversation_memory.py   # Chat history
│   └── interfaces/
│       ├── asr.py              # ASR implementations
│       ├── llm.py              # LLM implementations
│       └── tts.py              # TTS implementations
├── models/                     # Local model storage
└── test_*.py                   # Test scripts
```

## Core Components

### 1. ConversationEngine (`main.py`)
**Purpose**: Main orchestration loop coordinating all subsystems.

**Key Responsibilities**:
- Audio stream management
- Turn-taking coordination
- Interruption detection and handling
- Multi-threaded TTS queue processing
- Conversation state tracking

**Threading Model**:
- **Main Thread**: Audio processing loop (16kHz, 512-sample frames)
- **TTS Worker**: Consumes response queue, manages `ai_speaking` flag
- **ASR Worker**: Updates partial transcripts for interruption detection

**Critical State Variables**:
- `ai_speaking`: Boolean flag indicating AI speech status
- `human_interrupt_event`: Threading.Event for interruption signaling
- `response_queue`: Queue for TTS sentences
- `turn_audio`: Deque buffering current turn's audio

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

### 4. InterruptionManager (`core/interruption_manager.py`)
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

**Safeguards**:
```python
if not interruption_manager.is_turn_processing_allowed(ai_speaking):
    print("🛑 SAFEGUARD: Rejecting turn")
    return
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

### 1. `test_voices_automated.py`
**Purpose**: Verify voice/persona configurations.
- Mocks user input
- Tests all profiles
- Validates TTS output

### 2. `test_interruptions_simulated.py`
**Purpose**: Unit tests for `InterruptionManager` logic.
- Tests Human/AI authority modes
- Validates sensitivity thresholds
- No real audio required

### 3. `test_interruption_actuation.py`
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
