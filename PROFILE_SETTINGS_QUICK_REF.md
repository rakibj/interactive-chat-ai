# Per-Profile Settings - Quick Reference

## The 9 Settings Per Profile

```
1. name              → Human-readable profile name
2. start             → Who speaks first: "ai" or "human"
3. voice             → TTS voice: "alba", "jean", "marius", "cosette", "fantine"
4. max_tokens        → LLM max response length (typically 80-150)
5. temperature       → LLM creativity (0.0-1.0, higher = more creative)
6. pause_ms          → Pause threshold before allowing interruption (ms)
7. end_ms            → End-of-turn threshold (ms)
8. safety_timeout_ms → Force turn end if this duration exceeded (ms)
9. interruption_sensitivity → How easily interrupted (0.0-1.0)
```

## Example: Check Current Settings

```python
from interactive_chat.config import get_profile_settings

# Get all settings for a profile
settings = get_profile_settings("ielts_instructor")

print(settings)
# Output:
# {
#     'name': 'IELTS Speaking Instructor',
#     'start': 'ai',
#     'voice': 'jean',
#     'max_tokens': 120,
#     'temperature': 0.6,
#     'pause_ms': 800,
#     'end_ms': 1500,
#     'safety_timeout_ms': 3500,
#     'interruption_sensitivity': 0.3,
#     'instructions': '...'
# }
```

## Example: List All Profiles

```bash
python test_profiles.py
```

Output shows each profile with its complete settings.

## Example: Create New Profile

Add to `interactive_chat/config.py` INSTRUCTION_PROFILES:

```python
"therapist": {
    "name": "AI Therapist",
    "start": "ai",
    "voice": "fantine",
    "max_tokens": 150,
    "temperature": 0.7,
    "pause_ms": 1000,  # More pause for thoughtful responses
    "end_ms": 2000,    # Longer turns
    "safety_timeout_ms": 4000,
    "interruption_sensitivity": 0.1,  # Hard to interrupt
    "instructions": "You are a compassionate AI therapist...",
},
```

## Profile Characteristics

| Profile               | Role                | Timing              | Interaction                    | LLM                                  |
| --------------------- | ------------------- | ------------------- | ------------------------------ | ------------------------------------ |
| **negotiator**        | Buyer negotiating   | Quick (600/1200)    | Aggressive (0.0 interrupt)     | Brief, factual (80 tokens, 0.5 temp) |
| **ielts_instructor**  | Language test guide | Measured (800/1500) | Moderate (0.3 interrupt)       | Detailed (120 tokens, 0.6 temp)      |
| **confused_customer** | Customer support    | Standard (700/1400) | Conversational (0.5 interrupt) | Helpful (90 tokens, 0.7 temp)        |
| **technical_support** | Tech support agent  | Quick (500/1000)    | Professional (0.2 interrupt)   | Concise (100 tokens, 0.4 temp)       |
| **language_tutor**    | English tutor       | Standard (700/1400) | Teaching (0.1 interrupt)       | Encouraging (110 tokens, 0.6 temp)   |
| **curious_friend**    | Casual friend       | Natural (750/1300)  | Friendly (0.4 interrupt)       | Creative (95 tokens, 0.75 temp)      |

## Key Formulas

### Recommended Timing Relationships

- Safety timeout ≈ 2.0-2.5x end_ms
- End_ms ≈ 1.5-2.0x pause_ms

Example (ielts_instructor):

- pause_ms: 800
- end_ms: 1500 (≈ 1.875x pause)
- safety_timeout_ms: 3500 (≈ 2.33x end_ms)

### Interruption Sensitivity

- 0.0 = Wait for complete response (professional)
- 0.5 = Natural interruption (conversational)
- 1.0 = Constant interruptions (aggressive)

### Temperature

- 0.4 = Factual, consistent (technical)
- 0.6 = Balanced (most profiles)
- 0.75+ = Creative, varied (casual)

## Using Profile Settings

### In ConversationEngine

```python
engine = ConversationEngine(profile_name="ielts_instructor")
# All settings automatically applied!
```

### Manual Application

```python
from interactive_chat.config import get_profile_settings
from interactive_chat.core.turn_taker import TurnTaker
from interactive_chat.core.interruption_manager import InterruptionManager

settings = get_profile_settings("ielts_instructor")

turn_taker = TurnTaker()
turn_taker.pause_ms = settings["pause_ms"]
turn_taker.end_ms = settings["end_ms"]
turn_taker.safety_timeout_ms = settings["safety_timeout_ms"]

interruption_mgr = InterruptionManager()
interruption_mgr.set_sensitivity(settings["interruption_sensitivity"])

# Use in LLM calls:
llm.stream_completion(
    system_prompt=...,
    messages=...,
    max_tokens=settings["max_tokens"],
    temperature=settings["temperature"],
)
```

## Modifying Profiles

Edit `interactive_chat/config.py` INSTRUCTION_PROFILES, then restart the application.

```python
"ielts_instructor": {
    # ... change any setting ...
    "max_tokens": 150,  # Changed!
    # ... restart to take effect ...
},
```

## Validation

Run tests to verify settings:

```bash
python test_settings_system.py  # Comprehensive test
python test_profiles.py         # Show all profiles
python test_main_profiles.py    # Test main.py integration
```

All tests should pass ✓
