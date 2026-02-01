# Interactive Chat AI - Modular Project Structure

## Directory Layout

```
interactive_chat/
├── config.py                  # Centralized configuration (YAML-loadable)
├── main.py                    # Minimal orchestration loop (~150 lines)
├── core/
│   ├── __init__.py
│   ├── audio_manager.py       # VAD + energy detection + stream management
│   ├── turn_taker.py          # State machine (IDLE/SPEAKING/PAUSING) + confidence scoring
│   ├── interruption_manager.py# Sensitivity-aware interruption logic
│   └── conversation_memory.py # Ephemeral history buffer (deque wrapper)
├── interfaces/
│   ├── __init__.py
│   ├── asr.py                 # Abstract ASR interface + Vosk/Whisper implementations
│   ├── llm.py                 # Abstract LLM interface + Groq/OpenAI/local implementations
│   └── tts.py                 # Abstract TTS interface + Pocket/PowerShell implementations
└── utils/
    ├── __init__.py
    ├── audio.py               # float32↔int16, chunking helpers
    └── text.py                # Sentence boundary detection, lexical bias scoring
```

## Quick Start

```python
from interactive_chat.main import ConversationEngine

engine = ConversationEngine()
engine.run()
```

## Configuration

All settings are in `config.py`:

- Audio parameters (sample rate, VAD thresholds)
- ASR mode (Vosk/Whisper)
- LLM backend (Groq/OpenAI/Local)
- TTS mode (Pocket/PowerShell)
- Turn-taking thresholds
- Interruption sensitivity

## Architecture

### Core Modules

- **AudioManager**: Handles microphone stream, VAD, and energy detection
- **TurnTaker**: State machine for conversation turn management
- **InterruptionManager**: Human interruption detection with sensitivity control
- **ConversationMemory**: Ephemeral context buffer with deque

### Interfaces

- **ASR**: Abstract interface with Vosk (low-latency) and Whisper (accurate) implementations
- **LLM**: Abstract interface with local (llama.cpp) and cloud (Groq/OpenAI/DeepSeek) implementations
- **TTS**: Abstract interface with Pocket TTS (neural) and PowerShell (system) implementations

### Utils

- **audio.py**: Audio format conversion and chunking helpers
- **text.py**: Lexical bias scoring and turn-taking confidence metrics

## Performance Metrics

Timing reports include:

- Audio capture duration
- Whisper transcription time + RTF (Real-Time Factor)
- LLM generation latency
- Total response latency
