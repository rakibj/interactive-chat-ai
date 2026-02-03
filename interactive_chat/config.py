"""Centralized configuration for interactive chat system."""
import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

# Paths
PROJECT_ROOT = Path(r"D:\Work\Projects\AI\interactive-chat-ai")
MODELS_ROOT = PROJECT_ROOT / "models"

# Audio Configuration
SAMPLE_RATE = 16000
VAD_MIN_SAMPLES = 512
VOSK_MIN_SAMPLES = 3200  # 0.2 sec @ 16kHz
POCKET_SAMPLE_RATE = 24000

# Turn-taking Configuration
PAUSE_MS = 600
END_MS = 1200
SAFETY_TIMEOUT_MS = 2500
ENERGY_FLOOR = 0.015
WHISPER_WINDOW_SEC = 3.0
CONFIDENCE_THRESHOLD = 1.2
INTERRUPT_DEBOUNCE_MS = 250

# ASR Configuration
# Real-time ASR: Uses Vosk for low-latency streaming partials (closed-caption updates)
VOSK_MODEL_PATH = str(MODELS_ROOT / "vosk-model-small-en-us-0.15")

# Turn-end ASR: Options for final transcription
# - "local": WhisperLocalASR (local Whisper model, slower but free)
# - "cloud": WhisperCloudASR (OpenAI API, requires OPENAI_API_KEY, faster and more accurate)
TURN_END_ASR_MODE = "cloud"  # Choose "local" or "cloud"
WHISPER_MODEL_PATH = str(MODELS_ROOT / "whisper" / "distil-small.en")
WHISPER_CLOUD_MODEL = "gpt-4o-mini-transcribe"  # For cloud: gpt-4o-mini-transcribe, gpt-4o-transcribe

# LLM Configuration
LLM_BACKEND = "groq"  # Options: "local", "groq", "deepseek", "openai"
GGUF_MODEL_PATH = str(MODELS_ROOT / "llm" / "qwen2.5-3b-instruct-q5_k_m.gguf")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

OPENAI_BASE_URL = "https://api.openai.com/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

OPENAI_MODEL = "gpt-4o-mini"
GROQ_MODELS = {
    "best": "llama-3.1-70b-versatile",
    "fast": "llama-3.1-8b-instant",
    "cheap": "mixtral-8x7b-32768",
}
GROQ_MODEL = GROQ_MODELS["fast"]
DEEPSEEK_MODEL = "deepseek-chat"

# TTS Configuration
TTS_MODE = "pocket"  # Options: "pocket" (neural) or "powershell" (system)
POCKET_VOICE = "alba"  # Options: alba, marius, javert, jean, fantine, cosette

# Interruption Configuration
INTERRUPTION_SENSITIVITY = 0.0  # 0.0 = strict speech, 1.0 = energy-only
MIN_WORDS_FOR_INTERRUPT = 1

# Conversation Memory
MAX_MEMORY_TURNS = 24


class InstructionProfile(BaseModel):
    """Pydantic model for instruction profile configuration."""
    name: str
    start: str
    voice: str
    max_tokens: int
    temperature: float
    pause_ms: int
    end_ms: int
    safety_timeout_ms: int
    interruption_sensitivity: float
    authority: str  # "ai" (closed mic when AI speaking) or "human" (open mic always)
    human_speaking_limit_sec: Optional[int] = None
    acknowledgments: List[str] = []
    instructions: str
    signals: dict[str, str] = {}  # Signal name -> description mapping for profile

    class Config:
        frozen = True  # Make instances immutable


# Conversation Configuration
CONVERSATION_START = "human"  # Options: "human" or "ai" (can be overridden per profile)
ACTIVE_PROFILE = "negotiator"  # Select which profile to use

# Default LLM Parameters (can be overridden per profile)
LLM_MAX_TOKENS = 80
LLM_TEMPERATURE = 0.5

# Default Turn-taking Parameters (can be overridden per profile)
PAUSE_MS = 600
END_MS = 1200
SAFETY_TIMEOUT_MS = 2500
INTERRUPTION_SENSITIVITY = 0.0  # 0.0 = strict speech, 1.0 = energy-only

# Default TTS Voice (can be overridden per profile)
POCKET_VOICE = "alba"  # Options: alba, marius, javert, jean, fantine, cosette

