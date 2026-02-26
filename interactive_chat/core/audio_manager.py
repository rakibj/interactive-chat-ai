"""Audio manager: VAD, energy detection, and stream management."""
import numpy as np
import sounddevice as sd
import torch
from collections import deque
import time
import threading
from interactive_chat.config import (
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
        """Load Silero VAD model with timeout."""
        import threading
        
        vad_loaded = threading.Event()
        vad_error = {"error": None}
        
        def load_vad_with_timeout():
            try:
                print("Loading Silero VAD...")
                self.vad_model, _ = torch.hub.load(
                    repo_or_dir="snakers4/silero-vad",
                    model="silero_vad",
                    force_reload=False,
                )
                print("✅ Silero VAD loaded")
                vad_loaded.set()
            except Exception as e:
                vad_error["error"] = str(e)
                print(f"⚠️  VAD loading failed: {e}")
                vad_loaded.set()
        
        # Start VAD loading in a thread with timeout
        vad_thread = threading.Thread(target=load_vad_with_timeout, daemon=True)
        vad_thread.start()
        
        # Wait for VAD loading with 30-second timeout
        if not vad_loaded.wait(timeout=30.0):
            print(f"⚠️  VAD loading timed out (30s)")
            vad_error["error"] = "Timeout"
        
        if vad_error["error"]:
            self.vad_model = None
            print(f"⚠️  VAD will not be available - using energy-only detection")
    
    def _audio_callback(self, indata, frames, time_obj, status):
        """Audio stream callback."""
        if status:
            print(f"Audio status: {status}")
        self.audio_buffer.append(indata.copy())
    
    def _start_stream(self) -> None:
        """Start audio input stream with timeout."""
        import threading
        init_complete = threading.Event()
        init_error = {"error": None}
        
        def start_stream_with_timeout():
            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    callback=self._audio_callback,
                    blocksize=512,
                )
                self.stream.start()
                print(f"🎙️ Audio stream started at {self.sample_rate}Hz")
                init_complete.set()
            except Exception as e:
                init_error["error"] = str(e)
                print(f"⚠️  Audio stream failed to initialize: {e}")
                init_complete.set()
        
        # Start stream initialization in a thread with timeout
        stream_thread = threading.Thread(target=start_stream_with_timeout, daemon=True)
        stream_thread.start()
        
        # Wait for initialization with 5-second timeout
        if not init_complete.wait(timeout=5.0):
            print(f"⚠️  Audio stream initialization timed out (5s)")
            init_error["error"] = "Timeout"
        
        if init_error["error"]:
            self.stream = None  # Mark as unavailable
            print(f"⚠️  Audio input will not be available")
        
        return init_error["error"] is None
    
    def get_audio_chunk(self) -> np.ndarray:
        """Get next audio chunk from buffer."""
        if self.stream is None:
            # Audio not available, return empty chunk
            return np.array([], dtype=np.float32)
        
        with self.lock:
            if self.audio_buffer:
                return self.audio_buffer.pop(0).astype(np.float32).flatten()
        return np.array([], dtype=np.float32)
    
    def detect_speech(self, audio_chunk: np.ndarray) -> tuple:
        """
        Detect speech using VAD or energy-only fallback.
        Returns: (speech_started, rms_energy)
        """
        if len(audio_chunk) < VAD_MIN_SAMPLES:
            return False, 0.0
        
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        
        # Use VAD if available, otherwise use energy-only detection
        if self.vad_model is not None:
            try:
                with torch.no_grad():
                    vad_confidence = self.vad_model(
                        torch.from_numpy(audio_chunk).unsqueeze(0),
                        self.sample_rate,
                    ).item()
                speech_started = vad_confidence > 0.5
            except Exception as e:
                # Fallback to energy-only if VAD fails
                print(f"⚠️  VAD inference failed: {e}")
                speech_started = rms > ENERGY_FLOOR
        else:
            # Energy-only detection when VAD not available
            speech_started = rms > ENERGY_FLOOR
        
        return speech_started, rms
    
    def is_sustained_speech(self, energy_history: deque) -> bool:
        """Check if sustained speech based on recent energy."""
        if len(energy_history) < 3:
            return False
        return sum(e > ENERGY_FLOOR for e in energy_history) >= 3
    
    def stop(self) -> None:
        """Stop audio stream."""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                print("🎙️ Audio stream stopped")
            except Exception as e:
                print(f"⚠️  Error stopping audio stream: {e}")
        else:
            print("ℹ️  Audio stream was not active")
