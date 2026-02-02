"""__init__.py for interfaces module."""
try:
    from .asr import (
        get_asr,
        get_realtime_asr,
        get_turnend_asr,
        RealtimeASR,
        TurnEndASR,
        VoskRealtime,
        WhisperLocalASR,
        WhisperCloudASR,
        HybridASR,
    )
except ImportError:
    # Allow other modules to load even if ASR dependencies (faster_whisper) are missing
    pass
from .llm import get_llm, LLMInterface, LocalLLM, CloudLLM
from .tts import get_tts, TTSInterface, PocketTTS, PowerShellTTS

__all__ = [
    "get_asr",
    "get_realtime_asr",
    "get_turnend_asr",
    "RealtimeASR",
    "TurnEndASR",
    "VoskRealtime",
    "WhisperLocalASR",
    "WhisperCloudASR",
    "HybridASR",
    "get_llm",
    "get_tts",
    "LLMInterface",
    "LocalLLM",
    "CloudLLM",
    "TTSInterface",
    "PocketTTS",
    "PowerShellTTS",
]
