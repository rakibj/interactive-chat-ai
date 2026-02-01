# Per-Profile Settings System - Visual Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION LAYER                         │
│                         (config.py)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  INSTRUCTION_PROFILES Dictionary (6 profiles × 9 settings)       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ "profile_key": {                                         │   │
│  │   "name": "Human-Readable Name",                         │   │
│  │   "start": "ai" | "human",  ← Conversation Starter     │   │
│  │   "voice": "voice_name",    ← TTS Voice                │   │
│  │   "max_tokens": 100,        ← LLM Response Length      │   │
│  │   "temperature": 0.6,       ← LLM Creativity           │   │
│  │   "pause_ms": 600,          ← Pause Threshold          │   │
│  │   "end_ms": 1200,           ← End-of-Turn              │   │
│  │   "safety_timeout_ms": 2500,← Force End Timeout        │   │
│  │   "interruption_sensitivity": 0.3,← Interruption       │   │
│  │   "instructions": "System Prompt..."                    │   │
│  │ }                                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Helper Functions:                                               │
│  • get_profile_settings(profile_key)  → Returns merged dict      │
│  • get_system_prompt(profile_key)     → Returns full prompt      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                         ACTIVE_PROFILE
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  INITIALIZATION LAYER                            │
│                  (main.py: ConversationEngine)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Load profile_settings = get_profile_settings(ACTIVE_PROFILE) │
│                                                                   │
│  2. Apply to Components:                                         │
│     ├─ TurnTaker:                                                │
│     │  • pause_ms ← profile_settings["pause_ms"]                 │
│     │  • end_ms ← profile_settings["end_ms"]                     │
│     │  • safety_timeout_ms ← profile_settings["safety_timeout"]  │
│     │                                                             │
│     ├─ InterruptionManager:                                      │
│     │  • sensitivity ← profile_settings["interruption_sensitive"]│
│     │                                                             │
│     └─ Display at startup:                                       │
│        • name, voice, timeouts, start                            │
│                                                                   │
│  3. Store for runtime access:                                    │
│     • self.profile_settings (dict accessible throughout)         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION LAYER                               │
│              (Runtime Conversation Processing)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Turn-Taking Logic:                                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ IDLE → SPEAKING → PAUSING (with profile-specific timing)  │ │
│  │                                                             │ │
│  │ • Waits for PAUSE_MS silence → pause_ms from profile      │ │
│  │ • Accumulates until END_MS → end_ms from profile          │ │
│  │ • Forces end if SAFETY_TIMEOUT_MS → safety_timeout from   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Interruption Logic:                                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Checks if human should interrupt AI speech                │ │
│  │ Sensitivity: profile_settings["interruption_sensitivity"] │ │
│  │ • 0.0  → Never interrupt                                  │ │
│  │ • 0.5  → Interrupt sometimes                              │ │
│  │ • 1.0  → Always interrupt                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  LLM Calls:                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ llm.stream_completion(                                     │ │
│  │     system_prompt=get_system_prompt(profile),              │ │
│  │     messages=messages,                                     │ │
│  │     max_tokens=profile_settings["max_tokens"],             │ │
│  │     temperature=profile_settings["temperature"]            │ │
│  │ )                                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Conversation Starter:                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ if profile_settings["start"] == "ai":                      │ │
│  │     Generate AI greeting (using profile LLM settings)      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Profile Settings Map

```
Each Profile (6 Total)
│
├── BEHAVIOR SETTINGS (instructions, name)
│   └── AI behavior and conversation style
│
├── TIMING SETTINGS (pause_ms, end_ms, safety_timeout_ms)
│   ├── pause_ms: 400-1000ms
│   ├── end_ms: 800-2000ms
│   └── safety_timeout_ms: 2000-4000ms
│
├── INTERACTION SETTINGS (interruption_sensitivity, start)
│   ├── interruption_sensitivity: 0.0-1.0
│   └── start: "ai" or "human"
│
├── LLM SETTINGS (max_tokens, temperature)
│   ├── max_tokens: 80-150
│   └── temperature: 0.3-0.85
│
└── VOICE SETTINGS (voice)
    └── voice: "alba", "jean", "marius", "cosette", "fantine"
```

## Component Integration Matrix

```
                        TurnTaker  Interruption  LLM  TTS  Memory
                        ─────────  ────────────  ───  ───  ──────
pause_ms                    ✓           ✗        ✗   ✗    ✗
end_ms                      ✓           ✗        ✗   ✗    ✗
safety_timeout_ms           ✓           ✗        ✗   ✗    ✗
interruption_sensitivity    ✗           ✓        ✗   ✗    ✗
max_tokens                  ✗           ✗        ✓   ✗    ✗
temperature                 ✗           ✗        ✓   ✗    ✗
voice                       ✗           ✗        ✗   ✓    ✗
start                       ✗           ✗        ✓   ✗    ✗
instructions                ✗           ✗        ✓   ✗    ✗
name                        ✗           ✗        ✗   ✗    ✗
```