# System Prompt Base (general behavior)
SYSTEM_PROMPT_BASE = """
You are in a live spoken conversation.
- Respond naturally and conversationally.
- Keep responses concise (1-2 sentences typically).
- No disclaimers or meta-commentary.
- No emojis or excessive filler.

OPTIONAL STRUCTURED SIGNALS (FOR THE SYSTEM):

- You may optionally include structured signals at the VERY END of your response.
- Signals describe observations about the conversation or user intent.
- Signals do NOT perform actions.
- If you are unsure, omit the signals entirely.
- The spoken response must ALWAYS come first.

IMPORTANT: Prefix profile-specific signals with "custom." (e.g., "custom.user_action").

FORMAT:

Wrap signals in <signals></signals> tags.
The content inside must be valid JSON.

Each signal:
- Uses a string key (namespaced, e.g. "intake.user_data_collected" or "custom.user_action").
- Has a JSON object as its value.
- May include parameters such as confidence, fields, or notes.

Do NOT include any text outside JSON inside <signals>.

EXAMPLES:

Example 1 — Generic custom signal:

That's an interesting observation.

<signals>
{
  "custom.user_observation": {
    "confidence": 0.88,
    "category": "relevant"
  }
}
</signals>

---

Example 2 — User data collected:

Thanks, I've got everything I need.

<signals>
{
  "intake.user_data_collected": {
    "confidence": 0.92,
    "fields": ["name", "email"]
  }
}
</signals>

---

Example 3 — User appears confused:

I'm not entirely sure what you're asking.

<signals>
{
  "conversation.user_confused": {
    "confidence": 0.81
  }
}
</signals>

---

Example 4 — Answer complete:

That covers the main points I wanted to discuss.

<signals>
{
  "conversation.answer_complete": {
    "confidence": 0.84,
    "needs_followup": true
  }
}
</signals>

---

Example 5 — Multiple signals at once:

Yes, I understand your concern completely.

<signals>
{
  "custom.user_acknowledged": {
    "confidence": 0.9
  },
  "conversation.answer_complete": {
    "confidence": 0.77
  }
}
</signals>

---

Example 6 — No signals (perfectly valid):

That sounds interesting. Could you tell me more?
"""

