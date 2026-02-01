"""Abstract ASR interface and implementations.

Split into two stages:
1. RealtimeASR: Streaming partial transcriptions (uses Vosk)
2. TurnEndASR: Final transcription at turn end (uses WhisperLocalASR or WhisperCloudASR)

Main.py uses both via HybridASR which combines them.
"""
from abc import ABC, abstractmethod
import json
import io
import numpy as np
from collections import deque
from faster_whisper import WhisperModel
from config import (
    WHISPER_MODEL_PATH,
    VOSK_MODEL_PATH,
    SAMPLE_RATE,
    VOSK_MIN_SAMPLES,
    OPENAI_API_KEY,
    TURN_END_ASR_MODE,
    WHISPER_CLOUD_MODEL,
)
from utils.audio import float32_to_int16


class RealtimeASR(ABC):
    """Abstract base for real-time streaming ASR."""
    
    @abstractmethod
    def get_partial(self) -> str:
        """Get partial/streaming transcription for closed-caption-like updates."""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset ASR state for new turn."""
        pass


class TurnEndASR(ABC):
    """Abstract base for turn-end final transcription."""
    
    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to final text at turn end."""
        pass


class VoskRealtime(RealtimeASR):
    """Vosk-based real-time ASR for streaming partials.
    
    Provides low-latency partial results for closed-caption-like display
    and for lexical bias scoring in turn-taking.
    """
    
    def __init__(self):
        from vosk import Model, KaldiRecognizer
        
        print("Loading Vosk (for real-time streaming)...")
        vosk_model = Model(VOSK_MODEL_PATH)
        self.recognizer = KaldiRecognizer(vosk_model, SAMPLE_RATE)
        self.recognizer.SetWords(True)
        self.current_partial = ""
    
    def get_partial(self) -> str:
        """Get current partial transcription from Vosk."""
        res = json.loads(self.recognizer.PartialResult())
        self.current_partial = res.get("partial", "").strip()
        return self.current_partial
    
    def accept_waveform(self, chunk_bytes: bytes) -> bool:
        """Feed audio chunk to Vosk recognizer.
        
        Returns True if a final result is available.
        """
        return self.recognizer.AcceptWaveform(chunk_bytes)
    
    def get_result(self) -> str:
        """Get current result (partial or final) from Vosk."""
        res = json.loads(self.recognizer.Result())
        return res.get("text", "").strip()
    
    def reset(self) -> None:
        """Reset recognizer state for new turn."""
        self.recognizer.Reset()
        self.current_partial = ""


class WhisperLocalASR(TurnEndASR):
    """Whisper-based ASR for high-accuracy final transcription.
    
    Called at turn end for accurate, complete transcription.
    Uses local model files for CPU inference.
    """
    
    def __init__(self):
        print("Loading Whisper (local model for final transcription)...")
        self.model = WhisperModel(
            WHISPER_MODEL_PATH,
            device="cpu",
            compute_type="int8",
            local_files_only=True,
            cpu_threads=8,
        )
    
    def transcribe(self, audio: np.ndarray) -> str:
        """Full transcription of audio buffer at turn end."""
        segments, _ = self.model.transcribe(
            audio,
            language="en",
            beam_size=5,
            temperature=0.0,
            condition_on_previous_text=False,
        )
        return " ".join(seg.text for seg in segments).strip()


class WhisperCloudASR(TurnEndASR):
    """OpenAI Whisper Cloud API for high-accuracy final transcription.
    
    Called at turn end for accurate, complete transcription.
    Uses OpenAI's cloud API (gpt-4o-transcribe or gpt-4o-mini-transcribe).
    Requires OPENAI_API_KEY environment variable.
    
    Advantages over local Whisper:
    - Higher accuracy
    - Faster transcription
    - Automatic audio format handling
    - Support for multiple languages
    
    Note: Requires API calls and will incur costs.
    """
    
    def __init__(self):
        from openai import OpenAI
        
        if not OPENAI_API_KEY:
            raise ValueError(
                "WhisperCloudASR requires OPENAI_API_KEY environment variable. "
                "Set it or use WhisperLocalASR instead."
            )
        
        print(f"Using OpenAI Whisper Cloud ({WHISPER_CLOUD_MODEL}) for final transcription...")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = WHISPER_CLOUD_MODEL
    
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio buffer using OpenAI Whisper API.
        
        Converts numpy audio to WAV format and sends to OpenAI API.
        """
        try:
            # Convert numpy float32 to WAV bytes
            wav_bytes = self._numpy_to_wav(audio)
            
            # Send to OpenAI API
            transcript = self.client.audio.transcriptions.create(
                model=self.model,
                file=("audio.wav", wav_bytes, "audio/wav"),
                response_format="text",
                language="en",
            )
            
            return transcript.strip()
        except Exception as e:
            print(f"Error transcribing with cloud API: {e}")
            return ""
    
    @staticmethod
    def _numpy_to_wav(audio: np.ndarray) -> bytes:
        """Convert numpy float32 audio to WAV bytes."""
        import wave
        
        # Ensure float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        # Convert to 16-bit PCM
        audio_int16 = float32_to_int16(audio)
        
        # Write to WAV bytes
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio_int16.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer.read()


class HybridASR:
    """Combines real-time ASR (Vosk) with turn-end ASR (Whisper).
    
    - RealtimeASR: Vosk for streaming partials (closed-caption updates)
    - TurnEndASR: Whisper for final high-accuracy transcription
    
    Maintains compatibility with existing main.py API:
    - get_partial(): from Vosk
    - transcribe(): from Whisper
    """
    
    def __init__(self):
        self.realtime = VoskRealtime()
        self.turnend = WhisperLocalASR()
    
    def get_partial(self) -> str:
        """Get real-time partial from Vosk."""
        return self.realtime.get_partial()
    
    def accept_waveform(self, chunk_bytes: bytes) -> bool:
        """Feed audio to Vosk for real-time updates."""
        return self.realtime.accept_waveform(chunk_bytes)
    
    def transcribe(self, audio: np.ndarray) -> str:
        """Get final transcription from Whisper."""
        return self.turnend.transcribe(audio)
    
    def reset(self) -> None:
        """Reset both ASR components."""
        self.realtime.reset()


def get_asr() -> HybridASR:
    """Factory function to get hybrid ASR (Vosk + Whisper).
    
    Returns:
        HybridASR: Combines VoskRealtime for streaming and WhisperLocalASR for final transcription.
    """
    return HybridASR()


def get_realtime_asr() -> RealtimeASR:
    """Get just the real-time ASR component."""
    return VoskRealtime()


def get_turnend_asr() -> TurnEndASR:
    """Get just the turn-end ASR component."""
    return WhisperLocalASR()
