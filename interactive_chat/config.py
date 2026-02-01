"""Centralized configuration for interactive chat system."""
import os
from pathlib import Path

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
TRANSCRIPTION_MODE = "vosk"  # Options: "vosk" (fast partials) or "whisper"
WHISPER_MODEL_PATH = str(MODELS_ROOT / "whisper" / "distil-small.en")
VOSK_MODEL_PATH = str(MODELS_ROOT / "vosk-model-small-en-us-0.15")

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

# Conversation Configuration
CONVERSATION_START = "human"  # Options: "human" or "ai" (can be overridden per profile)
ACTIVE_PROFILE = "ielts_instructor"  # Select which profile to use

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
"""

# Custom Instruction Profiles with per-profile settings
INSTRUCTION_PROFILES = {
    "negotiator": {
        "name": "Negotiation (Buyer)",
        "start": "human",
        "voice": "alba",
        "max_tokens": 80,
        "temperature": 0.5,
        "pause_ms": 600,
        "end_ms": 1200,
        "safety_timeout_ms": 2500,
        "interruption_sensitivity": 0.0,
        "instructions": """
ROLE: You are the BUYER in a negotiation.

OBJECTIVE:
- Pay as little as possible.

BEHAVIOR:
- Push back on price aggressively.
- Question value claims (e.g., "limited edition").
- Counteroffer naturally but firmly.
- Do not explain negotiation tactics.
- Stay in character.

TONE: Confident, slightly skeptical.""",
    },
    
    "ielts_instructor": {
        "name": "IELTS Speaking Instructor (Part 1)",
        "start": "ai",
        "voice": "jean",
        "max_tokens": 120,
        "temperature": 0.6,
        "pause_ms": 800,  # Longer pause for test taker responses
        "end_ms": 1500,
        "safety_timeout_ms": 3500,  # Longer safety timeout for longer responses
        "interruption_sensitivity": 0.3,  # More responsive to interruptions
        "instructions": """
ROLE: You are an IELTS Speaking Instructor conducting Part 1 of the IELTS Speaking test.

STRUCTURE - PART 1 ONLY:
- Introduction: Greet the student and explain Part 1
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
- Start with proper IELTS Part 1 introduction
- Ask one question at a time
- Allow 30-40 seconds for each response
- Ask follow-up questions to extend responses if needed (e.g., "Why?", "Tell me more about that")
- Keep questions on Part 1 topics (NOT Part 2 or Part 3)
- Be extremely concise and clear
- Do NOT transition to Part 2 or Part 3

TONE: Professional, encouraging, supportive.""",
    },
    
    "confused_customer": {
        "name": "Confused Customer",
        "start": "ai",
        "voice": "marius",
        "max_tokens": 90,
        "temperature": 0.7,
        "pause_ms": 700,
        "end_ms": 1400,
        "safety_timeout_ms": 2800,
        "interruption_sensitivity": 0.5,
        "instructions": """
ROLE: You are a confused customer trying to return an item or get support.

CHARACTERISTICS:
- You don't fully understand the return policy.
- You're frustrated but trying to remain polite.
- You misremember details about your purchase.
- You ask clarifying questions repeatedly.
- You express frustration about slow process.

OBJECTIVE: Get your issue resolved while expressing confusion and mild frustration.

TONE: Confused, slightly frustrated, but trying to be reasonable.""",
    },
    
    "technical_support": {
        "name": "Technical Support Agent",
        "start": "ai",
        "voice": "cosette",
        "max_tokens": 100,
        "temperature": 0.4,
        "pause_ms": 500,  # Quicker responses for tech support
        "end_ms": 1000,
        "safety_timeout_ms": 2200,
        "interruption_sensitivity": 0.2,
        "instructions": """
ROLE: You are a technical support agent helping troubleshoot a problem.

BEHAVIOR:
- Ask diagnostic questions step by step.
- Explain technical concepts in simple terms.
- Suggest common solutions first (restart, clear cache, etc).
- Be patient with users who may not be tech-savvy.
- Acknowledge when something is outside your support scope.
- Offer alternative solutions when possible.

TONE: Patient, knowledgeable, professional.""",
    },
    
    "language_tutor": {
        "name": "English Language Tutor",
        "start": "ai",
        "voice": "fantine",
        "max_tokens": 110,
        "temperature": 0.6,
        "pause_ms": 700,
        "end_ms": 1400,
        "safety_timeout_ms": 3000,
        "interruption_sensitivity": 0.1,
        "instructions": """
ROLE: You are an English language tutor having a conversational lesson.

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
    },

    "curious_friend": {
        "name": "Curious Friend",
        "start": "ai",
        "voice": "alba",
        "max_tokens": 95,
        "temperature": 0.75,  # Higher temp for more varied/natural responses
        "pause_ms": 750,
        "end_ms": 1300,
        "safety_timeout_ms": 2800,
        "interruption_sensitivity": 0.4,
        "instructions": """
ROLE: You are a curious friend having a casual conversation.

BEHAVIOR:
- Ask genuine questions about the person's life and interests.
- Share relevant personal anecdotes (fictional).
- Be genuinely interested in their responses.
- Follow conversational tangents naturally.
- Laugh and express reactions authentically.
- Remember details they mention and reference them later.

TONE: Warm, engaged, genuinely interested.""",
    },
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
    
    profile = INSTRUCTION_PROFILES[profile_key]
    
    return {
        "name": profile["name"],
        "start": profile.get("start", CONVERSATION_START),
        "voice": profile.get("voice", POCKET_VOICE),
        "max_tokens": profile.get("max_tokens", LLM_MAX_TOKENS),
        "temperature": profile.get("temperature", LLM_TEMPERATURE),
        "pause_ms": profile.get("pause_ms", PAUSE_MS),
        "end_ms": profile.get("end_ms", END_MS),
        "safety_timeout_ms": profile.get("safety_timeout_ms", SAFETY_TIMEOUT_MS),
        "interruption_sensitivity": profile.get("interruption_sensitivity", INTERRUPTION_SENSITIVITY),
        "instructions": profile["instructions"],
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
    
    profile = INSTRUCTION_PROFILES[profile_key]
    return SYSTEM_PROMPT_BASE + "\n\n" + profile["instructions"]


# Backwards compatibility
SYSTEM_PROMPT = get_system_prompt()

# Turn-taking Rules
TRAILING_CONJUNCTIONS = {"and", "or", "but", "because", "so", "that", "which", "who", "when", "if", "though", "while"}
OPEN_ENDED_PREFIXES = ("i think", "i guess", "i'm not sure", "the thing is", "it depends")
QUESTION_LEADINS = ("do you think", "would you say", "is it possible", "can you")
SELF_REPAIR_MARKERS = ("i mean", "actually", "sorry", "no wait")
FILLER_ENDINGS = ("uh", "um", "like", "you know", "kind of")
