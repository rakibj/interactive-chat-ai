"""Abstract ASR interface and implementations (Vosk/Whisper)."""
from abc import ABC, abstractmethod
import json
import numpy as np
from collections import deque
from faster_whisper import WhisperModel
from config import (
    TRANSCRIPTION_MODE,
    WHISPER_MODEL_PATH,
    VOSK_MODEL_PATH,
    SAMPLE_RATE,
    VOSK_MIN_SAMPLES,
)
from utils.audio import float32_to_int16


class ASRInterface(ABC):
    """Abstract base for ASR implementations."""
    
    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text."""
        pass
    
    @abstractmethod
    def get_partial(self) -> str:
        """Get partial/streaming transcription."""
        pass


class WhisperASR(ASRInterface):
    """Whisper-based ASR with sliding window for streaming."""
    
    def __init__(self):
        print("Loading Whisper (for final transcription)...")
        self.model = WhisperModel(
            WHISPER_MODEL_PATH,
            device="cpu",
            compute_type="int8",
            local_files_only=True,
            cpu_threads=8,
        )
        self.audio_buffer = deque()
        self.current_partial = ""
    
    def transcribe(self, audio: np.ndarray) -> str:
        """Full transcription of audio."""
        segments, _ = self.model.transcribe(
            audio,
            language="en",
            beam_size=5,
            temperature=0.0,
            condition_on_previous_text=False,
        )
        return " ".join(seg.text for seg in segments).strip()
    
    def get_partial(self) -> str:
        """Return current partial transcription."""
        return self.current_partial


class VoskASR(ASRInterface):
    """Vosk-based ASR with low-latency streaming."""
    
    def __init__(self):
        from vosk import Model, KaldiRecognizer
        
        print("Loading Vosk...")
        vosk_model = Model(VOSK_MODEL_PATH)
        self.recognizer = KaldiRecognizer(vosk_model, SAMPLE_RATE)
        self.recognizer.SetWords(True)
        self.current_partial = ""
        self.last_final_text = ""
    
    def transcribe(self, audio: np.ndarray) -> str:
        """Process full turn audio for final transcription."""
        pcm16 = float32_to_int16(audio)
        
        # Process full audio, accumulating results
        final_text = ""
        
        # Feed audio in chunks (Vosk processes internally)
        chunk_size = int(SAMPLE_RATE * 0.2)  # 200ms chunks
        for i in range(0, len(pcm16), chunk_size):
            chunk = pcm16[i:i+chunk_size]
            
            if self.recognizer.AcceptWaveform(chunk.tobytes()):
                res = json.loads(self.recognizer.Result())
                text = res.get("text", "").strip()
                if text:
                    final_text += text + " "
        
        # Final flush to get any remaining partial as final
        self.recognizer.PartialResult()  # Trigger internal flush
        res = json.loads(self.recognizer.Result())
        text = res.get("text", "").strip()
        if text:
            final_text += text
        
        # Reset recognizer for next turn
        self.recognizer.Reset()
        
        return final_text.strip()
    
    def get_partial(self) -> str:
        """Get partial transcription."""
        res = json.loads(self.recognizer.PartialResult())
        self.current_partial = res.get("partial", "").strip()
        return self.current_partial
    
    def reset(self) -> None:
        """Reset recognizer state."""
        self.recognizer.Reset()
        self.current_partial = ""


def get_asr() -> ASRInterface:
    """Factory function to get appropriate ASR implementation."""
    if TRANSCRIPTION_MODE == "vosk":
        return VoskASR()
    elif TRANSCRIPTION_MODE == "whisper":
        return WhisperASR()
    else:
        raise ValueError(f"Unknown ASR mode: {TRANSCRIPTION_MODE}")
