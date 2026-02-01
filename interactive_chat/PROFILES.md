"""Configuration and Profile Guide

This system supports multiple conversation profiles and configurations.

## Quick Start

1. View available profiles:

   ```
   uv run python .\interactive_chat\list_profiles.py
   ```

2. Edit config.py to set your profile:

   ```python
   CONVERSATION_START = "human"  # or "ai"
   ACTIVE_PROFILE = "negotiator"  # or other profile key
   ```

3. Run the chat:
   ```
   uv run python .\interactive_chat\main.py
   ```

## Conversation Starters

- **"human"**: You speak first. AI listens and responds.
- **"ai"**: AI greets you first and starts the conversation.

## Available Profiles

### 1. negotiator

- Role: You're a buyer negotiating price
- Best for: Price negotiations, haggling scenarios
- Behavior: Pushes back on price, questions value claims, counteroffers aggressively

### 2. ielts_instructor

- Role: IELTS Speaking Test instructor
- Best for: English speaking practice, test preparation
- Structure:
  - Part 1: Personal questions (4-5 questions)
  - Part 2: Long turn with cue card topic
  - Part 3: Discussion follow-ups
- Behavior: Guides through simplified IELTS format

### 3. confused_customer

- Role: A confused customer with a support issue
- Best for: Customer service role-play
- Behavior: Expresses confusion, frustration, asks clarifying questions

### 4. technical_support

- Role: Tech support agent troubleshooting
- Best for: IT support practice, technical Q&A
- Behavior: Asks diagnostic questions, explains simply, suggests solutions

### 5. language_tutor

- Role: English language tutor for conversation
- Best for: ESL/EFL practice, vocabulary building
- Behavior: Corrects gently, expands vocabulary, provides feedback

### 6. curious_friend

- Role: A naturally curious friend
- Best for: Casual conversation practice, natural dialogue
- Behavior: Asks genuine questions, shares anecdotes, remembers details

## Examples

### Example 1: IELTS Practice

```python
CONVERSATION_START = "human"
ACTIVE_PROFILE = "ielts_instructor"
```

Run: `uv run python .\interactive_chat\main.py`
Then speak naturally - the AI will guide you through an IELTS-style test.

### Example 2: Language Tutor (AI starts)

```python
CONVERSATION_START = "ai"
ACTIVE_PROFILE = "language_tutor"
```

Run: `uv run python .\interactive_chat\main.py`
The AI will greet you and start a conversation.

### Example 3: Customer Service Role-Play

```python
CONVERSATION_START = "human"
ACTIVE_PROFILE = "confused_customer"
```

Run: `uv run python .\interactive_chat\main.py`
You're now helping a confused customer!

## Customizing Profiles

To add a new profile, edit config.py:

```python
INSTRUCTION_PROFILES = {
    "my_new_profile": {
        "name": "Display Name",
        "instructions": """
ROLE: Your role description

BEHAVIOR: What you should do

TONE: Your tone/personality
        """,
    },
    # ... other profiles
}
```

Then add the key to ACTIVE_PROFILE options.

## System Prompt Structure

The complete system prompt is built from:

1. **SYSTEM_PROMPT_BASE**: General conversation behavior (always used)
2. **Profile Instructions**: Specific role and behavior (profile-specific)

This ensures consistency while allowing role customization.
"""