## Timing Relationships Visualization

```
negotiator:
pause_ms: 600 ├──────────────┤
end_ms: 1200  ├──────────────────────────────────┤
safety: 2500  ├──────────────────────────────────────────────────────────┤
             ×1.0           ×2.0                    ×2.08

ielts_instructor:
pause_ms: 800 ├──────────────┤
end_ms: 1500  ├──────────────────────────────────────────┤
safety: 3500  ├──────────────────────────────────────────────────────────────┤
             ×1.0          ×1.88                    ×2.33

technical_support:
pause_ms: 500 ├─────────┤
end_ms: 1000  ├─────────────────────────┤
safety: 2200  ├─────────────────────────────────────────────┤
             ×1.0      ×2.0                    ×2.20
```

## Temperature Scale

```
0.0 ───────────────────────────────────────────────────────→ 1.0
│                                                             │
Very Factual              Balanced              Very Creative
(Technical)            (Most profiles)         (Casual/Creative)
│                          │                         │
technical_support     negotiator              curious_friend
0.4                   ielts_instructor         0.75
                      0.6
```

## Interruption Sensitivity Scale

```
0.0 ────────────────────────────────────────────────────→ 1.0
│                                                        │
Never Interrupt      Professional    Conversational   Always
                                                    Interrupt
│                       │                 │              │
negotiator         technical_support   confused_     (hypothetical)
0.0                0.2, ielts 0.3    customer 0.5
                   language_tutor 0.1  curious_friend
                                       0.4
```

## State Diagram: TurnTaker with Profile Settings

```
                    ┌─────────────────┐
                    │      IDLE       │
                    │  (Listening)    │
                    └────────┬────────┘
                             │
                    (user starts talking)
                             │
                             ↓
                    ┌─────────────────┐
                    │    SPEAKING     │
                    │   (Audio in)    │
                    └────────┬────────┘
                             │
          (silence >= pause_ms from profile)
                             │
                             ↓
                    ┌─────────────────┐
                    │    PAUSING      │
                    │   (Waiting)     │
                    └────────┬────────┘
                             │
        (timer >= end_ms from profile)
                    OR
   (force timer >= safety_timeout_ms)
                             │
                             ↓
                    ┌─────────────────┐
                    │   TURN_ENDED    │
                    │  (Process text) │
                    └────────┬────────┘
                             │
                    (response generated)
                             │
                             ↓
                    ┌─────────────────┐
                    │      IDLE       │
                    └─────────────────┘
```

## Data Structure: Profile Settings Dictionary

```python
profile_settings = {
    'name': 'IELTS Speaking Instructor',
    'start': 'ai',
    'voice': 'jean',
    'max_tokens': 120,
    'temperature': 0.6,
    'pause_ms': 800,
    'end_ms': 1500,
    'safety_timeout_ms': 3500,
    'interruption_sensitivity': 0.3,
    'instructions': '...'  # Full system prompt text
}

# Access in code:
settings["max_tokens"]  # 120
settings["pause_ms"]    # 800
settings["voice"]       # "jean"
# ... etc
```

## File Organization

```
interactive-chat-ai/
├── config.py
│   ├── INSTRUCTION_PROFILES dict (6 profiles)
│   ├── get_profile_settings()
│   └── get_system_prompt()
│
├── main.py (ConversationEngine)
│   ├── __init__: Load profile_settings
│   ├── Components: Apply profile settings
│   ├── LLM calls: Use profile LLM settings
│   └── run(): Display profile info
│
├── core/
│   ├── turn_taker.py: pause_ms, end_ms, safety_timeout_ms
│   ├── interruption_manager.py: sensitivity
│   └── audio_manager.py, conversation_memory.py
│
├── interfaces/
│   ├── asr.py, llm.py, tts.py
│   └── Ready for per-profile voice
│
└── Tests/
    ├── test_profiles.py
    ├── test_settings_system.py
    └── test_e2e_integration.py
```

## Key Relationships

```
ACTIVE_PROFILE (1 line in config.py)
         │
         ├─→ get_profile_settings()
         │        └─→ INSTRUCTION_PROFILES[key]
         │            └─→ Returns: dict with 9 settings + defaults
         │
         └─→ ConversationEngine.__init__()
              ├─→ TurnTaker.pause_ms = settings["pause_ms"]
              ├─→ TurnTaker.end_ms = settings["end_ms"]
              ├─→ TurnTaker.safety_timeout_ms = settings["safety_timeout_ms"]
              ├─→ InterruptionManager.sensitivity = settings["interruption_sensitivity"]
              └─→ Store self.profile_settings for LLM calls
```

---

**Result**: One-line profile switch enables complete system reconfiguration without code changes. ✓
