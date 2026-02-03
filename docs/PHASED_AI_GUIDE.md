# Phased AI System - Complete Guide

## Overview

The **Phased AI System** enables deterministic, signal-driven transitions between conversation phases. This allows you to build complex, multi-stage interactions (like exams, sales calls, or support flows) where the AI automatically progresses through phases based on signals it emits.

## Key Concepts

### 1. InstructionProfile (Unchanged)

InstructionProfiles work **standalone** or as **phases within a PhaseProfile**.

```python
class InstructionProfile(BaseModel):
    name: str                           # Display name
    start: str                          # "human" or "ai"
    voice: str                          # TTS voice
    max_tokens: int                     # LLM response limit
    temperature: float                  # LLM creativity
    pause_ms: int                       # Turn-taking timeout
    end_ms: int                         # Turn end timeout
    safety_timeout_ms: int              # Force turn end
    interruption_sensitivity: float     # 0.0-1.0
    authority: str                      # "human", "ai", "default"
    human_speaking_limit_sec: Optional[int]
    acknowledgments: List[str]
    instructions: str                   # System prompt
    signals: dict[str, str]             # Signal name → description
```

**Key Point**: When used in a PhaseProfile, additional context is injected automatically.

### 2. PhaseProfile (New)

A container for multi-phase conversations with deterministic transitions.

```python
class PhaseProfile(BaseModel):
    name: str                                   # Display name
    phases: dict[str, InstructionProfile]       # phase_id → profile
    transitions: List[PhaseTransition]          # Transition rules
    initial_phase: str                          # Starting phase ID
    phase_context: Optional[str]                # Global context for all phases
    per_phase_context: Optional[dict[str, str]] # Phase-specific context
```

**Methods**:

- `get_phase(phase_id)`: Get InstructionProfile by ID
- `get_phase_context(phase_id)`: Get full context (global + phase-specific)
- `find_transition(current_phase, emitted_signals)`: Find next phase based on signals

### 3. PhaseTransition (New)

Defines how to move from one phase to another based on signals.

```python
class PhaseTransition(BaseModel):
    from_phase: str                # Phase ID to transition from
    to_phase: str                  # Phase ID to transition to
    trigger_signals: List[str]     # Signals that trigger transition
    require_all: bool = False      # If True, all signals must fire; if False, any one triggers
```

## How It Works

### Signal-Based Transitions

1. **AI emits signals** during response generation (in `<signals></signals>` blocks)
2. **System extracts signals** from LLM response
3. **Transition logic checks** if any signals match transition rules
4. **Phase changes** if transition condition met
5. **New profile activated** with updated settings and context

### Flow Example (IELTS Test)

```
greeting phase
  ↓ LLM emits: custom.exam.greeting_complete
part1 phase (4-5 personal questions)
  ↓ LLM emits: custom.exam.questions_completed
part2 phase (1-2 minute monologue)
  ↓ LLM emits: custom.exam.monologue_complete
part3 phase (abstract discussion)
  ↓ LLM emits: custom.exam.discussion_complete
closing phase (farewell)
```

### Context Injection

When running a phase, the system prompt is constructed as:

```
SYSTEM_PROMPT_BASE
+ Signal hints (from profile.signals)
+ Phase context (global + phase-specific)
+ Profile instructions
```

This gives the AI full awareness of:

- What phase it's in
- What signals it can emit
- What its role is in this phase

## Creating a PhaseProfile

### Example: Simple Two-Phase Tutorial

