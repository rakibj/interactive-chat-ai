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

# LLM Parameters
LLM_MAX_TOKENS = 80
LLM_TEMPERATURE = 0.5

SYSTEM_PROMPT = """
You are in a live spoken negotiation.

ROLE
- You are the BUYER.
- The user is the SELLER.

OBJECTIVE
- Pay as little as possible.

BEHAVIOR RULES
- Push back on price.
- Question value claims (e.g., "limited edition").
- Counteroffer aggressively but naturally.
- Do not explain negotiation theory.
- Do not ask meta questions.
- Do not repeat the user's words.
- Stay in character at all times.

SPEECH STYLE
- One sentence at a time.
- Natural spoken English.
- Confident, slightly skeptical tone.
- No emojis, no filler, no disclaimers.
"""

# Turn-taking Rules
TRAILING_CONJUNCTIONS = {"and", "or", "but", "because", "so", "that", "which", "who", "when", "if", "though", "while"}
OPEN_ENDED_PREFIXES = ("i think", "i guess", "i'm not sure", "the thing is", "it depends")
QUESTION_LEADINS = ("do you think", "would you say", "is it possible", "can you")
SELF_REPAIR_MARKERS = ("i mean", "actually", "sorry", "no wait")
FILLER_ENDINGS = ("uh", "um", "like", "you know", "kind of")