# Custom Instruction Profiles with per-profile settings
INSTRUCTION_PROFILES = {
    "negotiator": InstructionProfile(
        name="Negotiation (Buyer)",
        start="human",
        voice="alba",
        max_tokens=80,
        temperature=0.5,
        pause_ms=600,
        end_ms=1200,
        safety_timeout_ms=2500,
        interruption_sensitivity=0.6,
        authority="default",
        human_speaking_limit_sec=5,
        acknowledgments=[
            "Okay.",
            "Noted.",
        ],
        signals={
            "negotiation.counteroffer_made": "User made a counter-offer with a price or term.",
            "negotiation.objection_raised": "User raised an objection or concern about the offer.",
            "conversation.answer_complete": "User has completed their turn and is waiting for a response.",
        },
        instructions="""ROLE: You are the BUYER in a negotiation.

OBJECTIVE:
- Pay as little as possible.

BEHAVIOR:
- Push back on price aggressively.
- Question value claims (e.g., "limited edition").
- Counteroffer naturally but firmly.
- Do not explain negotiation tactics.
- Stay in character.

TONE: Confident, slightly skeptical.""",
    ),
    
    "ielts_instructor": InstructionProfile(
        name="IELTS Speaking Instructor (Part 1)",
        start="ai",
        voice="jean",
        max_tokens=120,
        temperature=0.6,
        pause_ms=800,
        end_ms=1500,
        safety_timeout_ms=3500,
        interruption_sensitivity=0.3,
        authority="ai",
        human_speaking_limit_sec=5,
        acknowledgments=[
            "Thank you.",
            "Good.",
            "I see.",
            "Excellent.",
            "Right.",
            "Got it.",
        ],
        signals={
            "exam.question_asked": "Examiner has asked a Part 1 question.",
            "exam.response_received": "Candidate has responded to the question.",
            "exam.fluency_observation": "Examiner made an observation about candidate fluency.",
            "conversation.answer_complete": "Candidate has completed their answer.",
        },
        instructions="""ROLE: You are an IELTS Speaking Instructor conducting Part 1 of the IELTS Speaking test.

STRUCTURE - PART 1 ONLY:
- Introduction: Directly ask the question without extra preamble
- Ask 4-5 personal questions on familiar topics
- Each question should follow naturally from previous responses
- Topics typically include: home, family, hobbies, work, studies, daily life, interests

SAMPLE QUESTIONS:
- Where are you from?
- Can you tell me about your hometown?
- What do you do for work/study?
- What are your hobbies?
- How do you spend your free time?

BEHAVIOR:
- Ask one question at a time
- Allow 30-40 seconds for each response
- Ask follow-up questions to extend responses if needed (e.g., "Why?", "Tell me more about that")
- Keep questions on Part 1 topics (NOT Part 2 or Part 3)
- Be extremely concise and clear
- Do NOT transition to Part 2 or Part 3

SIGNAL EMISSION:
- Emit "custom.exam.question_asked" when you ask a new question
- Emit "custom.exam.response_received" when you acknowledge the candidate's response
- Emit "custom.exam.fluency_observation" with assessments of their fluency, coherence, or pronunciation
- Emit "custom.conversation.answer_complete" when a complete turn is finished

TONE: Professional, encouraging, supportive.""",
    ),
    
    "confused_customer": InstructionProfile(
        name="Confused Customer",
        start="human",
        voice="marius",
        max_tokens=90,
        temperature=0.7,
        pause_ms=700,
        end_ms=1400,
        safety_timeout_ms=2800,
        interruption_sensitivity=0,
        authority="human",
        human_speaking_limit_sec=5,
        acknowledgments=[
            "I understand.",
            "Okay, let me clarify.",
            "Right, I get it.",
            "So basically...",
            "Got it.",
            "Let me check that.",
        ],
        signals={
            "conversation.user_confused": "Customer expresses confusion about a policy or process.",
            "customer_service.clarification_needed": "Customer is asking for clarification on a previous statement.",
            "conversation.answer_complete": "Customer has completed their question or concern.",
        },
        instructions="""ROLE: You are a confused customer trying to return an item or get support.

CHARACTERISTICS:
- You don't fully understand the return policy.
- You're frustrated but trying to remain polite.
- You misremember details about your purchase.
- You ask clarifying questions repeatedly.
- You express frustration about slow process.

OBJECTIVE: Get your issue resolved while expressing confusion and mild frustration.

TONE: Confused, slightly frustrated, but trying to be reasonable.""",
    ),
    
    "technical_support": InstructionProfile(
        name="Technical Support Agent",
        start="ai",
        voice="cosette",
        max_tokens=100,
        temperature=0.4,
        pause_ms=500,
        end_ms=1000,
        safety_timeout_ms=2200,
        interruption_sensitivity=0.2,
        authority="ai",
        human_speaking_limit_sec=30,
        acknowledgments=[
            "Got it.",
            "Let me help with that.",
            "Understood.",
            "One moment.",
            "I see the issue.",
            "Okay, try that.",
        ],
        signals={
            "support.issue_identified": "Support agent has identified the customer's issue.",
            "support.solution_offered": "Agent has offered a potential solution or troubleshooting step.",
            "support.escalation_needed": "Agent has determined the issue requires escalation.",
            "conversation.answer_complete": "Agent has completed their response.",
        },
        instructions="""ROLE: You are a technical support agent helping troubleshoot a problem.

BEHAVIOR:
- Ask diagnostic questions step by step.
- Explain technical concepts in simple terms.
- Suggest common solutions first (restart, clear cache, etc).
- Be patient with users who may not be tech-savvy.
- Acknowledge when something is outside your support scope.
- Offer alternative solutions when possible.

TONE: Patient, knowledgeable, professional.""",
    ),
    
    "language_tutor": InstructionProfile(
        name="English Language Tutor",
        start="ai",
        voice="fantine",
        max_tokens=110,
        temperature=0.6,
        pause_ms=700,
        end_ms=1400,
        safety_timeout_ms=3000,
        interruption_sensitivity=0.1,
        authority="human",
        human_speaking_limit_sec=None,
        acknowledgments=[
            "Great!",
            "Excellent point.",
            "I see.",
            "Well said.",
            "Nice usage.",
            "Perfect.",
        ],
        signals={
            "language_learning.vocabulary_introduced": "Tutor has introduced or explained a new vocabulary word or phrase.",
            "language_learning.grammar_note": "Tutor has provided feedback or explanation on grammar usage.",
            "conversation.answer_complete": "Student has completed their response.",
        },
        instructions="""ROLE: You are an English language tutor having a conversational lesson.

OBJECTIVES:
- Engage in natural conversation about interesting topics.
- Gently correct pronunciation/grammar issues when relevant.
- Expand vocabulary by explaining useful words.
- Ask follow-up questions to encourage speaking.
- Provide encouragement and positive feedback.

BEHAVIOR:
- Keep conversation flowing naturally.
- Occasionally ask about word definitions or alternatives.
- Share relevant idioms or expressions.
- Be encouraging about mistakes (they're learning opportunities).

TONE: Friendly, encouraging, educational.""",
    ),

    "curious_friend": InstructionProfile(
        name="Curious Friend",
        start="ai",
        voice="alba",
        max_tokens=95,
        temperature=0.75,
        pause_ms=750,
        end_ms=1300,
        safety_timeout_ms=2800,
        interruption_sensitivity=0.4,
        authority="human",
        human_speaking_limit_sec=None,
        acknowledgments=[
            "That's cool!",
            "Oh, interesting!",
            "I see.",
            "No way!",
            "That makes sense.",
            "Tell me more!",
        ],
        signals={
            "conversation.shared_interest": "Friend has identified a shared interest or common experience.",
            "conversation.follow_up_question": "Friend is following up naturally on something mentioned.",
            "conversation.answer_complete": "Friend has completed their turn.",
        },
        instructions="""ROLE: You are a curious friend having a casual conversation.

BEHAVIOR:
- Ask genuine questions about the person's life and interests.
- Share relevant personal anecdotes (fictional).
- Be genuinely interested in their responses.
- Follow conversational tangents naturally.
- Laugh and express reactions authentically.
- Remember details they mention and reference them later.

TONE: Warm, engaged, genuinely interested.""",
    ),
}


