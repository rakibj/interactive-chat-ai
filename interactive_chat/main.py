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
    CONFIDENCE_THRESHOLD,
    ACTIVE_PROFILE,
    get_system_prompt,
    get_profile_settings,
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
        # Load profile settings
        self.profile_settings = get_profile_settings(ACTIVE_PROFILE)
        
        self.audio_manager = AudioManager()
        self.turn_taker = TurnTaker()
        self.interruption_manager = InterruptionManager()
        self.conversation_memory = ConversationMemory()
        
        # Update turn_taker with profile-specific settings
        from config import PAUSE_MS, END_MS, SAFETY_TIMEOUT_MS
        self.turn_taker.pause_ms = self.profile_settings["pause_ms"]
        self.turn_taker.end_ms = self.profile_settings["end_ms"]
        self.turn_taker.safety_timeout_ms = self.profile_settings["safety_timeout_ms"]
        
        # Update interruption manager with profile-specific settings
        self.interruption_manager.sensitivity = self.profile_settings["interruption_sensitivity"]
        
        self.asr = get_asr()
        self.llm = get_llm()
        self.tts = get_tts()
        
        # State
        self.turn_audio = deque()
        self.human_speech_start_time = None  # Track when human starts speaking
        self.human_speaking_limit_ack_sent = False  # Track if we've already sent acknowledgment
        self._last_debug_duration = -1  # Track for debug output
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
    
    def _generate_ai_greeting(self, system_prompt: str) -> None:
        """Generate initial AI greeting."""
        print("🤖 AI is speaking first...\n")
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        greeting = ""
        for token in self.llm.stream_completion(
            messages=messages,
            max_tokens=self.profile_settings["max_tokens"],
            temperature=self.profile_settings["temperature"],
        ):
            if token:
                greeting += token
                print(token, end="", flush=True)
        
        print("\n")
        
        if greeting.strip():
            self.conversation_memory.add_message("assistant", greeting.strip())
            self.response_queue.put(greeting.strip())
    
    def _process_turn(self, turn_audio_frames: List, human_limit_ack: str = None) -> None:
        """Process a complete conversation turn.
        
        Args:
            turn_audio_frames: List of audio frames from this turn
            human_limit_ack: Optional acknowledgment to prepend if limit was exceeded
        """
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
            
            # Prepend acknowledgment if human speaking limit was exceeded
            if human_limit_ack:
                print(f"📝 Prepending acknowledgment: '{human_limit_ack}'")
                user_text = f"{human_limit_ack} {user_text}".strip()
            
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
            system_prompt = get_system_prompt(ACTIVE_PROFILE)
            messages = (
                [{"role": "system", "content": system_prompt}]
                + self.conversation_memory.get_messages()
            )
            
            full_response_text = ""
            sentence_buffer = ""
            
            for token in self.llm.stream_completion(
                messages=messages,
                max_tokens=self.profile_settings["max_tokens"],
                temperature=self.profile_settings["temperature"],
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
        import random
        
        system_prompt = get_system_prompt(ACTIVE_PROFILE)
        print(f"🎙️ Real-time conversation started")
        print(f"📋 Profile: {self.profile_settings['name']}")
        print(f"👥 Start with: {self.profile_settings['start'].upper()}")
        print(f"🎙️ Voice: {self.profile_settings['voice']}")
        print(f"⏱️  Timeouts: pause={self.profile_settings['pause_ms']}ms, end={self.profile_settings['end_ms']}ms, safety={self.profile_settings['safety_timeout_ms']}ms")
        if self.profile_settings["human_speaking_limit_sec"]:
            print(f"⏰ Human speaking limit: {self.profile_settings['human_speaking_limit_sec']}s")
        print(f"{'='*60}\n")
        
        # If AI starts, generate opening greeting
        if self.profile_settings["start"] == "ai":
            self._generate_ai_greeting(system_prompt)
        
        vad_buffer = np.zeros(0, dtype=np.float32)
        energy_history = deque(maxlen=15)
        human_limit_exceeded_ack = None  # Track acknowledgment to inject into turn
        
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
                    
                    # Track human speaking start time for time limit
                    if self.human_speech_start_time is None:
                        self.human_speech_start_time = now
                        self.human_speaking_limit_ack_sent = False
                        human_limit_exceeded_ack = None  # Reset for this turn
                        self._last_debug_duration = -1  # Reset debug counter
                        limit_sec = self.profile_settings.get("human_speaking_limit_sec")
                        print(f"\n💬 [SPEECH START] limit_sec={limit_sec}, flag={self.human_speaking_limit_ack_sent}")
                    
                    # Check if human has exceeded speaking time limit
                    limit_sec = self.profile_settings.get("human_speaking_limit_sec")
                    if limit_sec is not None:
                        if not self.human_speaking_limit_ack_sent:
                            speaking_duration = now - self.human_speech_start_time
                            
                            # Print every 1 second of duration
                            if int(speaking_duration) > self._last_debug_duration:
                                self._last_debug_duration = int(speaking_duration)
                                print(f"   [LIMIT CHECK] {speaking_duration:.2f}s (limit: {limit_sec}s, exceeded: {speaking_duration > limit_sec})")
                            
                            if speaking_duration > limit_sec:
                                # Select acknowledgment
                                ack = random.choice(self.profile_settings["acknowledgments"])
                                print(f"\n✅ LIMIT EXCEEDED ({speaking_duration:.1f}s > {limit_sec}s) → interrupting with: '{ack}'")
                                human_limit_exceeded_ack = ack
                                self.human_speaking_limit_ack_sent = True
                                
                                # INTERRUPT: Speak the acknowledgment immediately
                                try:
                                    self.tts.speak(ack)
                                    print(f"🔊 Spoke interruption: '{ack}'")
                                except Exception as e:
                                    print(f"⚠️ Failed to speak interruption: {e}")
                else:
                    self.human_speaking_now.clear()
                    # NOTE: Don't reset speech timer on pauses!
                    # Pauses < 800ms are part of continuous speech.
                    # We only reset when moving to a NEW turn (handled in turn-end logic).
                
                # Turn-taking state machine
                with self.asr_lock:
                    partial = self.current_partial_text
                
                state, should_end_turn = self.turn_taker.process_state(
                    speech_started,
                    sustained,
                    now,
                    partial,
                )
                
                # If human exceeded speaking limit, take over on next pause (don't wait for safety timeout)
                if self.human_speaking_limit_ack_sent and state == "PAUSING":
                    print(f"🎤 Limit exceeded - taking over on pause (not waiting for safety timeout)")
                    should_end_turn = True
                
                # Buffer audio with timestamp
                if state in ("SPEAKING", "PAUSING"):
                    self.turn_audio.append((frame.copy(), now))
                
                # End turn
                if should_end_turn:
                    turn_frames = list(self.turn_audio)
                    self.turn_audio.clear()
                    
                    print(f"📍 Starting turn {self.turn_counter} (ack={human_limit_exceeded_ack})")
                    # Pass the acknowledgment (if limit was exceeded) to turn processing
                    threading.Thread(
                        target=self._process_turn,
                        args=(turn_frames, human_limit_exceeded_ack),
                        daemon=True,
                    ).start()
                    human_limit_exceeded_ack = None  # Reset after passing
                    
                    # Reset speech timer for next turn (after turn processing)
                    self.human_speech_start_time = None
                    self.human_speaking_limit_ack_sent = False
                    print(f"⏱️  Reset timer for next turn")
        
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.shutdown_event.set()  # Signal all threads to stop
            self.audio_manager.stop()
            time.sleep(0.2)  # Allow threads to finish gracefully
            print("✅ Goodbye!")
        except Exception as e:
            print(f"\n❌ FATAL ERROR in main loop: {e}")
            import traceback
            traceback.print_exc()
            self.shutdown_event.set()
            self.audio_manager.stop()


if __name__ == "__main__":
    engine = ConversationEngine()
    engine.run()
