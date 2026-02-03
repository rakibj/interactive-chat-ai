# Interactive Chat AI - Project Summary

## Overview

A real-time voice conversation system with configurable AI personas, advanced interruption handling, and multi-modal ASR/TTS capabilities. Built for natural, low-latency human-AI voice interactions with sophisticated turn-taking logic.

**Key Features**:

- Event-driven architecture with deterministic state machine reducer
- **Phased AI system with signal-driven transitions** (NEW)
- Decoupled signals layer for optional plugin/dashboard integration without core modification
- Multi-authority modes (human, AI, default) with profile-based turn-taking
- Human speaking limit enforcement for controlled conversation dynamics
- Comprehensive analytics with per-turn metrics logging

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
│   │   ├── signals.py          # Signals architecture (observations layer)
│   │   ├── audio_manager.py    # Audio I/O and VAD
│   │   ├── conversation_memory.py   # Chat history
│   │   └── analytics.py        # Telemetry
│   └── interfaces/
│       ├── asr.py              # ASR implementations
│       ├── llm.py              # LLM implementations (with signal emission)
│       └── tts.py              # TTS implementations
├── models/                     # Local model storage
└── test_*.py                   # Test scripts
```

## Core Components

### 1. ConversationEngine (`main.py`)

**Purpose**: Orchestration engine based on event-driven dispatcher loop with integrated analytics.

**Key Responsibilities**:

- Running the Main Event Loop (get events, reduce state, handle actions)
- Executing Side-Effects from `Action` objects (speak, interrupt, log, play acknowledgments)
- Coordinating asynchronous turn processing (transcription → LLM → TTS)
- Capturing turn metrics for analytics logging
- Graceful shutdown management

**Event Loop**:

```python
while not shutdown:
    event = event_queue.get()
    state, actions = Reducer.reduce(state, event)
    for action in actions:
        _handle_action(action)  # Execute side effects
