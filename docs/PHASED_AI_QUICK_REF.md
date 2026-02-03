# Phased AI - Quick Reference

## Basic Usage

### Activate a PhaseProfile

In `config.py`:

```python
ACTIVE_PHASE_PROFILE = "ielts_full_exam"  # or "sales_call"
```

Run normally:

```bash
python interactive_chat/main.py
```

## Create a Simple PhaseProfile

```python
from config import PhaseProfile, PhaseTransition, InstructionProfile

my_profile = PhaseProfile(
    name="My Workflow",
    initial_phase="start",
    phase_context="Global context for all phases",

    phases={
        "start": InstructionProfile(
            name="Start Phase",
            start="ai",  # AI speaks first
            voice="alba",
            max_tokens=80,
            temperature=0.6,
            pause_ms=600,
            end_ms=1200,
            safety_timeout_ms=2500,
            interruption_sensitivity=0.6,
            authority="default",
            signals={
                "workflow.ready_to_proceed": "User is ready for next step.",
            },
            instructions="Your instructions here..."
        ),

        "next": InstructionProfile(
            name="Next Phase",
            # ... same structure ...
            signals={
                "workflow.task_complete": "Task is done.",
            },
            instructions="Next phase instructions..."
        ),
    },

    transitions=[
        PhaseTransition(
            from_phase="start",
            to_phase="next",
            trigger_signals=["custom.workflow.ready_to_proceed"],
            require_all=False  # Any one signal triggers
        ),
    ],
)

# Add to config
PHASE_PROFILES["my_workflow"] = my_profile
```

## Signal Format

### In LLM Response

```
Your AI response text here.

<signals>
{
  "custom.workflow.ready_to_proceed": {
    "confidence": 0.9,
    "reason": "User confirmed readiness"
  }
}
</signals>
```

### In Profile Definition

```python
signals={
    "workflow.ready_to_proceed": "Description of when to emit this signal.",
}
```

**Note**: Profile defines without `custom.` prefix, but LLM emits with `custom.` prefix.

## Transition Types

### Simple (One-to-One)

```python
PhaseTransition(
    from_phase="intro",
    to_phase="main",
    trigger_signals=["custom.intro.complete"],
)
```

### Branching (One-to-Many)

```python
# From "assessment" can go to either "treatment" OR "referral"
PhaseTransition(
    from_phase="assessment",
    to_phase="treatment",
    trigger_signals=["custom.assessment.mild_case"],
),
PhaseTransition(
    from_phase="assessment",
    to_phase="referral",
    trigger_signals=["custom.assessment.severe_case"],
),
```

### Loop-Back

```python
PhaseTransition(
    from_phase="practice",
    to_phase="lesson",  # Go back!
    trigger_signals=["custom.practice.needs_review"],
),
```

### Multi-Signal (AND Logic)

```python
PhaseTransition(
    from_phase="intake",
    to_phase="diagnosis",
    trigger_signals=[
        "custom.intake.symptoms_collected",
        "custom.intake.history_collected"
    ],
    require_all=True,  # Both must be emitted
)
```

## Built-in Examples

### IELTS Full Exam

```python
ACTIVE_PHASE_PROFILE = "ielts_full_exam"
```

Phases: greeting → part1 → part2 → part3 → closing

### Sales Call

```python
ACTIVE_PHASE_PROFILE = "sales_call"
```

Phases: opening → discovery → pitch → objection_handling ⟷ close

## Phase Context

### Global Context (All Phases)

```python
phase_context="This context applies to every phase."
```

### Per-Phase Context

```python
per_phase_context={
    "intro": "Be friendly and warm.",
    "assessment": "Be analytical and thorough.",
    "conclusion": "Be clear about next steps.",
}
```

## Testing

```bash
# Test structure and logic
python test_phase_profiles.py

# Test in conversation
ACTIVE_PHASE_PROFILE = "ielts_full_exam"
python interactive_chat/main.py
```

## Debugging

### Check Current Phase

Look for log messages:

- `🎭 Starting PhaseProfile: <name>`
- `🔀 Initial phase: <phase_name>`
- `✅ Transitioned to phase: <phase_name>`

### Verify Signal Emission

Signals appear in logs but not in spoken output. Check:

1. LLM emits: `<signals>{"custom.signal.name": {...}}</signals>`
2. Transition uses: `trigger_signals=["custom.signal.name"]`
3. Signal name matches exactly (including `custom.` prefix)

### Common Issues

| Issue                     | Solution                                                   |
| ------------------------- | ---------------------------------------------------------- |
| Transition not triggering | Verify signal name includes `custom.` prefix in transition |
| Phase context not working | Use `get_system_prompt_with_phase_context()`               |
| Settings not updating     | Check `_transition_to_phase()` updates `self.state`        |

## API Reference

### PhaseProfile Methods

```python
profile.get_phase(phase_id: str) -> InstructionProfile
profile.get_phase_context(phase_id: str) -> str
profile.find_transition(current_phase: str, signals: List[str]) -> Optional[str]
```

### ConversationEngine Methods

```python
engine._transition_to_phase(next_phase_id: str) -> None
engine._check_phase_transitions(emitted_signals: List[str]) -> None
engine._extract_signals(response_text: str) -> List[str]
engine._get_current_system_prompt() -> str
```

## Signal Naming Convention

Format: `namespace.action_or_state`

Good:

- ✅ `exam.questions_completed`
- ✅ `sales.objection_raised`
- ✅ `tutorial.exercise_passed`

Avoid:

- ❌ `done`
- ❌ `next`
- ❌ `complete`

## System Prompt Structure

**Standalone Mode:**

```
SYSTEM_PROMPT_BASE
+ Signal hints (from profile.signals)
+ Profile instructions
```

**Phase Mode:**

```
SYSTEM_PROMPT_BASE
+ Signal hints (from profile.signals)
+ === PHASE CONTEXT ===
+ Phase context (global + per-phase)
+ ===================
+ Profile instructions
```

## Architecture

```
LLM emits signals in response
    ↓
_extract_signals() parses them
    ↓
_check_phase_transitions() checks rules
    ↓
PHASE_TRANSITION event → Reducer
    ↓
TRANSITION_PHASE action → Handler
    ↓
_transition_to_phase() executes:
    - Load new profile
    - Update state
    - Clear signal history
    - Generate AI turn if needed
```

## Key Files

- `config.py`: Define PhaseProfiles, PhaseTransitions
- `core/event_driven_core.py`: PHASE_TRANSITION event, TRANSITION_PHASE action
- `main.py`: Transition logic, signal extraction
- `test_phase_profiles.py`: Validation tests
- `docs/PHASED_AI_GUIDE.md`: Comprehensive guide

## Backward Compatibility

✅ **Standalone profiles still work!**

If `ACTIVE_PHASE_PROFILE = None`:

- System uses `ACTIVE_PROFILE` (single InstructionProfile)
- No phase context injected
- No transitions checked
- Works exactly as before

## Cheat Sheet

| Task                   | Code                                        |
| ---------------------- | ------------------------------------------- |
| Activate phase profile | `ACTIVE_PHASE_PROFILE = "name"`             |
| Define new phase       | Add to `PHASE_PROFILES` dict                |
| Add transition         | Append to `transitions` list                |
| Emit signal (LLM)      | `<signals>{"custom.name": {...}}</signals>` |
| Test transitions       | `python test_phase_profiles.py`             |
| Debug current phase    | Check `state.current_phase_id`              |

---

For full details, see [PHASED_AI_GUIDE.md](PHASED_AI_GUIDE.md)