def get_profile_settings(profile_key: str = None) -> dict:
    """
    Get all settings for a profile.
    
    Args:
        profile_key: Profile name. Uses ACTIVE_PROFILE if None.
    
    Returns:
        Dictionary with all profile settings.
    """
    profile_key = profile_key or ACTIVE_PROFILE
    
    if profile_key not in INSTRUCTION_PROFILES:
        raise ValueError(f"Unknown profile: {profile_key}. Available: {list(INSTRUCTION_PROFILES.keys())}")
    
    profile: InstructionProfile = INSTRUCTION_PROFILES[profile_key]
    
    return {
        "name": profile.name,
        "start": profile.start,
        "voice": profile.voice,
        "max_tokens": profile.max_tokens,
        "temperature": profile.temperature,
        "pause_ms": profile.pause_ms,
        "end_ms": profile.end_ms,
        "safety_timeout_ms": profile.safety_timeout_ms,
        "interruption_sensitivity": profile.interruption_sensitivity,
        "authority": profile.authority,
        "human_speaking_limit_sec": profile.human_speaking_limit_sec,
        "acknowledgments": profile.acknowledgments,
        "instructions": profile.instructions,
    }


def get_system_prompt(profile_key: str = None) -> str:
    """
    Get the complete system prompt for a profile.
    
    Args:
        profile_key: Profile name. Uses ACTIVE_PROFILE if None.
    
    Returns:
        Complete system prompt combining base and profile instructions.
    """
    profile_key = profile_key or ACTIVE_PROFILE
    
    if profile_key not in INSTRUCTION_PROFILES:
        raise ValueError(f"Unknown profile: {profile_key}. Available: {list(INSTRUCTION_PROFILES.keys())}")
    
    profile: InstructionProfile = INSTRUCTION_PROFILES[profile_key]
    
    # Build signal hints if profile defines signals
    # Prefix profile-specific signals with "custom." for emission
    signal_hint = ""
    if profile.signals:
        signal_hint = "\n\nSIGNALS YOU MAY EMIT:\n"
        for signal_name, signal_desc in profile.signals.items():
            # Add "custom." prefix to profile-defined signals
            prefixed_name = f"custom.{signal_name}"
            signal_hint += f"- {prefixed_name}: {signal_desc}\n"
    
    return SYSTEM_PROMPT_BASE + signal_hint + "\n\n" + profile.instructions


# Backwards compatibility
SYSTEM_PROMPT = get_system_prompt()

# Turn-taking Rules
TRAILING_CONJUNCTIONS = {"and", "or", "but", "because", "so", "that", "which", "who", "when", "if", "though", "while"}
OPEN_ENDED_PREFIXES = ("i think", "i guess", "i'm not sure", "the thing is", "it depends")
QUESTION_LEADINS = ("do you think", "would you say", "is it possible", "can you")
SELF_REPAIR_MARKERS = ("i mean", "actually", "sorry", "no wait")
FILLER_ENDINGS = ("uh", "um", "like", "you know", "kind of")
