# Quick Start Guide - Conversation Profiles

## 🚀 Quick Reference

### View All Profiles

```bash
uv run python .\interactive_chat\list_profiles.py
```

### Available Profiles & Keys

| Profile             | Key                 | Best For                  |
| ------------------- | ------------------- | ------------------------- |
| Negotiation (Buyer) | `negotiator`        | Price haggling            |
| IELTS Speaking Test | `ielts_instructor`  | English speaking practice |
| Confused Customer   | `confused_customer` | Customer service training |
| Technical Support   | `technical_support` | IT troubleshooting        |
| Language Tutor      | `language_tutor`    | English conversation      |
| Curious Friend      | `curious_friend`    | Casual chat               |

### Change Profile

Edit `interactive_chat/config.py`:

```python
ACTIVE_PROFILE = "ielts_instructor"
```

### Change Who Starts

Edit `interactive_chat/config.py`:

```python
CONVERSATION_START = "ai"  # AI starts, or "human"
```

### Run

```bash
uv run python .\interactive_chat\main.py
```

---

## 📚 Profile Descriptions

### 1️⃣ **Negotiator** (Default)

- **You are**: Buyer
- **AI is**: Seller
- **Goal**: Negotiate price down
- **Behavior**: Push back on price, question value

**Config:**

```python
ACTIVE_PROFILE = "negotiator"
CONVERSATION_START = "human"
```

---

### 2️⃣ **IELTS Instructor**

- **You are**: Test taker
- **AI is**: IELTS examiner
- **Goal**: Complete speaking test
- **Structure**:
  - Part 1: Personal questions
  - Part 2: Long turn with topic
  - Part 3: Discussion questions

**Config:**

```python
ACTIVE_PROFILE = "ielts_instructor"
CONVERSATION_START = "human"  # You go first with your answers
```

---

### 3️⃣ **Confused Customer**

- **You are**: Support agent
- **AI is**: Confused customer
- **Goal**: Help resolve their issue
- **Behavior**: Customer is confused, frustrated, asks repeatedly

**Config:**

```python
ACTIVE_PROFILE = "confused_customer"
CONVERSATION_START = "ai"  # Customer explains their problem first
```

---

### 4️⃣ **Technical Support**

- **You are**: User with problem
- **AI is**: Support agent
- **Goal**: Get tech problem solved
- **Behavior**: Agent asks diagnostic questions, suggests solutions

**Config:**

```python
ACTIVE_PROFILE = "technical_support"
CONVERSATION_START = "ai"  # Agent greets you
```

---

### 5️⃣ **Language Tutor**

- **You are**: Student
- **AI is**: English tutor
- **Goal**: Practice English conversation
- **Behavior**: Tutor corrects gently, expands vocabulary

**Config:**

```python
ACTIVE_PROFILE = "language_tutor"
CONVERSATION_START = "ai"  # Tutor starts lesson
```

---

### 6️⃣ **Curious Friend**

- **You are**: Friend chatting
- **AI is**: Curious friend
- **Goal**: Have natural conversation
- **Behavior**: Friend asks questions, shares stories, remembers details

**Config:**

```python
ACTIVE_PROFILE = "curious_friend"
CONVERSATION_START = "ai"  # Friend greets you warmly
```

---

## 🎮 Example Scenarios

### Scenario 1: Prepare for IELTS

```python
CONVERSATION_START = "human"
ACTIVE_PROFILE = "ielts_instructor"
```

→ Run → Start speaking answers

### Scenario 2: Customer Service Training

```python
CONVERSATION_START = "ai"
ACTIVE_PROFILE = "confused_customer"
```

→ Run → Listen to customer's problem

### Scenario 3: Negotiate Phone Price

```python
CONVERSATION_START = "human"
ACTIVE_PROFILE = "negotiator"
```

→ Run → "I want to buy that phone..."

### Scenario 4: Get Tech Help

```python
CONVERSATION_START = "ai"
ACTIVE_PROFILE = "technical_support"
```

→ Run → Explain your tech problem

---

## ⚙️ Add Custom Profile

Edit `interactive_chat/config.py` and add to `INSTRUCTION_PROFILES`:

```python
"my_profile": {
    "name": "Display Name",
    "instructions": """
ROLE: What you are

OBJECTIVE: What you're trying to do

BEHAVIOR: How you act

TONE: Your personality
    """,
},
```

Then use:

```python
ACTIVE_PROFILE = "my_profile"
```

---

## 🛑 Exit

- Press **Ctrl+C** to exit cleanly

---

## 📊 View Current Settings

```bash
uv run python .\interactive_chat\list_profiles.py
```

Shows:

- All available profiles
- Current `CONVERSATION_START`
- Current `ACTIVE_PROFILE`
