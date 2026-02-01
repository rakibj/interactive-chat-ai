# Per-Profile Settings System - Implementation Guide

## Overview

The interactive chat system now supports fully customizable per-profile settings. Each conversation profile (negotiator, IELTS instructor, confused customer, etc.) has its own:

- **Timing Settings**: pause_ms, end_ms, safety_timeout_ms
- **Interaction Settings**: interruption_sensitivity, start (who speaks first)
- **LLM Settings**: max_tokens, temperature
- **Voice Settings**: voice (TTS voice to use)
- **Content Settings**: name, instructions (system prompt)

## Profile Configuration

All profile settings are defined in `interactive_chat/config.py` in the `INSTRUCTION_PROFILES` dictionary:

```python
INSTRUCTION_PROFILES = {
    "profile_key": {
        "name": "Human-readable profile name",
        "start": "ai",  # or "human" - who speaks first
        "voice": "alba",  # TTS voice name
        "max_tokens": 80,  # LLM max tokens for responses
        "temperature": 0.5,  # LLM temperature (0.0-1.0)
        "pause_ms": 600,  # Pause threshold in milliseconds
        "end_ms": 1200,  # End-of-turn threshold
        "safety_timeout_ms": 2500,  # Force turn end timeout
        "interruption_sensitivity": 0.0,  # 0.0 (no interruption) to 1.0 (always interrupt)
        "instructions": "System prompt for the AI...",
    },
}
```

### Current Profiles

| Profile           | Voice   | Start | pause_ms | end_ms | safety_timeout_ms | interruption_sensitivity | max_tokens | temperature |
| ----------------- | ------- | ----- | -------- | ------ | ----------------- | ------------------------ | ---------- | ----------- |
| negotiator        | alba    | human | 600      | 1200   | 2500              | 0.0                      | 80         | 0.5         |
| ielts_instructor  | jean    | ai    | 800      | 1500   | 3500              | 0.3                      | 120        | 0.6         |
| confused_customer | marius  | ai    | 700      | 1400   | 2800              | 0.5                      | 90         | 0.7         |
| technical_support | cosette | ai    | 500      | 1000   | 2200              | 0.2                      | 100        | 0.4         |
| language_tutor    | fantine | ai    | 700      | 1400   | 3000              | 0.1                      | 110        | 0.6         |
| curious_friend    | alba    | ai    | 750      | 1300   | 2800              | 0.4                      | 95         | 0.75        |

## Using Profile Settings in Code

### 1. Load Profile Settings

```python
from interactive_chat.config import get_profile_settings

# Get all settings for a profile
settings = get_profile_settings("ielts_instructor")

# Access individual settings
pause_ms = settings["pause_ms"]  # 800
voice = settings["voice"]  # "jean"
max_tokens = settings["max_tokens"]  # 120
```

### 2. Apply Settings to Components

#### TurnTaker Component

```python
from interactive_chat.core.turn_taker import TurnTaker

turn_taker = TurnTaker()
turn_taker.pause_ms = settings["pause_ms"]
turn_taker.end_ms = settings["end_ms"]
turn_taker.safety_timeout_ms = settings["safety_timeout_ms"]
```

#### InterruptionManager Component

```python
from interactive_chat.core.interruption_manager import InterruptionManager

interruption_manager = InterruptionManager()
interruption_manager.set_sensitivity(settings["interruption_sensitivity"])
```

#### LLM Calls

```python
response = llm.stream_completion(
    system_prompt=system_prompt,
    messages=messages,
    max_tokens=settings["max_tokens"],
    temperature=settings["temperature"],
)
```

#### TTS Voice Selection

```python
from interactive_chat.interfaces.tts import get_tts

tts = get_tts(voice=settings["voice"])
```

### 3. Get System Prompt for Profile

```python
from interactive_chat.config import get_system_prompt

# Get complete system prompt (base + profile instructions)
system_prompt = get_system_prompt("ielts_instructor")
```

## Integration with Main Conversation Engine

