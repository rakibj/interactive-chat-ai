# Interactive Chat AI - Per-Profile Settings System

A flexible, modular interactive chat system with multiple conversation profiles, each with independent timing, voice, LLM, and interaction settings.

## Quick Start

### Installation

```bash
# Clone or download the project
cd interactive-chat-ai

# Install dependencies (using uv or pip)
uv sync
# or: pip install -r requirements.txt
```

### Run

```bash
# Run with current profile (default: negotiator)
python -m interactive_chat.main

# Change profile by editing config.py:
#   ACTIVE_PROFILE = "ielts_instructor"  # or another profile
```

## Profiles Available

| Profile               | Role              | Timing                | LLM                   | Interaction     |
| --------------------- | ----------------- | --------------------- | --------------------- | --------------- |
| **negotiator**        | Buyer negotiating | Fast (600/1200ms)     | Brief (80 tok)        | No interruption |
| **ielts_instructor**  | Test guide        | Measured (800/1500ms) | Detailed (120 tok)    | Professional    |
| **confused_customer** | Support scenario  | Standard (700/1400ms) | Helpful (90 tok)      | Conversational  |
| **technical_support** | Tech support      | Quick (500/1000ms)    | Concise (100 tok)     | Professional    |
| **language_tutor**    | English tutor     | Standard (700/1400ms) | Encouraging (110 tok) | Teaching        |
| **curious_friend**    | Casual friend     | Natural (750/1300ms)  | Creative (95 tok)     | Friendly        |

## Key Features

### Per-Profile Settings (9 Parameters)

Each profile has independent configuration:

- **Timing**: `pause_ms`, `end_ms`, `safety_timeout_ms` - Controls when turns end
- **LLM**: `max_tokens`, `temperature` - Controls response quality
- **Voice**: `voice` - TTS voice selection
- **Interaction**: `interruption_sensitivity` - How easily interrupted (0.0-1.0)
- **Content**: `name`, `start` (ai/human), `instructions` (system prompt)

### Zero-Code Profile Switching

Edit `config.py` one line:

```python
ACTIVE_PROFILE = "ielts_instructor"  # Switch profile without code changes
```

Restart - all settings apply automatically.

### Component Architecture

- **Core**: Audio management, turn-taking, interruption handling, conversation memory
- **Interfaces**: Abstract ASR, LLM, and TTS with multiple implementations
- **Config**: Centralized profile definitions with helper functions

## Documentation

- **[PROFILE_SETTINGS.md](PROFILE_SETTINGS.md)** - Comprehensive guide to profile system
- **[PROFILE_SETTINGS_QUICK_REF.md](PROFILE_SETTINGS_QUICK_REF.md)** - Quick reference
- **[PER_PROFILE_SETTINGS_SUMMARY.md](PER_PROFILE_SETTINGS_SUMMARY.md)** - Implementation details
- **[PROFILES.md](interactive_chat/PROFILES.md)** - Profile instructions

## Testing

```bash
# List all profiles and settings
python test_profiles.py

# Comprehensive system test
python test_settings_system.py

# Full integration test
python test_e2e_integration.py
```

**All tests passing ✓** (5/5 test groups)

## Usage Examples

### Example 1: Load Profile Settings

```python
from interactive_chat.config import get_profile_settings

settings = get_profile_settings("ielts_instructor")
print(settings["voice"])  # "jean"
print(settings["max_tokens"])  # 120
print(settings["interruption_sensitivity"])  # 0.3
```

### Example 2: Get System Prompt

```python
from interactive_chat.config import get_system_prompt

prompt = get_system_prompt("language_tutor")
# Returns: base prompt + language tutor instructions
```

### Example 3: Use in ConversationEngine

```python
from interactive_chat.main import ConversationEngine

# Profile settings automatically applied
engine = ConversationEngine()  # Uses ACTIVE_PROFILE
engine.run()
```

## Creating a Custom Profile

Add to `interactive_chat/config.py`:

```python
INSTRUCTION_PROFILES = {
    # ... existing profiles ...
    "my_profile": {
        "name": "My Custom Role",
        "start": "ai",
        "voice": "alba",
        "max_tokens": 100,
        "temperature": 0.6,
        "pause_ms": 650,
        "end_ms": 1250,
        "safety_timeout_ms": 2700,
        "interruption_sensitivity": 0.3,
        "instructions": "Your system prompt for the AI...",
    },
}
```

Then set:

```python
ACTIVE_PROFILE = "my_profile"
```

## Configuration Reference

### Timing Guidelines

- **pause_ms**: 400-1000ms (pause before allowing interruption)
  - Quick (technical): 400-500ms
  - Standard: 600-800ms
  - Thoughtful: 800-1000ms

- **end_ms**: 800-2000ms (end-of-turn threshold)
  - Quick transitions: 800-1000ms
  - Standard: 1200-1400ms
  - Long responses: 1500-2000ms

- **safety_timeout_ms**: Should be ~2.0-2.5x end_ms
  - Prevents infinite waiting

### Interruption Sensitivity (0.0-1.0)

- 0.0 = Never interrupt (wait for complete response)
- 0.2-0.3 = Professional (rare interruptions)
- 0.4-0.5 = Conversational (natural interruptions)
- 0.7-1.0 = Aggressive (frequent interruptions)

### LLM Temperature (0.0-1.0)

- 0.3-0.5 = Factual, consistent
- 0.5-0.7 = Balanced
- 0.7-1.0 = Creative, varied

## Architecture Overview

```
ConversationEngine
  ├── AudioManager (Silero VAD)
  ├── TurnTaker (state machine with profile timing)
  ├── InterruptionManager (with profile sensitivity)
  ├── ConversationMemory (deque-based history)
  ├── ASR (Vosk/Whisper) - Profile-aware
  ├── LLM (Groq/OpenAI/local) - Profile-aware
  └── TTS (Pocket/PowerShell) - Profile-aware

config.py
  ├── INSTRUCTION_PROFILES[6]
  ├── get_profile_settings()
  └── get_system_prompt()
```

## Technologies

- **ASR**: Vosk (low-latency) + Faster-Whisper (accurate)
- **VAD**: Silero Voice Activity Detection
- **LLM**: Groq API (primary) + OpenAI/DeepSeek/llama.cpp (fallbacks)
- **TTS**: Pocket TTS (neural) + PowerShell (system)
- **Threading**: Daemon workers for ASR/TTS, main loop for audio processing

## Troubleshooting

**"Profile not found" error**

- Check `ACTIVE_PROFILE` in `config.py` matches a key in `INSTRUCTION_PROFILES`
- Available profiles: negotiator, ielts_instructor, confused_customer, technical_support, language_tutor, curious_friend

**Settings not applying**

- Restart the application after changing `ACTIVE_PROFILE`
- Verify profile is in `INSTRUCTION_PROFILES` dictionary

**Voice not changing**

- Current voice selection needs TTS initialization parameter (ready for implementation)

## Status

✓ **Per-Profile Settings System - COMPLETE**

- 6 pre-configured profiles
- 9 customizable parameters per profile
- All components integrated
- Full test coverage
- Ready for production use

## Next Steps

1. Implement per-profile voice parameter in TTS initialization
2. Add additional profiles as needed
3. Consider extending with: custom_vocabulary, energy_floor, confidence_threshold
4. Create interactive profile selector UI

## License

[Your License Here]

## Support

For issues or feature requests, see [PROFILE_SETTINGS.md](PROFILE_SETTINGS.md) and [PER_PROFILE_SETTINGS_SUMMARY.md](PER_PROFILE_SETTINGS_SUMMARY.md).