```

**Action Handlers**:

- `LOG`: Print messages
- `INTERRUPT_AI`: Set interrupt flag, clear queues
- `PLAY_ACK`: Thread acknowledgment playback
- `SPEAK_SENTENCE`: Queue text for TTS
- `PROCESS_TURN`: Run turn processing asynchronously
- `LOG_TURN` (NEW): Create TurnAnalytics and call `session_analytics.log_turn()`

**Timing Capture** (NEW):
`_process_turn_async()` measures and stores:

- ASR transcription latency
- LLM generation latency
- Total processing latency
- Final user and AI transcripts

### 2. Event-Driven Core (`core/event_driven_core.py`)

**Purpose**: Centralized business logic and state management.

**Components**:

- **SystemState**: Single source of truth (dataclass) with turn metrics tracking
- **Event**: Standardized inputs (VAD, Audio, ASR, AI Status, TICK timer)
- **Action**: Deterministic side-effect triggers (Interrupt, ProcessTurn, Log, PlayAck, SpeakSentence, **LogTurn**)
- **Reducer**: Pure function for state transitions with explicit TICK event handler

**Action Types**:

- `LOG`: Print diagnostic messages
- `INTERRUPT_AI`: Stop AI speech immediately
- `PROCESS_TURN`: Trigger transcription/LLM processing
- `PLAY_ACK`: Play acknowledgment sound
- `SPEAK_SENTENCE`: Queue sentence for TTS
- `LOG_TURN`: Emit turn analytics (NEW)

**Turn Metrics Tracking** (NEW):
SystemState now tracks per-turn metrics for automatic analytics logging:

- `turn_interrupt_attempts`: Count of interruption checks
- `turn_interrupt_accepts`: Successful interruptions
- `turn_partial_transcripts`: List of ASR partial texts
- `turn_final_transcript`: Final user transcription
- `turn_ai_transcript`: Complete AI response
- `turn_end_reason`: Why turn ended (silence, safety_timeout, limit_exceeded)
- `turn_transcription_ms`, `turn_llm_generation_ms`, `turn_total_latency_ms`: Latency metrics
- `turn_confidence_score`: ASR confidence

**TICK Event Handler**:

- Drives state machine advancement without external input
- Advances time-based state transitions (e.g., PAUSING → IDLE)
- Enables safety timeout logic to function correctly
- Called continuously by main event loop to ensure responsive timing

**Metric Collection Flow**:

1. **Turn Begins**: VAD_SPEECH_START sets `turn_start_time`
2. **During Turn**: AUDIO_FRAME counts interrupt attempts; ASR_PARTIAL_TRANSCRIPT collects texts
3. **Turn Ends**: PAUSING state sets `turn_end_reason`
4. **Processing**: PROCESS_TURN action triggers `_process_turn_async()` with timing capture
5. **Logging**: RESET_TURN event emits LOG_TURN action with complete metrics
6. **Output**: LOG_TURN handler calls `session_analytics.log_turn()`

### 3. Signals & Observability (`core/signals.py` + LLM Response Signals)

**Purpose**: Two-tier signal system combining framework signals (state changes, analytics) with LLM-emitted observation signals (custom per-profile).

**Key Insight**: Signals describe state changes and observations; they do not trigger state transitions. LLM can also emit signals to describe its observations without modifying response quality.

**Signal Sources**:

**Framework Signals** (from core reducer):

- `conversation.interrupted`: User interrupted AI speech
- `conversation.speaking_limit_exceeded`: User exceeded speaking duration limit
- `llm.generation_start`: LLM began response generation
- `llm.generation_complete`: LLM finished response generation
- `llm.generation_error`: LLM generation failed
- `analytics.turn_metrics_updated`: Complete turn metrics logged

**LLM-Emitted Signals** (custom per profile):

- Extracted from LLM response as `<signals>{JSON}</signals>` blocks
- Prefixed with `custom.` namespace (e.g., `custom.exam.question_asked`)
- Profile-specific, defined in `InstructionProfile.signals` dict
- Examples: IELTS emits `custom.exam.question_asked`, negotiator emits `custom.negotiation.counteroffer_made`
- System prompt dynamically injects profile signals so LLM knows what to emit

**Signal Extraction**:

- Regex pattern: `<signals>\s*\{.*?\}\s*</signals>`
- Happens during streaming, signals buffered silently (not sent to TTS)
- Clean response (signal-stripped) stored in conversation memory

**Backward Compatibility**: 100% - All signals are optional. Core functions identically with zero listeners registered.

### 4. Phased AI System (NEW - `config.py` + `main.py`)

**Purpose**: Multi-phase conversations with deterministic, signal-driven transitions between stages.

**Key Insight**: Use signals not just for observability, but also to orchestrate conversation flow. The AI can emit signals that trigger automatic phase transitions, enabling complex multi-stage interactions (exams, sales calls, tutorials) without hardcoded logic.

**Components**:

**PhaseProfile** - Container for multi-phase conversations:

- Contains multiple InstructionProfiles (one per phase)
- Defines transitions between phases based on signals
- Provides global and per-phase context
- Supports linear, branching, and loop-back flows

**PhaseTransition** - Defines when to move between phases:

- `from_phase`: Source phase ID
- `to_phase`: Destination phase ID
- `trigger_signals`: List of signals that trigger transition
- `require_all`: If True, all signals must be emitted; if False, any one triggers

**Use Cases**:

- **IELTS Exam**: greeting → part1 → part2 → part3 → closing (5 phases, linear)
- **Sales Call**: opening → discovery → pitch ⟷ objection_handling → close (5 phases, branching + loop-back)
- **Tutorial**: intro → lesson → practice → assessment → conclusion (multi-stage learning)
- **Support**: intake → diagnosis → solution → verification → closing (structured troubleshooting)

**Flow Example** (IELTS):

```
1. greeting phase (AI starts)
   - AI: "Good morning, may I see your ID?"
   - AI emits: custom.exam.greeting_complete
   ↓ TRANSITION
2. part1 phase
   - AI asks 4-5 personal questions
   - AI emits: custom.exam.questions_completed
   ↓ TRANSITION
3. part2 phase
   - AI gives topic card, candidate speaks 1-2 minutes
   - AI emits: custom.exam.monologue_complete
   ↓ TRANSITION
4. part3 phase
   - AI asks abstract discussion questions
   - AI emits: custom.exam.discussion_complete
   ↓ TRANSITION
5. closing phase
   - AI: "That concludes the test. Thank you."
