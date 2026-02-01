"""Minimal orchestration loop for interactive chat system."""
import os
import sys

# Load environment variables FIRST, before any other imports
from dotenv import load_dotenv
load_dotenv()

import threading
import time
import queue
import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import List

# Bootstrap torch threads
os.environ["OMP_NUM_THREADS"] = "8"
os.environ["OPENBLAS_NUM_THREADS"] = "8"
os.environ["MKL_NUM_THREADS"] = "8"
os.environ["VECLIB_MAXIMUM_THREADS"] = "8"
os.environ["NUMEXPR_NUM_THREADS"] = "8"

import torch
torch.set_num_threads(8)
torch.set_num_interop_threads(1)
torch.set_grad_enabled(False)

# Add project to path
sys.path.insert(0, str(os.path.dirname(__file__)))

from config import (
    SAFETY_TIMEOUT_MS,
    CONFIDENCE_THRESHOLD,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    SYSTEM_PROMPT,
)
from core import AudioManager, TurnTaker, InterruptionManager, ConversationMemory
from interfaces import get_asr, get_llm, get_tts


@dataclass
class TurnTiming:
    """Performance timing metrics for a conversation turn."""
    
    turn_id: int = 0
    speech_end_time: float = 0.0
    whisper_transcribe_ms: float = 0.0
    whisper_rtf: float = 0.0
    llm_generate_ms: float = 0.0
    llm_tokens_per_sec: float = 0.0
    total_latency_ms: float = 0.0
    total_audio_duration_sec: float = 0.0
    
    def print_report(self) -> None:
        """Print turn timing report."""
        print(f"\n{'='*60}")
        print(f"📊 TURN #{self.turn_id} TIMING AUDIT")
        print(f"{'='*60}")
        print(f"🎙️  User audio duration:     {self.total_audio_duration_sec:.2f}s")
        print(f"⏱️  Speech end → Response:   {self.total_latency_ms:.0f}ms total")
        print(f"{'─'*40}")
        print(f"1. Whisper transcription:    {self.whisper_transcribe_ms:.1f}ms (RTF: {self.whisper_rtf:.2f}x)")
        print(f"2. LLM generation:           {self.llm_generate_ms:.1f}ms ({self.llm_tokens_per_sec:.1f} tok/s)")
        print(f"{'='*60}\n")


