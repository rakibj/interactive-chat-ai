# Profile System Implementation Summary

## ✅ What Was Added

### 1. **Conversation Starter Configuration**

```python
CONVERSATION_START = "human"  # or "ai"
```

- **"human"**: You speak first, AI listens and responds
- **"ai"**: AI greets you and starts the conversation

### 2. **Profile System**

```python
ACTIVE_PROFILE = "negotiator"  # Select your profile
```

Available profiles:

- **negotiator**: Price negotiation role-play (buyer)
- **ielts_instructor**: IELTS speaking test guide
- **confused_customer**: Customer service scenario
- **technical_support**: IT troubleshooting agent
- **language_tutor**: English conversation tutor
- **curious_friend**: Casual friendly conversation

### 3. **Dynamic System Prompt**

- **SYSTEM_PROMPT_BASE**: General conversation behavior (always used)
- **INSTRUCTION_PROFILES**: Role-specific instructions per profile
- **get_system_prompt()**: Function to build complete prompt from profile

### 4. **Helper Scripts**

- **list_profiles.py**: View all available profiles and current config
- **run_with_profile.py**: Interactive CLI to select profile (beta)

## 📝 Configuration Files Modified

### config.py

- Added `CONVERSATION_START` setting
- Added `ACTIVE_PROFILE` setting
- Added `LLM_MAX_TOKENS` and `LLM_TEMPERATURE` (restored)
- Added `SYSTEM_PROMPT_BASE` (general behavior)
- Added `INSTRUCTION_PROFILES` dictionary with 6 profiles
- Added `get_system_prompt(profile_key)` function

### main.py

- Updated imports to use `get_system_prompt()` instead of `SYSTEM_PROMPT`
- Added `CONVERSATION_START` and `ACTIVE_PROFILE` imports
- Added `_generate_ai_greeting()` method for AI-starts mode
- Updated `run()` to display profile and starter on startup
- Updated `run()` to call AI greeting if `CONVERSATION_START == "ai"`
- Updated `_process_turn()` to get system prompt dynamically

## 🎯 How to Use

### View Available Profiles

```bash
uv run python .\interactive_chat\list_profiles.py
```

### Change Settings

Edit `interactive_chat/config.py`:

```python
CONVERSATION_START = "ai"  # AI starts
ACTIVE_PROFILE = "ielts_instructor"  # IELTS mode
```

### Run

```bash
uv run python .\interactive_chat\main.py
```

## 🎭 Profile Examples

### IELTS Speaking Practice

```python
CONVERSATION_START = "human"
ACTIVE_PROFILE = "ielts_instructor"
```

✨ AI guides you through IELTS test format

### Language Tutoring

```python
CONVERSATION_START = "ai"
ACTIVE_PROFILE = "language_tutor"
```

✨ AI greets you and starts a tutoring conversation

### Price Negotiation

```python
CONVERSATION_START = "human"
ACTIVE_PROFILE = "negotiator"
```

✨ You negotiate prices with AI as buyer

## 🔧 Adding Custom Profiles

Edit `interactive_chat/config.py`:

```python
INSTRUCTION_PROFILES = {
    "my_custom_profile": {
        "name": "My Custom Role",
        "instructions": """
ROLE: What you are

BEHAVIOR: What you do

TONE: Your personality
        """,
    },
    # ... other profiles
}
```

Then use:

```python
ACTIVE_PROFILE = "my_custom_profile"
```

## 📊 Architecture

```
config.py
├── CONVERSATION_START ─────────┐
├── ACTIVE_PROFILE ─────────────┤
├── SYSTEM_PROMPT_BASE ─────────┼──> get_system_prompt()
├── INSTRUCTION_PROFILES ───────┤       │
└── get_system_prompt() ────────┘       │
                                        ├──> main.py
                                        │    ├── _generate_ai_greeting()
                                        │    ├── _process_turn()
                                        │    └── run()
```

## ✨ Key Features

✅ **Flexible Roles**: 6 pre-built profiles, easily extensible
✅ **Dynamic Prompts**: System prompt built from base + profile
✅ **Configurable Start**: Choose who initiates conversation  
✅ **AI Greeting**: AI generates contextual opening based on profile
✅ **Easy Config**: Simple one-line changes to switch modes
✅ **Profile Discovery**: Built-in script to view all profiles