```

**How It Works**:

1. System starts in `initial_phase`
2. After each AI response, `_extract_signals()` parses `<signals></signals>` blocks
3. `_check_phase_transitions()` checks if emitted signals match any transition rules
4. If match found, `PHASE_TRANSITION` event emitted
5. `_transition_to_phase()` executes:
   - Loads new InstructionProfile
   - Updates SystemState with new settings (authority, timeouts, etc.)
   - Clears signal history for new phase
   - Injects phase context into system prompt
   - Generates AI greeting if new phase starts with AI

**Context Injection**:
When running a phase, system prompt is constructed as:

```
SYSTEM_PROMPT_BASE
+ Signal hints (what signals to emit)
+ === PHASE CONTEXT ===
+ Global context (applies to all phases)
+ Per-phase context (specific to this phase)
+ ===================
+ Profile instructions (phase-specific role)
```

**Backward Compatibility**: 100% - Standalone InstructionProfiles work unchanged. Set `ACTIVE_PHASE_PROFILE = None` to use single profile mode.

**Documentation**: See `docs/PHASED_AI_GUIDE.md` for comprehensive guide, `docs/PHASED_AI_QUICK_REF.md` for quick reference.

### 5. AudioManager (`core/audio_manager.py`)

**Purpose**: Low-level audio I/O and speech detection.

**Key Methods**:

- `get_audio_chunk()`: Returns 512-sample frames at 16kHz
- `detect_speech(frame)`: Silero VAD inference (returns bool + RMS energy)
- `is_sustained_speech(energy_history)`: Energy-based speech confirmation

**VAD Configuration**:

- Threshold: 0.5 (Silero probability)
- Energy floor: 0.015 (RMS)
- Frame size: 512 samples (32ms @ 16kHz)

### 6. TurnTaker (`core/turn_taker.py`)

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

### 7. InterruptionManager (`core/interruption_manager.py`)

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

### 8. ASR System (`interfaces/asr.py`)

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

### 9. LLM System (`interfaces/llm.py`)

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

### 10. TTS System (`interfaces/tts.py`)

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

### 11. Configuration System (`config.py`)

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
    signals: Dict[str, str]             # Custom signals this profile may emit (NEW)
```

**System Prompt Construction**:

- **Base**: `SYSTEM_PROMPT_BASE` with generic signal guidance (not profile-specific)
- **Dynamic Injection**: `get_system_prompt()` appends profile-specific signals with `custom.` prefix
- **Profile Instructions**: Added after signal hints
- Result: LLM receives exact signals to emit for its role

**Pre-configured Profiles** (with custom signals):

- `negotiator`: 3 signals (counteroffer_made, objection_raised, answer_complete)
- `ielts_instructor`: 4 signals (exam.question_asked, exam.response_received, exam.fluency_observation, answer_complete)
- `confused_customer`: 3 signals (user_confused, clarification_needed, answer_complete)
- `technical_support`: 4 signals (issue_identified, solution_offered, escalation_needed, answer_complete)
- `language_tutor`: 3 signals (vocabulary_introduced, grammar_note, answer_complete)
- `curious_friend`: 3 signals (shared_interest, follow_up_question, answer_complete)

## Key Design Patterns

### 1. Hybrid Streaming with Signal Detection

**Problem**: Signals appear at END of LLM response, but streaming sends sentences to TTS before signals arrive.

**Solution**: Stream until `<signals` tag detected, then buffer silently:

```python
for token in llm.stream_completion(...):
    full_response += token

    if "<signals" in full_response and not signals_started:
        signals_started = True
        # Send any remaining incomplete sentence
        # Then silently collect signal block
        continue

    if not signals_started:
        # Process as normal (send to TTS on punctuation)
    # else: buffer silently
```

**Benefits**:

- Low latency for main response (streaming + sentence-level)
- Zero signal contamination (signal blocks never reach TTS)
- Minimal buffering (only trailing signal block)

### 2. AI-Initiated Turns

**Pattern**: Two methods for turn generation:

- `_process_turn_async()`: User-initiated turn (ASR → LLM → TTS)
- `_generate_ai_turn()`: AI-initiated turn (LLM → TTS, no ASR). Used for greetings when `start="ai"`

**Benefits**:

- Profiles starting with `start="ai"` can greet first
- Cleaner initialization (no dummy audio needed)
- Reusable for proactive AI statements

### 3. Immediate vs. Polite Interruption

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

### 3. Signals for Decoupled Observability

**Pattern**: Core emits named Signals describing state changes; external listeners subscribe optionally without core knowledge of their existence.

**Separation of Concerns**:

- **Actions** (from Reducer): Trigger state changes and side effects (deterministic)
- **Signals** (from Reducer): Broadcast observations about state changes (optional, no-op if no listeners)
- **Core Logic**: Reducer is unaware of and unaffected by listeners (pure function)

**Benefits**:

- Plugins/dashboards added without modifying core
- Analytics decoupled from business logic
- Multiple listeners can react to same event independently
- Listener failures isolated (exception caught, logged, core unaffected)

**Example Signal Flow**:

```
VAD_SPEECH_START event
→ Reducer: state.conversation.state = SPEAKING
→ emit_signal("conversation.interrupted", {...}) [if applicable]
→ Listener 1: Log to analytics DB
→ Listener 2: Send metrics to monitoring dashboard
→ Listener 3: Calculate turn features for ML
[All listeners run independently, exceptions don't crash core]
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

Structured logging for conversation behavior to enable data-driven tuning of interruption sensitivity, pause thresholds, and confidence scores. Fully integrated into event-driven architecture via LOG_TURN action.

### Integration

**Event-Driven Collection**:

- Metrics captured automatically during state transitions (no manual calls)
- LOG_TURN action emitted when turn completes (RESET_TURN event)
- Handler converts SystemState turn metrics → TurnAnalytics dataclass → JSONL log
- Works with all profiles, ASR backends, and LLM backends

### Components

**`core/analytics.py`**:

- `TurnAnalytics` dataclass: Immutable turn record with 40+ metrics
- `SessionAnalytics` class: JSONL logging and summary generation

**`core/event_driven_core.py`** (NEW):

- `LOG_TURN` action type: Carries all turn metrics when turn completes
- SystemState turn metrics: 12 fields tracking throughout turn lifecycle
- Metric collection in Reducer: Counts, transcripts, timings, end reasons

**`main.py`** (NEW):

- LOG_TURN action handler: Converts metrics → TurnAnalytics → logs to JSONL
- Timing capture in `_process_turn_async()`: ASR and LLM latency measured
- Transcript accumulation: AI text gathered during sentence streaming

**Metrics Tracked**:

- **Timing**: Transcription latency, LLM generation latency, total latency
- **Interruptions**: Attempts, accepted count, blocked count, trigger reasons
- **Turn Decisions**: End reason (silence/timeout/limit), authority mode, sensitivity
- **Transcripts**: Full user transcript, full AI transcript, partial ASR history
- **Latency Details**: Per-component timing breakdown
- **State**: Authority mode, interruption sensitivity setting, confidence scores
- **Phase Tracking** (NEW): Current phase ID if using PhaseProfile mode (tracks which phase produced each turn)

### Output Files

**Per-Turn JSONL** (`logs/session_YYYYMMDD_HHMMSS.jsonl`):
One JSON object per line, written automatically when each turn completes:

```json
{
  "turn_id": 0,
  "timestamp": 1738515601.234,
  "profile_name": "IELTS Speaking Test (Full)",
  "phase_id": "part1",
  "human_transcript": "I am from Beijing.",
  "ai_transcript": "Interesting. Tell me more about your hometown.",
  "interrupt_attempts": 0,
  "interrupts_accepted": 0,
  "interrupts_blocked": 0,
  "end_reason": "silence",
  "authority_mode": "ai",
  "sensitivity_value": 0.3,
  "transcription_ms": 903.9,
  "llm_generation_ms": 366.7,
  "total_latency_ms": 1270.6
}
```

**Session Summary** (`logs/session_YYYYMMDD_HHMMSS_summary.json`):
Aggregated metrics across all turns, generated at session end:

```json
{
  "session_id": "session_20260202_230800",
  "total_turns": 15,
  "session_duration_sec": 287.5,
  "avg_total_latency_ms": 1270.6,
  "interrupt_acceptance_rate": 0.75,
  "end_reason_distribution": { "silence": 10, "safety_timeout": 5 },
  "avg_transcription_ms": 903.9,
  "avg_llm_generation_ms": 366.7
}
```

### PhaseProfile Integration (NEW)

When using PhaseProfile mode, each turn's analytics are automatically tagged with the current `phase_id`. This enables:

- **Phase-specific performance analysis**: Compare latency, interruption rates, and effectiveness across phases
- **Phase transitions tracking**: Observe which signals triggered transitions and when
- **Behavioral patterns**: Identify if authority modes, sensitivity settings, or turn characteristics vary by phase
- **Quality metrics per phase**: Measure interruption acceptance, ASR accuracy, and LLM latency per exam/sales/tutorial phase

Example query: _"In part2 (long monologue), what was the average interruption acceptance rate?"_

The `phase_id` field is `None` for standalone InstructionProfile mode (single-phase conversations).

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