class ConversationEngine:
    """Main orchestration engine."""
    
    def __init__(self):
        self.audio_manager = AudioManager()
        self.turn_taker = TurnTaker()
        self.interruption_manager = InterruptionManager()
        self.conversation_memory = ConversationMemory()
        
        self.asr = get_asr()
        self.llm = get_llm()
        self.tts = get_tts()
        
        # State
        self.turn_audio = deque()
        self.response_queue = queue.Queue()
        self.human_interrupt_event = threading.Event()
        self.ai_speaking_event = threading.Event()
        self.human_speaking_now = threading.Event()
        
        self.turn_counter = 0
        self.timing_history: List[TurnTiming] = []
        self.current_partial_text = ""  # For ASR streaming
        self.asr_lock = threading.Lock()
        self.shutdown_event = threading.Event()  # Signal for graceful shutdown
        
        # Start threads
        self._start_tts_worker()
        self._start_asr_worker()
    
    def _start_tts_worker(self) -> None:
        """Start TTS queue processor thread."""
        threading.Thread(target=self._tts_worker, daemon=True).start()
    
    def _start_asr_worker(self) -> None:
        """Start ASR partial text updater thread."""
        threading.Thread(target=self._asr_worker, daemon=True).start()
    
    def _asr_worker(self) -> None:
        """Periodically update partial text from ASR for confidence scoring."""
        while not self.shutdown_event.is_set():
            try:
                with self.asr_lock:
                    partial = self.asr.get_partial()
                    if partial and partial != self.current_partial_text:
                        self.current_partial_text = partial
                time.sleep(0.1)
            except Exception:
                time.sleep(0.1)
    
    def _tts_worker(self) -> None:
        """Process TTS response queue."""
        while not self.shutdown_event.is_set():
            try:
                text = self.response_queue.get(timeout=0.1)
                if self.human_interrupt_event.is_set():
                    with self.response_queue.mutex:
                        self.response_queue.queue.clear()
                    continue
                
                self.tts.speak(text)
            
            except queue.Empty:
                pass
    
    def _process_turn(self, turn_audio_frames: List) -> None:
        """Process a complete conversation turn."""
        if not turn_audio_frames:
            print("⚠️ No audio captured — skipping response")
            return
        
        timing = TurnTiming(turn_id=self.turn_counter)
        timing.speech_end_time = time.perf_counter()
        
        try:
            # Transcribe
            t1 = time.perf_counter()
            
            # Extract frames from (frame, timestamp) tuples
            audio_frames = [frame for frame, _ in turn_audio_frames] if turn_audio_frames and isinstance(turn_audio_frames[0], tuple) else turn_audio_frames
            full_audio = np.concatenate(audio_frames)
            
            if full_audio.size == 0:
                print("⚠️ Empty audio buffer — skipping response")
                return
            
            user_text = self.asr.transcribe(full_audio)
            
            if self.human_interrupt_event.is_set():
                print("🧠 Interrupted during transcription")
                return
            
            timing.whisper_transcribe_ms = (time.perf_counter() - t1) * 1000
            timing.total_audio_duration_sec = full_audio.shape[0] / 16000.0
            timing.whisper_rtf = timing.whisper_transcribe_ms / (timing.total_audio_duration_sec * 1000)
            
            if not user_text:
                print("⚠️ Empty transcription — skipping response")
                return
            
            # Add to memory
            self.conversation_memory.add_message("user", user_text)
            print(f"💬 User: '{user_text}'")
            
            # Generate response
            t3 = time.perf_counter()
            messages = (
                [{"role": "system", "content": SYSTEM_PROMPT}]
                + self.conversation_memory.get_messages()
            )
            
            full_response_text = ""
            sentence_buffer = ""
            
            for token in self.llm.stream_completion(
                messages=messages,
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
            ):
                if self.human_interrupt_event.is_set():
                    print("🛑 LLM interrupted by human")
                    return
                
                if not token:
                    continue
                
                full_response_text += token
                sentence_buffer += token
                
                # Speak on sentence boundary
                if token in ".!?":
                    sentence = sentence_buffer.strip()
                    if sentence:
                        self.response_queue.put(sentence)
                    sentence_buffer = ""
            
            # Handle remaining text
            if sentence_buffer.strip():
                self.response_queue.put(sentence_buffer.strip())
            
            # Timing metrics
            gen_time = time.perf_counter() - t3
            timing.llm_generate_ms = gen_time * 1000
            output_tokens = len(full_response_text.split())
            timing.llm_tokens_per_sec = output_tokens / gen_time if gen_time > 0 else 0
            
            if full_response_text.strip():
                self.conversation_memory.add_message("assistant", full_response_text)
            
            timing.total_latency_ms = (time.perf_counter() - timing.speech_end_time) * 1000
            timing.print_report()
            self.timing_history.append(timing)
            self.turn_counter += 1
            self.human_interrupt_event.clear()
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self) -> None:
        """Main conversation loop."""
        print("🎙️ Real-time conversation started")
        
        vad_buffer = np.zeros(0, dtype=np.float32)
        energy_history = deque(maxlen=15)
        
        try:
            while True:
                # Get audio chunk
                chunk = self.audio_manager.get_audio_chunk()
                if chunk.size == 0:
                    time.sleep(0.01)
                    continue
                
                vad_buffer = np.concatenate([vad_buffer, chunk])
                if len(vad_buffer) < 512:
                    continue
                
                frame = vad_buffer[:512]
                vad_buffer = vad_buffer[512:]
                
                now = time.time()
                
                # Speech detection
                speech_started, rms = self.audio_manager.detect_speech(frame)
                energy_history.append(rms)
                sustained = self.audio_manager.is_sustained_speech(energy_history)
                
                if speech_started or sustained:
                    self.human_speaking_now.set()
                else:
                    self.human_speaking_now.clear()
                
                # Turn-taking state machine
                with self.asr_lock:
                    partial = self.current_partial_text
                
                state, should_end_turn = self.turn_taker.process_state(
                    speech_started,
                    sustained,
                    now,
                    partial,
                )
                
                # Buffer audio with timestamp
                if state in ("SPEAKING", "PAUSING"):
                    self.turn_audio.append((frame.copy(), now))
                
                # End turn
                if should_end_turn:
                    turn_frames = list(self.turn_audio)
                    self.turn_audio.clear()
                    
                    threading.Thread(
                        target=self._process_turn,
                        args=(turn_frames,),
                        daemon=True,
                    ).start()
        
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.shutdown_event.set()  # Signal all threads to stop
            self.audio_manager.stop()
            time.sleep(0.2)  # Allow threads to finish gracefully
            print("✅ Goodbye!")


if __name__ == "__main__":
    engine = ConversationEngine()
    engine.run()