The `ConversationEngine` class (in `interactive_chat/main.py`) automatically:

1. **Loads profile settings** on initialization
2. **Applies timing settings** to the turn-taker
3. **Applies interaction settings** to the interruption manager
4. **Uses profile-specific LLM parameters** in all AI responses
5. **Displays profile information** at startup

Example:

```python
from interactive_chat.main import ConversationEngine

# Create engine with a specific profile
engine = ConversationEngine(profile_name="ielts_instructor")
# All settings are automatically applied!
```

## Modifying Profile Settings

To modify a profile's settings:

1. Edit `interactive_chat/config.py`
2. Find the profile in the `INSTRUCTION_PROFILES` dictionary
3. Update the specific setting (e.g., `"pause_ms": 1000`)
4. Restart the application

Example - Making the IELTS instructor more talkative:

```python
"ielts_instructor": {
    # ... other settings ...
    "max_tokens": 180,  # Increased from 120
    "temperature": 0.7,  # Increased from 0.6 for more varied responses
},
```

## Creating New Profiles

To add a new profile:

1. Add an entry to `INSTRUCTION_PROFILES` in `config.py`
2. Include all required keys (see template above)
3. Use profile name from command line or API

```python
INSTRUCTION_PROFILES = {
    # ... existing profiles ...
    "my_custom_profile": {
        "name": "My Custom Role",
        "start": "ai",
        "voice": "alba",
        "max_tokens": 100,
        "temperature": 0.6,
        "pause_ms": 650,
        "end_ms": 1250,
        "safety_timeout_ms": 2700,
        "interruption_sensitivity": 0.3,
        "instructions": "Your custom system prompt here...",
    },
}
```

## Setting Recommendations

### Pause Duration (pause_ms)

- **Quick responses**: 400-500ms (technical_support)
- **Normal conversation**: 600-800ms (negotiator, ielts_instructor)
- **Thoughtful responses**: 800-1000ms (language_tutor)

### End-of-Turn Duration (end_ms)

- **Quick transitions**: 800-1000ms (technical_support)
- **Normal transitions**: 1200-1400ms (negotiator, confused_customer)
- **Long-form responses**: 1500-2000ms (ielts_instructor)

### Safety Timeout (safety_timeout_ms)

- Recommended: 1.5-2.5x the end_ms value
- Prevents infinite waiting if confidence never reached
- Example: if end_ms=1200, set safety_timeout_ms=2500

### Interruption Sensitivity (0.0 to 1.0)

- **0.0**: No interruptions (wait for complete response)
- **0.2-0.3**: Professional settings (technical_support)
- **0.4-0.5**: Conversational settings (curious_friend, confused_customer)
- **1.0**: Always interrupt (aggressive negotiation)

### LLM Temperature (0.0 to 1.0)

- **0.3-0.5**: Factual, consistent responses (technical_support, ielts_instructor)
- **0.5-0.7**: Balanced tone (negotiator, confused_customer)
- **0.7-1.0**: Creative, varied responses (curious_friend, language_tutor)

### Max Tokens

- **80-100**: Brief responses (negotiator, technical_support)
- **100-120**: Standard responses (ielts_instructor)
- **150+**: Long-form responses (when detailed explanations needed)

## Testing Profile Settings

Run the comprehensive test suite:

```bash
python test_settings_system.py
```

This verifies:

1. All profiles have required settings
2. Default values work correctly
3. Each profile has unique settings
4. Voice settings are configured
5. Conversation starters are valid

## Advanced: Per-Profile Customization

Beyond the basic settings, consider implementing:

- `max_memory_turns`: How many previous turns to remember per profile
- `energy_floor`: Audio energy threshold per profile
- `confidence_threshold`: When to end turn based on confidence score
- `custom_vocabulary`: Lexical bias for specific domains
- `allowed_interruption_keywords`: Profile-specific interrupt triggers
- `system_context`: Background information for the profile

These can be added to the profile dictionary and retrieved via `get_profile_settings()`.