```python
tutorial_profile = PhaseProfile(
    name="Programming Tutorial",
    initial_phase="introduction",
    phase_context="You are teaching a beginner programmer. Be patient and clear.",

    phases={
        "introduction": InstructionProfile(
            name="Tutorial - Introduction",
            start="ai",
            voice="alba",
            max_tokens=80,
            temperature=0.6,
            pause_ms=600,
            end_ms=1200,
            safety_timeout_ms=2500,
            interruption_sensitivity=0.6,
            authority="default",
            signals={
                "tutorial.ready_to_code": "Student is ready to start coding.",
            },
            instructions="Introduce yourself and explain what we'll learn today. Ask if they're ready to start."
        ),

        "coding": InstructionProfile(
            name="Tutorial - Coding",
            start="ai",
            voice="alba",
            max_tokens=120,
            temperature=0.6,
            pause_ms=600,
            end_ms=1200,
            safety_timeout_ms=2500,
            interruption_sensitivity=0.6,
            authority="default",
            signals={
                "tutorial.exercise_complete": "Student completed the exercise.",
            },
            instructions="Guide them through coding exercises. Give hints when stuck."
        ),
    },

    transitions=[
        PhaseTransition(
            from_phase="introduction",
            to_phase="coding",
            trigger_signals=["custom.tutorial.ready_to_code"],
            require_all=False
        ),
    ],
)

# Add to PHASE_PROFILES dict
PHASE_PROFILES["tutorial"] = tutorial_profile
```

### Using the PhaseProfile

In `config.py`:

```python
ACTIVE_PHASE_PROFILE = "tutorial"  # Set this to activate
# ACTIVE_PROFILE is ignored when ACTIVE_PHASE_PROFILE is set
```

Run normally:

```bash
python interactive_chat/main.py
```

The system will:

1. Start in "introduction" phase
2. AI greets and introduces the tutorial
3. When AI emits `custom.tutorial.ready_to_code` signal
4. System transitions to "coding" phase
5. New profile settings and context take effect

## Built-in Examples

### 1. IELTS Full Exam (`ielts_full_exam`)

**Phases**: greeting → part1 → part2 → part3 → closing

**Use Case**: Complete IELTS Speaking test simulation with proper structure and timing.

**Key Features**:

- AI authority (controlled test environment)
- Phase-specific timing (longer timeouts for Part 2 monologue)
- Structured progression through test sections

### 2. Sales Call (`sales_call`)

**Phases**: opening → discovery → pitch → objection_handling → close

**Use Case**: Structured sales conversation with branching logic.

**Key Features**:

- Default authority (balanced conversation)
- Branching transitions (pitch can go to objection_handling OR close)
- Loop-back (objection_handling can return to pitch)

## Advanced Features

### Branching Transitions

Multiple transitions from one phase:

```python
PhaseTransition(
    from_phase="pitch",
    to_phase="objection_handling",
    trigger_signals=["custom.sales.objection_raised"],
),
PhaseTransition(
    from_phase="pitch",
    to_phase="close",
    trigger_signals=["custom.sales.value_presented"],
),
```

The first matching transition wins.

### Loop-Back Transitions

Return to previous phases:

```python
PhaseTransition(
    from_phase="objection_handling",
    to_phase="pitch",  # Go back!
    trigger_signals=["custom.sales.needs_more_info"],
),
```

### Multi-Signal Triggers

Require multiple signals:

```python
PhaseTransition(
    from_phase="assessment",
    to_phase="recommendation",
    trigger_signals=[
        "custom.assessment.symptoms_collected",
        "custom.assessment.medical_history_obtained",
    ],
    require_all=True,  # Both must be emitted
),
```

### Per-Phase Context

Different context for each phase:

```python
per_phase_context={
    "greeting": "Be warm and welcoming.",
    "diagnosis": "Be analytical and precise.",
    "treatment": "Be clear about next steps.",
}
```

## System Architecture

### Event Flow

```
LLM generates response with signals
    ↓
_extract_signals() parses <signals></signals> blocks
    ↓
_check_phase_transitions() checks transition rules
    ↓
PHASE_TRANSITION event emitted
    ↓
Reducer handles event → TRANSITION_PHASE action
    ↓
_transition_to_phase() executes:
    - Load new profile
    - Update state settings
    - Clear signal history
    - Generate AI greeting if needed
```

### State Tracking

SystemState tracks:

- `current_phase_id`: Active phase ID (None if standalone)
- `phase_profile_name`: Active PhaseProfile name (None if standalone)

ConversationEngine tracks:

- `active_phase_profile`: PhaseProfile object
- `phase_emitted_signals`: List of signals emitted in current phase

### System Prompt Construction

**Standalone Mode**:

