"""__init__.py for interfaces module."""
_asr_available = True
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
    _asr_available = False
    # Define stub functions/classes that raise helpful errors
    def get_asr(*args, **kwargs):
        raise RuntimeError("ASR not available - faster_whisper dependency missing")
    def get_realtime_asr(*args, **kwargs):
        raise RuntimeError("ASR not available - faster_whisper dependency missing")
    def get_turnend_asr(*args, **kwargs):
        raise RuntimeError("ASR not available - faster_whisper dependency missing")
    class RealtimeASR:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("ASR not available - faster_whisper dependency missing")
    class TurnEndASR:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("ASR not available - faster_whisper dependency missing")
    class VoskRealtime:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("ASR not available - faster_whisper dependency missing")
    class WhisperLocalASR:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("ASR not available - faster_whisper dependency missing")
    class WhisperCloudASR:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("ASR not available - faster_whisper dependency missing")
    class HybridASR:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("ASR not available - faster_whisper dependency missing")

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
