"""Abstract TTS interface and implementations (Pocket/PowerShell)."""
from abc import ABC, abstractmethod
import subprocess
import numpy as np
import sounddevice as sd
from config import TTS_MODE, POCKET_VOICE

try:
    from pocket_tts import TTSModel
    POCKET_AVAILABLE = True
except ImportError:
    POCKET_AVAILABLE = False


import threading

class TTSInterface(ABC):
    """Abstract base for TTS implementations."""
    
    @abstractmethod
    def speak(self, text: str, interrupt_event: threading.Event = None) -> None:
        """Speak text aloud. Optional interrupt_event to stop mid-speech."""
        pass


class PocketTTS(TTSInterface):
    """Pocket TTS neural voice implementation."""
    
    def __init__(self, voice_name: str = None):
        if not POCKET_AVAILABLE:
            raise ImportError("pocket-tts not installed. Install with: uv add pocket-tts")
        
        target_voice = voice_name or POCKET_VOICE
        print(f"⏳ Loading Pocket TTS (voice: {target_voice})...")
        self.model = TTSModel.load_model()
        self.voice_state = self.model.get_state_for_audio_prompt(target_voice)
        self.sample_rate = self.model.sample_rate
        print("✅ Pocket TTS loaded!")
    
    def speak(self, text: str, interrupt_event: threading.Event = None) -> None:
        """Generate and play audio using Pocket TTS."""
        if not text.strip():
            return
        
        try:
            # Check before generating (optimization)
            if interrupt_event and interrupt_event.is_set():
                return

            audio = self.model.generate_audio(self.voice_state, text)
            audio_np = audio.numpy() if hasattr(audio, "numpy") else np.array(audio)
            
            # Play in 100ms chunks
            chunk_size = int(self.sample_rate * 0.1)
            stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
            )
            stream.start()
            
            for i in range(0, len(audio_np), chunk_size):
                # Check interruption status inside the loop
                if interrupt_event and interrupt_event.is_set():
                    stream.stop()
                    stream.close()
                    return

                chunk = audio_np[i : i + chunk_size]
                stream.write(chunk)
            
            stream.stop()
            stream.close()
        
        except Exception as e:
            print(f"🔊 TTS error: {e}")


class PowerShellTTS(TTSInterface):
    """Windows PowerShell system TTS (fallback)."""
    
    def speak(self, text: str, interrupt_event: threading.Event = None) -> None:
        """Use Windows PowerShell for text-to-speech."""
        if not text.strip():
            return
        
        safe_text = text.replace('"', '""').replace("\n", " ").replace("\r", "")
        cmd = f'Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak("{safe_text}")'
        
        try:
            subprocess.run(
                ["powershell", "-Command", cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except Exception as e:
            print(f"🔊 Speech error: {e}")


def get_tts(voice_name: str = None) -> TTSInterface:
    """Factory function to get appropriate TTS implementation."""
    if TTS_MODE == "pocket":
        return PocketTTS(voice_name=voice_name)
    elif TTS_MODE == "powershell":
        return PowerShellTTS()
    else:
        raise ValueError(f"Unknown TTS mode: {TTS_MODE}")
