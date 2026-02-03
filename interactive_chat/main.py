"""Minimal orchestration loop for interactive chat system."""
import os
import sys
import random

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
    PROJECT_ROOT,
)
from core import (
    AudioManager,
    ConversationMemory,
    SessionAnalytics,
)
from core.event_driven_core import SystemState, Reducer, Event, Action, EventType, ActionType
from core.signals import get_signal_registry, Signal
from signals.consumer import handle_signal  # Import signal consumer for optional logging
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
    """Main orchestration engine based on Event-Driven Core."""
    
    def __init__(self):
        # Load profile settings
        self.profile_settings = get_profile_settings(ACTIVE_PROFILE)
        
        self.audio_manager = AudioManager()
        self.conversation_memory = ConversationMemory()
        
        # Initialize Event-Driven Core State
        self.state = SystemState(
            authority=self.profile_settings.get("authority", "human"),
            pause_ms=self.profile_settings["pause_ms"],
            end_ms=self.profile_settings["end_ms"],
            safety_timeout_ms=self.profile_settings["safety_timeout_ms"],
            interruption_sensitivity=self.profile_settings["interruption_sensitivity"],
            human_speaking_limit_sec=self.profile_settings.get("human_speaking_limit_sec")
        )
        
        # Event Queue
        self.event_queue = queue.Queue()
        
        self.asr = get_asr()
        self.llm = get_llm()
        self.tts = get_tts()
        
        # State
        self.response_queue = queue.Queue()
        self.human_interrupt_event = threading.Event()
        self.shutdown_event = threading.Event()  # Signal for graceful shutdown
        
        # Analytics
        self.session_analytics = SessionAnalytics(
            profile_name=self.profile_settings["name"],
            logs_dir=PROJECT_ROOT / "logs"
        )
        self.current_turn_analytics = None  # Populated per turn
        
        # New: Internal queue for TTS worker
        self.speech_to_speak_queue = queue.Queue()
        
        # Start threads
        self._start_tts_worker()
        self._start_asr_worker()
        self._start_producer_threads()
    
    def _start_producer_threads(self) -> None:
        """Start threads that emit events."""
        threading.Thread(target=self._audio_producer, daemon=True).start()

    def _audio_producer(self) -> None:
        """Continuously produces audio frames and VAD events."""
        vad_buffer = np.zeros(0, dtype=np.float32)
        energy_history = deque(maxlen=15)
        
        while not self.shutdown_event.is_set():
            chunk = self.audio_manager.get_audio_chunk()
            if chunk.size == 0:
                time.sleep(0.01)
                continue
            
            vad_buffer = np.concatenate([vad_buffer, chunk])
            while len(vad_buffer) >= 512:
                frame = vad_buffer[:512]
                vad_buffer = vad_buffer[512:]
                
                # VAD detection (always do this to keep energy_history current)
                speech_detected, rms = self.audio_manager.detect_speech(frame)
                energy_history.append(rms)
                sustained = self.audio_manager.is_sustained_speech(energy_history)

                # Hardware Mic Gating (AI Authority Only)
                is_ai_auth_turn = self.state.authority == "ai" and self.state.is_ai_speaking
                
                if not is_ai_auth_turn:
                    # Feed ASR (with error handling)
                    from utils.audio import float32_to_int16
                    try:
                        self.asr.accept_waveform(float32_to_int16(frame).tobytes())
                    except Exception as e:
                        # Silently ignore waveform processing errors
                        pass
                    
                    # Emit Events
                    now = time.time()
                    self.event_queue.put(Event(EventType.AUDIO_FRAME, now, "audio_stream", {"frame": frame, "is_speech": speech_detected or sustained}))
                    
                    # Simplified VAD events for core
                    if speech_detected or sustained:
                        self.event_queue.put(Event(EventType.VAD_SPEECH_START, now, "vad"))
                    else:
                        self.event_queue.put(Event(EventType.VAD_SPEECH_STOP, now, "vad"))

    def _start_asr_worker(self) -> None:
        """Periodically update partial text from ASR."""
        def asr_loop():
            while not self.shutdown_event.is_set():
                partial = self.asr.get_partial()
                if partial:
                    self.event_queue.put(Event(EventType.ASR_PARTIAL_TRANSCRIPT, time.time(), "asr", {"text": partial}))
                time.sleep(0.1)
        threading.Thread(target=asr_loop, daemon=True).start()

    def _tts_worker(self) -> None:
        """Process TTS sentences from REDUCER ACTIONS."""
        while not self.shutdown_event.is_set():
            try:
                text = self.speech_to_speak_queue.get(timeout=0.1)
                
                # Interrupt event only for human authority (polite mode otherwise)
                current_authority = self.state.authority
                event_to_pass = self.human_interrupt_event if current_authority == "human" else None
                
                self.tts.speak(text, interrupt_event=event_to_pass)
                
                # IMPORTANT: Notify reducer that speech finished
                self.event_queue.put(Event(EventType.AI_SPEECH_FINISHED, time.time(), "tts"))
                
                self.speech_to_speak_queue.task_done()
                time.sleep(0.1) # Small gap between sentences
            except queue.Empty:
                pass

    def _start_tts_worker(self) -> None:
        threading.Thread(target=self._tts_worker, daemon=True).start()

    def _handle_action(self, action: Action) -> None:
        """Execute side effects based on Actions from Reducer."""
        if action.type == ActionType.LOG:
            print(action.payload.get("message"))
            
        elif action.type == ActionType.INTERRUPT_AI:
            self.human_interrupt_event.set()
            # Clear response queues (both logic and hardware)
            with self.speech_to_speak_queue.mutex:
                self.speech_to_speak_queue.queue.clear()
            print(f"🛑 AI Interrupted: {action.payload.get('reason')}")
            self.asr.reset()
            
        elif action.type == ActionType.PLAY_ACK:
            def play_ack():
                # Don't play ack if user interrupted
                if self.human_interrupt_event.is_set():
                    return
                ack = random.choice(self.profile_settings["acknowledgments"])
                print(f"🔊 Acknowledgment: {ack}")
                self.tts.speak(ack)
            threading.Thread(target=play_ack, daemon=True).start()
            
        elif action.type == ActionType.SPEAK_SENTENCE:
            text = action.payload.get("text")
            self.speech_to_speak_queue.put(text)
            self.state.turn_ai_transcript += text + " "

        elif action.type == ActionType.PROCESS_TURN:
            reason = action.payload.get("reason")
            # Log is now handled by Reducer
            turn_audio = list(self.state.turn_audio_buffer)
            # Reset state for next turn via event to keep it deterministic
            self.event_queue.put(Event(EventType.RESET_TURN, time.time()))
            self.asr.reset()
            
            # Run transcription/LLM in background thread
            threading.Thread(target=self._process_turn_async, args=(turn_audio, reason), daemon=True).start()
        
        elif action.type == ActionType.LOG_TURN:
            # Extract turn metrics from action payload
            from core.analytics import TurnAnalytics
            
            payload = action.payload
            turn_analytics = TurnAnalytics(
                turn_id=payload.get("turn_id", 0),
                timestamp=payload.get("timestamp", time.time()),
                profile_name=self.profile_settings["name"],
                human_speech_duration_sec=payload.get("total_latency_ms", 0) / 1000.0 if payload.get("total_latency_ms") else 0,
                ai_speech_duration_sec=0,  # Will be captured from TTS
                silence_before_end_ms=0,
                interrupt_attempts=payload.get("interrupt_attempts", 0),
                interrupts_accepted=payload.get("interrupt_accepts", 0),
                interrupts_blocked=payload.get("interrupt_attempts", 0) - payload.get("interrupt_accepts", 0),
                interrupt_trigger_reasons=[],
                end_reason=payload.get("end_reason", "silence"),
                authority_mode=self.state.authority,
                sensitivity_value=self.state.interruption_sensitivity,
                partial_transcript_lengths=[len(t.split()) for t in payload.get("partial_transcripts", [])],
                final_transcript_length=len(payload.get("final_transcript", "").split()),
                confidence_score_at_cutoff=payload.get("confidence_score", 1.0),
                transcription_ms=payload.get("transcription_ms", 0),
                llm_generation_ms=payload.get("llm_generation_ms", 0),
                total_latency_ms=payload.get("total_latency_ms", 0),
                human_transcript=payload.get("final_transcript", ""),
                ai_transcript=payload.get("ai_transcript", "").strip(),
                transcript_timestamp=payload.get("timestamp", time.time()),
            )
            
            # Log to analytics system
            self.session_analytics.log_turn(turn_analytics)
            print(f"📊 Turn #{payload.get('turn_id', 0)} logged to analytics")

    def _generate_ai_turn(self) -> None:
        """Generate an AI turn without waiting for user input (for greetings, etc)."""
        try:
            # LLM Stream with timing
            llm_start = time.time()
            messages = [{"role": "system", "content": get_system_prompt(ACTIVE_PROFILE)}] + self.conversation_memory.get_messages()
            full_response = ""
            signals_started = False
            current_sentence = ""
            
            # Hybrid streaming: Stream until <signals, then buffer silently
            for token in self.llm.stream_completion(
                messages=messages,
                max_tokens=self.profile_settings["max_tokens"],
                temperature=self.profile_settings["temperature"],
            ):
                if self.human_interrupt_event.is_set():
                    self.human_interrupt_event.clear()
                    return
                
                if token:
                    full_response += token
                    
                    # Check if signals block is starting (check for opening tag)
                    if "<signals" in full_response and not signals_started:
                        signals_started = True
                        # Send any remaining incomplete sentence before signals
                        if current_sentence.strip():
                            self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": current_sentence.strip()}))
                        current_sentence = ""
                        continue
                    
                    # If signals haven't started, process token as normal sentence
                    if not signals_started:
                        current_sentence += token
                        
                        # Check for sentence-ending punctuation
                        if token in ".!?":
                            if current_sentence.strip():
                                self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": current_sentence.strip()}))
                            current_sentence = ""
                    # else: signals_started = True, just accumulate silently
            
            self.state.turn_llm_generation_ms = (time.time() - llm_start) * 1000
            
            # Strip signal blocks from full response for memory storage
            import re
            clean_response = re.sub(r"<signals>\s*\{.*?\}\s*</signals>", "", full_response, flags=re.DOTALL).strip()
            
            if clean_response:
                self.conversation_memory.add_message("assistant", clean_response)
                
        except Exception as e:
            print(f"❌ Error in AI turn generation: {e}")

    def _process_turn_async(self, audio_frames: List, reason: str) -> None:
        """Heavy lifting for turn processing (ASR -> LLM -> TTS)."""
        try:
            if not audio_frames:
                return
                
            # Capture transcription timing
            transcription_start = time.time()
            full_audio = np.concatenate(audio_frames)
            user_text = self.asr.transcribe(full_audio).strip()
            self.state.turn_transcription_ms = (time.time() - transcription_start) * 1000
            self.state.turn_final_transcript = user_text
            
            # Skip if empty, no letters, or too short (likely noise/error)
            if not user_text or not any(c.isalpha() for c in user_text):
                return
            
            # Filter out very short single words (likely ASR hallucinations on silence/noise)
            words = user_text.split()
            if len(words) == 1 and len(words[0]) <= 3:
                return
                
            print(f"💬 User: '{user_text}'")
            self.conversation_memory.add_message("user", user_text)
            
            # LLM Stream with timing
            llm_start = time.time()
            messages = [{"role": "system", "content": get_system_prompt(ACTIVE_PROFILE)}] + self.conversation_memory.get_messages()
            full_response = ""
            signals_started = False
            current_sentence = ""
            
            # Hybrid streaming: Stream until <signals, then buffer silently
            for token in self.llm.stream_completion(
                messages=messages,
                max_tokens=self.profile_settings["max_tokens"],
                temperature=self.profile_settings["temperature"],
            ):
                if self.human_interrupt_event.is_set():
                    self.human_interrupt_event.clear()
                    return
                
                if token:
                    full_response += token
                    
                    # Check if signals block is starting (check for opening tag)
                    if "<signals" in full_response and not signals_started:
                        signals_started = True
                        # Send any remaining incomplete sentence before signals
                        if current_sentence.strip():
                            self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": current_sentence.strip()}))
                        current_sentence = ""
                        continue
                    
                    # If signals haven't started, process token as normal sentence
                    if not signals_started:
                        current_sentence += token
                        
                        # Check for sentence-ending punctuation
                        if token in ".!?":
                            if current_sentence.strip():
                                self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": current_sentence.strip()}))
                            current_sentence = ""
                    # else: signals_started = True, just accumulate silently
            
            self.state.turn_llm_generation_ms = (time.time() - llm_start) * 1000
            self.state.turn_total_latency_ms = (time.time() - transcription_start) * 1000
            
            # Strip signal blocks from full response for memory storage
            import re
            clean_response = re.sub(r"<signals>\s*\{.*?\}\s*</signals>", "", full_response, flags=re.DOTALL).strip()
            
            if clean_response:
                self.conversation_memory.add_message("assistant", clean_response)
                
        except Exception as e:
            print(f"❌ Error in turn processing: {e}")

    def run(self) -> None:
        """Main dispatcher loop (The Event Loop)."""
        print(f"🎙️ Event-Driven Engine started")
        print(f"📋 Profile: {self.profile_settings['name']} (Authority: {self.state.authority})")
        
        # Get signal registry and attach optional consumer for logging
        signal_registry = get_signal_registry()
        signal_registry.register_all(handle_signal)  # Log all signals to stdout
        
        # Initial Greeting if AI starts
        if self.profile_settings["start"] == "ai":
            threading.Thread(target=self._generate_ai_turn, daemon=True).start()

        try:
            while not self.shutdown_event.is_set():
                try:
                    event = self.event_queue.get(timeout=0.1)
                    
                    # Core Transition
                    self.state, actions = Reducer.reduce(self.state, event)
                    
                    # Handle Side-Effects
                    for action in actions:
                        self._handle_action(action)
                    
                    # Dispatch signals to listeners (non-blocking, listeners are optional)
                    # Note: Signal emission happens in Reducer and _handle_action;
                    # this is just a reference point. Actual signals are emitted via emit_signal()
                    # from within the event_driven_core and this handler.
                        
                except queue.Empty:
                    # Drive state machine forward for timeouts even without external events
                    self.event_queue.put(Event(EventType.TICK, time.time()))
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.shutdown_event.set()
            self.audio_manager.stop()
            # Generate analytics summary
            self.session_analytics.save_summary()
            print("✅ Goodbye!")

if __name__ == "__main__":
    import random
    engine = ConversationEngine()
    engine.run()
