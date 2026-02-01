"""Audio manager: VAD, energy detection, and stream management."""
import numpy as np
import sounddevice as sd
import torch
from collections import deque
import time
import threading
from config import (
    SAMPLE_RATE,
    VAD_MIN_SAMPLES,
    ENERGY_FLOOR,
)


class AudioManager:
    """Manages audio stream, VAD, and energy detection."""
    
    def __init__(self):
        self.sample_rate = SAMPLE_RATE
        self.audio_buffer = []
        self.vad_model = None
        self.stream = None
        self.lock = threading.Lock()
        self._load_vad()
        self._start_stream()
    
    def _load_vad(self) -> None:
        """Load Silero VAD model."""
        print("Loading Silero VAD...")
        self.vad_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
        )
    
    def _audio_callback(self, indata, frames, time_obj, status):
        """Audio stream callback."""
        if status:
            print(f"Audio status: {status}")
        self.audio_buffer.append(indata.copy())
    
    def _start_stream(self) -> None:
        """Start audio input stream."""
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=self._audio_callback,
        )
        self.stream.start()
        print(f"🎙️ Audio stream started at {self.sample_rate}Hz")
    
    def get_audio_chunk(self) -> np.ndarray:
        """Get next audio chunk from buffer."""
        with self.lock:
            if self.audio_buffer:
                return self.audio_buffer.pop(0).astype(np.float32).flatten()
        return np.array([], dtype=np.float32)
    
    def detect_speech(self, audio_chunk: np.ndarray) -> tuple:
        """
        Detect speech using VAD.
        Returns: (speech_started, rms_energy)
        """
        if len(audio_chunk) < VAD_MIN_SAMPLES:
            return False, 0.0
        
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        
        with torch.no_grad():
            vad_confidence = self.vad_model(
                torch.from_numpy(audio_chunk).unsqueeze(0),
                self.sample_rate,
            ).item()
        
        speech_started = vad_confidence > 0.5
        return speech_started, rms
    
    def is_sustained_speech(self, energy_history: deque) -> bool:
        """Check if sustained speech based on recent energy."""
        if len(energy_history) < 3:
            return False
        return sum(e > ENERGY_FLOOR for e in energy_history) >= 3
    
    def stop(self) -> None:
        """Stop audio stream."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
        print("🎙️ Audio stream stopped")