```
SYSTEM_PROMPT_BASE + signal_hints + profile.instructions
```

**Phase Mode**:

```
SYSTEM_PROMPT_BASE + signal_hints + phase_context + profile.instructions
```

## Testing

### Standalone Test Script

```bash
python test_phase_profiles.py
```

Tests:

- ✅ PhaseProfile structure validation
- ✅ Transition logic
- ✅ Context injection
- ✅ Standalone vs Phase mode compatibility

### Integration Testing

Use headless testing framework:

```python
# In tests/test_phases.py
def test_phase_transition():
    from config import PHASE_PROFILES

    profile = PHASE_PROFILES["ielts_full_exam"]

    # Verify transition logic
    next_phase = profile.find_transition("greeting", ["custom.exam.greeting_complete"])
    assert next_phase == "part1"
```

## Best Practices

### 1. Signal Naming

Use consistent namespacing:

- `exam.*` for test-related signals
- `sales.*` for sales-related signals
- `tutorial.*` for tutorial-related signals

### 2. Phase Granularity

**Too Fine**: Micro-managing every sentence

- ❌ phases: "ask_name", "ask_age", "ask_hobby"

**Too Coarse**: Missing structure

- ❌ phases: "beginning", "middle", "end"

**Just Right**: Meaningful stages

- ✅ phases: "intake", "diagnosis", "treatment", "follow_up"

### 3. Transition Signals

**Clear and Specific**:

- ✅ `custom.exam.questions_completed`
- ❌ `custom.done`

**Observable from Response**:

- ✅ AI can determine when questions are complete
- ❌ Don't rely on external state

### 4. Phase Context

**Inform, Don't Over-Constrain**:

- ✅ "This is Part 2. Give the candidate 1-2 minutes to speak."
- ❌ "Say exactly: 'Now we'll move to Part 2.'"

## Migration Guide

### From Standalone to PhaseProfile

**Before** (single profile):

```python
ACTIVE_PROFILE = "ielts_instructor"
```

**After** (phased profile):

```python
ACTIVE_PHASE_PROFILE = "ielts_full_exam"
```

No code changes needed! The system automatically:

- Detects PhaseProfile mode
- Injects phase context
- Manages transitions
- Updates profile settings

## Debugging

### Enable Phase Logging

Look for these log messages:

- `🎭 Starting PhaseProfile: <name>`
- `🔀 Initial phase: <name>`
- `🔀 Phase transition to: <name>`
- `✅ Transitioned to phase: <name>`

### Check Signal Emission

Signals are logged in conversation memory but stripped from visible output. Check:

1. LLM is emitting signals in correct format: `<signals>{"signal.name": {...}}</signals>`
2. Signal names match `trigger_signals` in transitions (with `custom.` prefix)
3. Transitions are defined for current phase

### Common Issues

**Transition not triggering**:

- Verify signal name includes `custom.` prefix in transition definition
- Check LLM is actually emitting the signal
- Ensure `from_phase` matches current phase

**Context not appearing**:

- Use `_get_current_system_prompt()` helper method
- Verify `phase_context` or `per_phase_context` is set
- Check phase_id is valid

## Future Enhancements

Potential extensions:

- **Conditional transitions**: Add predicates beyond signals
- **Phase analytics**: Track time spent in each phase
- **Dynamic phases**: Generate phases on-the-fly
- **Parallel phases**: Run multiple sub-phases concurrently
- **Phase memory**: Share data between phases

## Summary

The Phased AI System provides:

✅ **Deterministic control** over conversation flow
✅ **Signal-driven** transitions (no hardcoded logic)
✅ **Backward compatible** (standalone profiles still work)
✅ **Flexible** (linear, branching, or loop-back flows)
✅ **Context-aware** (each phase gets custom instructions)
✅ **Testable** (pure functions, no side effects)

Perfect for:

- 🎓 Educational content (tutorials, lessons, exams)
- 💼 Business flows (sales, support, onboarding)
- 🏥 Healthcare (triage, diagnosis, treatment)
- 📋 Structured interviews (job interviews, surveys)

Start simple, iterate, and build sophisticated multi-phase interactions!
