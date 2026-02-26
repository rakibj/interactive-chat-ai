"""Minimal orchestration loop for interactive chat system."""
import os
import sys
import random
import argparse

# Fix Windows Unicode console encoding issues
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

# Load environment variables FIRST, before any other imports
from dotenv import load_dotenv
load_dotenv()

import threading
import time
import queue
import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import List, Dict, Any

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

from .config import (
    CONFIDENCE_THRESHOLD,
    ACTIVE_PROFILE,
    ACTIVE_PHASE_PROFILE,
    PHASE_PROFILES,
    LLM_BACKEND,
    get_system_prompt,
    get_system_prompt_with_phase_context,
    get_profile_settings,
    PROJECT_ROOT,
)
from .core import (
    AudioManager,
    ConversationMemory,
    SessionAnalytics,
)
from .core.event_driven_core import SystemState, Reducer, Event, Action, EventType, ActionType
from .core.signals import get_signal_registry, Signal
from .signals.consumer import handle_signal  # Import signal consumer for optional logging
from .interfaces import get_asr, get_llm, get_tts

# Global engine instance for API server access
_global_engine = None

def set_global_engine(engine):
    """Set the global engine instance for API access."""
    global _global_engine
    _global_engine = engine

def get_global_engine():
    """Get the global engine instance."""
    global _global_engine
    return _global_engine


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
    
    def __init__(self, profile_key: str = None):
        """Initialize ConversationEngine with optional profile override.
        
        Args:
            profile_key: Profile key to use (overrides ACTIVE_PROFILE and ACTIVE_PHASE_PROFILE from config)
        """
        # Determine if using PhaseProfile or standalone InstructionProfile
        self.active_phase_profile = None
        self.phase_emitted_signals = []  # Track signals for phase transitions
        
        current_phase_name = None  # Initialize phase name
        
        # Use provided profile_key if given, otherwise use config
        active_profile = profile_key or ACTIVE_PROFILE
        active_phase_profile_key = profile_key or ACTIVE_PHASE_PROFILE
        
        # Check if it's a PhaseProfile (try to load from PHASE_PROFILES)
        if active_phase_profile_key and active_phase_profile_key in PHASE_PROFILES:
            # Using PhaseProfile mode
            self.active_phase_profile = PHASE_PROFILES[active_phase_profile_key]
            current_phase_id = self.active_phase_profile.initial_phase
            current_profile = self.active_phase_profile.get_phase(current_phase_id)
            
            if not current_profile:
                raise ValueError(f"Invalid initial phase: {current_phase_id}")
            
            current_phase_name = current_profile.name  # Get the phase display name
            
            print(f"🎭 Starting PhaseProfile: {self.active_phase_profile.name}")
            print(f"🔀 Initial phase: {current_profile.name}")
            
            self.profile_settings = get_profile_settings(None, current_profile)
        else:
            # Using standalone InstructionProfile mode
            self.profile_settings = get_profile_settings(active_profile)
            current_phase_id = None
        
        # Initialize audio manager with error handling
        print("[INIT] Initializing audio system...")
        try:
            self.audio_manager = AudioManager()
        except Exception as e:
            print(f"⚠️ Audio manager failed: {e}")
            print(f"⚠️ Audio input will not be available")
            # Create a minimal audio manager that returns empty chunks
            self.audio_manager = None
        
        self.conversation_memory = ConversationMemory()
        
        # Calculate total phases if using phase profile
        total_phases = 0
        if self.active_phase_profile:
            total_phases = len(self.active_phase_profile.phases)
        
        # Initialize Event-Driven Core State
        self.state = SystemState(
            authority=self.profile_settings.get("authority", "human"),
            pause_ms=self.profile_settings["pause_ms"],
            end_ms=self.profile_settings["end_ms"],
            safety_timeout_ms=self.profile_settings["safety_timeout_ms"],
            interruption_sensitivity=self.profile_settings["interruption_sensitivity"],
            human_speaking_limit_sec=self.profile_settings.get("human_speaking_limit_sec"),
            current_phase_id=current_phase_id,
            phase_profile_name=self.active_phase_profile.name if self.active_phase_profile else None,
            # Add phase observation tracking
            active_phase_id=current_phase_id,
            active_phase_name=current_phase_name,  # Add the phase display name
            phase_index=0,
            total_phases=total_phases,
            phases_completed=[],
        )
        
        # Event Queue
        self.event_queue = queue.Queue()
        
        try:
            self.asr = get_asr()
        except Exception as e:
            print(f"⚠️ ASR not available: {e}")
            self.asr = None
        
        try:
            self.llm = get_llm()
        except Exception as e:
            print(f"⚠️ LLM not available: {e}")
            self.llm = None
        
        try:
            self.tts = get_tts()
        except Exception as e:
            print(f"⚠️ TTS not available: {e}")
            self.tts = None
        
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
        # Skip if audio manager is not available
        if self.audio_manager is None:
            print("⚠️  Audio producer: Skipping (audio manager not available)")
            return
        
        vad_buffer = np.zeros(0, dtype=np.float32)
        energy_history = deque(maxlen=15)
        last_emitted_vad_state = False
        vad_stability_count = 0
        vad_stability_threshold = 1  # Reduce to 1 frame for faster response (32ms)
        
        frame_count = 0
        
        while not self.shutdown_event.is_set():
            chunk = self.audio_manager.get_audio_chunk()
            if chunk.size == 0:
                time.sleep(0.01)
                continue
            
            vad_buffer = np.concatenate([vad_buffer, chunk])
            while len(vad_buffer) >= 512:
                frame = vad_buffer[:512]
                vad_buffer = vad_buffer[512:]
                
                # VAD detection
                speech_detected, rms = self.audio_manager.detect_speech(frame)
                energy_history.append(rms)
                sustained = self.audio_manager.is_sustained_speech(energy_history)
                current_vad_state = speech_detected or sustained
                
                frame_count += 1

                # Hardware Mic Gating (AI Authority Only)
                # CRITICAL: Check both authority AND is_ai_speaking
                is_ai_auth_turn = (
                    self.state.authority == "ai" and 
                    self.state.is_ai_speaking and
                    not getattr(self, '_audio_producer_override_gating', False)
                )
                
                now = time.time()
                
                if not is_ai_auth_turn:
                    # MICROPHONE ACTIVE - Process audio normally
                    
                    # Feed ASR (with error handling)
                    from utils.audio import float32_to_int16
                    try:
                        if self.asr is not None:
                            self.asr.accept_waveform(float32_to_int16(frame).tobytes())
                    except Exception as e:
                        pass  # Ignore errors
                    
                    # Always emit AUDIO_FRAME
                    self.event_queue.put(Event(EventType.AUDIO_FRAME, now, "audio_stream", {"frame": frame, "is_speech": current_vad_state}))
                    
                    # Emit debounced VAD events (1 frame threshold)
                    if current_vad_state != last_emitted_vad_state:
                        # State changed
                        vad_stability_count += 1
                        if vad_stability_count >= vad_stability_threshold:
                            # Emit transition immediately
                            if current_vad_state:
                                self.event_queue.put(Event(EventType.VAD_SPEECH_START, now, "vad"))
                                print(f"🟢 VAD_SPEECH_START (frame {frame_count})")
                            else:
                                self.event_queue.put(Event(EventType.VAD_SPEECH_STOP, now, "vad"))
                                print(f"⭕ VAD_SPEECH_STOP (frame {frame_count})")
                            last_emitted_vad_state = current_vad_state
                            vad_stability_count = 0
                    else:
                        # State unchanged
                        vad_stability_count = 0
                else:
                    # MICROPHONE GATED (AI is speaking) - Skip audio processing
                    pass

    def _start_asr_worker(self) -> None:
        """Periodically update partial text from ASR."""
        def asr_loop():
            while not self.shutdown_event.is_set():
                if self.asr is None:
                    time.sleep(0.1)
                    continue
                partial = self.asr.get_partial()
                if partial:
                    self.event_queue.put(Event(EventType.ASR_PARTIAL_TRANSCRIPT, time.time(), "asr", {"text": partial}))
                time.sleep(0.1)
        
        # Only start ASR loop if ASR is available
        if self.asr is not None:
            threading.Thread(target=asr_loop, daemon=True).start()

    def _tts_worker(self) -> None:
        """Process TTS sentences from REDUCER ACTIONS."""
        # Drain any queued speech even if shutdown has been requested.
        print("🎙️ TTS worker started, waiting for text...")
        while not self.shutdown_event.is_set() or not self.speech_to_speak_queue.empty():
            try:
                text = self.speech_to_speak_queue.get(timeout=0.1)
                print(f"📤 TTS: Got text from queue: '{text[:60]}'")
                
                # Only speak if TTS is available
                if self.tts is not None:
                    print(f"🔊 TTS: Speaking now...")
                    # Interrupt event only for human authority (polite mode otherwise)
                    current_authority = self.state.authority
                    event_to_pass = self.human_interrupt_event if current_authority == "human" else None
                    
                    self.tts.speak(text, interrupt_event=event_to_pass)
                    print(f"✅ TTS: Finished speaking")
                else:
                    print(f"⚠️  TTS not initialized, skipping: '{text[:60]}'")
                
                # IMPORTANT: Notify reducer that speech finished
                self.event_queue.put(Event(EventType.AI_SPEECH_FINISHED, time.time(), "tts"))
                
                self.speech_to_speak_queue.task_done()
                time.sleep(0.1) # Small gap between sentences
            except queue.Empty:
                pass
            except Exception as e:
                print(f"❌ TTS worker error: {e}")
                import traceback
                traceback.print_exc()

    def _request_shutdown(self) -> None:
        """Gracefully stop processing after pending speech finishes."""
        if self.shutdown_event.is_set():
            return
        # Wait for any queued speech to finish (bounded wait)
        try:
            self.speech_to_speak_queue.join()
        except Exception:
            pass

        start_wait = time.time()
        while (self.state.is_ai_speaking or not self.speech_to_speak_queue.empty()) and (time.time() - start_wait) < 5:
            time.sleep(0.05)

        self.shutdown_event.set()
        # Stop hardware streams
        if self.audio_manager is not None:
            self.audio_manager.stop()

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
            if self.asr is not None:
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
            # Additional safety: strip any signal tags that might have slipped through
            import re
            text = re.sub(r'<signals.*?</signals>', '', text, flags=re.DOTALL).strip()
            text = re.sub(r'<signals.*$', '', text, flags=re.DOTALL).strip()
            if text:  # Only queue if there's actual text after cleaning
                print(f"📥 SPEAK_SENTENCE action: queueing '{text[:60]}' for TTS")
                self.speech_to_speak_queue.put(text)
                self.state.turn_ai_transcript += text + " "
            else:
                print(f"⚠️  SPEAK_SENTENCE action: empty text after cleaning")


        elif action.type == ActionType.PROCESS_TURN:
            reason = action.payload.get("reason")
            # Log is now handled by Reducer
            turn_audio = list(self.state.turn_audio_buffer)
            
            # Debug: Log turn completion
            print(f"\n🔵 PROCESS_TURN triggered: reason={reason}, audio_frames={len(turn_audio)}")
            
            if len(turn_audio) == 0:
                print(f"⚠️  Warning: No audio frames captured for turn")
            
            # Reset state for next turn via event to keep it deterministic
            self.event_queue.put(Event(EventType.RESET_TURN, time.time()))
            if self.asr is not None:
                self.asr.reset()
            
            # Run transcription/LLM in background thread
            print(f"🚀 Starting _process_turn_async thread...")
            threading.Thread(target=self._process_turn_async, args=(turn_audio, reason), daemon=True).start()
        
        elif action.type == ActionType.LOG_TURN:
            # Extract turn metrics from action payload
            from core.analytics import TurnAnalytics
            
            payload = action.payload
            turn_analytics = TurnAnalytics(
                turn_id=payload.get("turn_id", 0),
                timestamp=payload.get("timestamp", time.time()),
                profile_name=self.profile_settings["name"],
                phase_id=self.state.current_phase_id if self.active_phase_profile else None,
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
        
        elif action.type == ActionType.TRANSITION_PHASE:
            # Execute phase transition (only if using PhaseProfile)
            if self.active_phase_profile:
                next_phase_id = action.payload.get("next_phase")
                self._transition_to_phase(next_phase_id)
    
    def _transition_to_phase(self, next_phase_id: str) -> None:
        """Transition to a new phase in the PhaseProfile."""
        if not self.active_phase_profile:
            return
        
        next_profile = self.active_phase_profile.get_phase(next_phase_id)
        if not next_profile:
            print(f"⚠️ Warning: Phase '{next_phase_id}' not found")
            return
        
        # SAVE current phase messages before clearing
        if self.state.current_phase_id:
            try:
                current_messages = self.conversation_memory.get_messages()
                # Filter out system messages
                non_system_messages = [
                    msg for msg in current_messages
                    if msg.get("role") != "system"
                ]
                self.state.message_history_by_phase[self.state.current_phase_id] = non_system_messages
                print(f"💾 Saved {len(non_system_messages)} messages from phase '{self.state.current_phase_id}'")
            except Exception as e:
                print(f"⚠️ Warning: Could not save phase messages: {e}")
        
        # Update profile settings
        self.profile_settings = get_profile_settings(None, next_profile)
        
        # Mark previous phase as completed (if there was one)
        if self.state.current_phase_id and self.state.current_phase_id not in self.state.phases_completed:
            self.state.phases_completed.append(self.state.current_phase_id)
        
        # CRITICAL: Deduplicate the entire list (remove any accumulated duplicates)
        # Use dict.fromkeys to preserve order while removing duplicates
        self.state.phases_completed = list(dict.fromkeys(self.state.phases_completed))
        
        # Calculate phase index (position in phase list)
        phase_ids = list(self.active_phase_profile.phases.keys())
        new_phase_index = phase_ids.index(next_phase_id) if next_phase_id in phase_ids else 0
        
        # Update state with new profile settings
        self.state.authority = self.profile_settings.get("authority", "human")
        self.state.pause_ms = self.profile_settings["pause_ms"]
        self.state.end_ms = self.profile_settings["end_ms"]
        self.state.safety_timeout_ms = self.profile_settings["safety_timeout_ms"]
        self.state.interruption_sensitivity = self.profile_settings["interruption_sensitivity"]
        self.state.human_speaking_limit_sec = self.profile_settings.get("human_speaking_limit_sec")
        self.state.current_phase_id = next_phase_id
        self.state.active_phase_id = next_phase_id  # Keep these in sync
        self.state.active_phase_name = next_profile.name  # Set the phase display name
        self.state.phase_index = new_phase_index
        
        # Clear phase signals for new phase
        self.phase_emitted_signals.clear()
        
        # DO NOT clear conversation_memory - messages are preserved in message_history_by_phase
        # and the /api/chat endpoint reconstructs the full history from all phases
        # self.conversation_memory.clear()  # REMOVED: Preserve chat history across phases
        
        print(f"✅ Transitioned to phase: {next_profile.name}")
        
        # If new phase starts with AI, generate greeting
        if next_profile.start == "ai":
            time.sleep(0.5)  # Brief pause between phases
            self._generate_ai_turn()
    
    def _check_phase_transitions(self, emitted_signals: List[str]) -> None:
        """Check if any signals trigger a phase transition."""
        if not self.active_phase_profile or not self.state.current_phase_id:
            return
        
        # Add newly emitted signals to the list
        for sig in emitted_signals:
            if sig not in self.phase_emitted_signals:
                self.phase_emitted_signals.append(sig)
        
        # Check if we should transition
        next_phase = self.active_phase_profile.find_transition(
            self.state.current_phase_id,
            self.phase_emitted_signals
        )
        
        if next_phase:
            print(f"🔀 Phase transition triggered: {self.state.current_phase_id} → {next_phase}")
            print(f"   Signals that triggered: {self.phase_emitted_signals}")
            
            # Emit phase transition event
            self.event_queue.put(Event(
                EventType.PHASE_TRANSITION,
                time.time(),
                "phase_manager",
                {"next_phase": next_phase}
            ))
            return
        else:
            # No transition found yet - show what would trigger it
            possible_transitions = [
                t for t in self.active_phase_profile.transitions
                if t.from_phase == self.state.current_phase_id
            ]
            if possible_transitions:
                for t in possible_transitions:
                    print(f"⏳ Waiting for transition signal: {self.state.current_phase_id} → {t.to_phase}")
                    print(f"   Needs signal(s): {t.trigger_signals}")

        # No transition fired. Check if this is a terminal phase. Only
        # consider shutdown when a signal that belongs to THIS phase has been
        # emitted (ignores stray signals carried over from previous phases).
        has_transitions = any(
            t.from_phase == self.state.current_phase_id 
            for t in self.active_phase_profile.transitions
        )
        if not has_transitions:
            current_phase_profile = self.active_phase_profile.get_phase(self.state.current_phase_id)
            allowed_signals = {f"custom.{name}" for name in (current_phase_profile.signals.keys() if current_phase_profile else [])}
            # Only terminate if at least one allowed signal for this phase was emitted
            if allowed_signals and any(sig in allowed_signals for sig in self.phase_emitted_signals):
                print(f"\n{'='*60}")
                print(f"✅ Phase Profile Complete: {self.active_phase_profile.name}")
                print(f"{'='*60}\n")
                print("All phases completed. Shutting down gracefully...")
                time.sleep(0.5)  # Brief pause before shutdown
                self._request_shutdown()
    
    def _is_valid_ai_sentence(self, text: str) -> bool:
        """Check if sentence is valid (not garbage/empty).
        
        Filters out:
        - Empty or whitespace-only strings
        - Strings that are just punctuation marks
        - Strings that are just dots, ellipsis, or repetitive punctuation
        """
        if not text or not text.strip():
            return False
        
        # Remove all punctuation and spaces - if nothing left, it's garbage
        import re
        alphanumeric_only = re.sub(r'[^a-zA-Z0-9]', '', text)
        if not alphanumeric_only:
            return False
        
        # Additional checks
        stripped = text.strip()
        # Reject if it's just dots or repeated punctuation
        if all(c in '.,!?;:…-' for c in stripped):
            return False
        
        return True

    def _get_current_system_prompt(self) -> str:
        """Get system prompt for current profile/phase."""
        if self.active_phase_profile and self.state.current_phase_id:
            # PhaseProfile mode: Include phase context
            current_profile = self.active_phase_profile.get_phase(self.state.current_phase_id)
            phase_context = self.active_phase_profile.get_phase_context(self.state.current_phase_id)
            return get_system_prompt_with_phase_context(current_profile, phase_context)
        else:
            # Standalone mode
            return get_system_prompt(ACTIVE_PROFILE)

    def _generate_ai_turn(self) -> None:
        """Generate an AI turn without waiting for user input (for greetings, etc)."""
        try:
            print(f"\n🎬 _generate_ai_turn() START")
            print(f"   authority={self.state.authority}, is_ai_speaking={self.state.is_ai_speaking}")
            
            # DO NOT set is_ai_speaking here - let the reducer manage it
            # Just set current_speaker so UI knows AI will speak
            self.state.current_speaker = "ai"
            print(f"   Set current_speaker=ai (reducer will set is_ai_speaking)")
            
            # LLM Stream with timing
            print(f"   Getting system prompt...")
            system_prompt = self._get_current_system_prompt()
            print(f"   System prompt: {len(system_prompt)} chars")
            
            # Skip if LLM is not available
            if self.llm is None:
                print(f"   ⚠️  LLM not available, skipping AI turn")
                self.state.current_speaker = "silence"
                return
            
            print(f"   Calling LLM.stream_completion()...")
            llm_start = time.time()
            messages = [{"role": "system", "content": system_prompt}] + self.conversation_memory.get_messages()
            print(f"   Messages to LLM: {len(messages)}")
            
            full_response = ""
            signals_started = False
            current_sentence = ""
            sentence_count = 0
            
            # Hybrid streaming: Stream until <signals, then buffer silently
            try:
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
                            # Strip any partial signal tags from current_sentence before sending
                            import re
                            clean_sentence = re.sub(r'<signals.*$', '', current_sentence, flags=re.DOTALL).strip()
                            if clean_sentence and self._is_valid_ai_sentence(clean_sentence):
                                print(f"   📤 Sentence {sentence_count}: '{clean_sentence[:50]}'")
                                self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": clean_sentence}))
                                sentence_count += 1
                            current_sentence = ""
                            continue
                        
                        # If signals haven't started, process token as normal sentence
                        if not signals_started:
                            current_sentence += token
                            
                            # Check for sentence-ending punctuation
                            if token in ".!?":
                                if current_sentence.strip() and self._is_valid_ai_sentence(current_sentence.strip()):
                                    print(f"   📤 Sentence {sentence_count}: '{current_sentence.strip()[:50]}'")
                                    self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": current_sentence.strip()}))
                                    sentence_count += 1
                                current_sentence = ""
                        # else: signals_started = True, just accumulate silently
            except Exception as llm_error:
                # Catch API auth errors and other LLM failures
                error_msg = str(llm_error)
                if "401" in error_msg or "invalid_request_error" in error_msg or "invalid_api_key" in error_msg or "unauthorized" in error_msg.lower():
                    print(f"\n{'='*60}")
                    print(f"⚠️  {LLM_BACKEND.upper()} API Authentication Error")
                    print(f"{'='*60}")
                    print(f"Error: {error_msg}")
                    print(f"\n💡 Solutions:")
                    print(f"   1. Check that your {LLM_BACKEND.upper()}_API_KEY in .env is valid")
                    print(f"   2. Make sure your API key hasn't expired")
                    print(f"   3. Try a different API backend:")
                    print(f"      - GROQ (currently set)")
                    print(f"      - OpenAI (requires OPENAI_API_KEY)")
                    print(f"      - DeepSeek (requires DEEPSEEK_API_KEY)")
                    print(f"      - Local (download a GGUF model, no API key needed)")
                    print(f"\n📝 To switch backends, edit interactive_chat/config.py:")
                    print(f"   LLM_BACKEND = 'local'  # or 'openai', 'deepseek'")
                    print(f"\n🛠️  Then restart the application")
                    print(f"{'='*60}\n")
                    print(f"System will continue with text-only mode (demo mode)")
                    
                    # Queue a helpful message to user
                    error_response = "I apologize, but I cannot initialize the voice system at the moment. The system is running in text-only mode. Please verify your API configuration and restart."
                    for sentence in error_response.split(". "):
                        sentence = sentence.strip()
                        if sentence:
                            self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": sentence + "."}))
                            sentence_count += 1
                else:
                    # Re-raise non-auth errors
                    raise
            
            # Handle any remaining sentence at end of stream (stream ended without period)
            if current_sentence.strip() and not signals_started and self._is_valid_ai_sentence(current_sentence.strip()):
                print(f"   📤 Sentence {sentence_count}: '{current_sentence.strip()[:50]}'")
                self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": current_sentence.strip()}))
                sentence_count += 1
            
            generation_time = (time.time() - llm_start) * 1000
            print(f"✅ _generate_ai_turn() END: {sentence_count} sentences in {generation_time:.0f}ms")
            
            self.state.turn_llm_generation_ms = generation_time
            
            # Strip signal blocks from full response for memory storage
            import re
            clean_response = re.sub(r"<signals>\s*\{.*?\}\s*</signals>", "", full_response, flags=re.DOTALL).strip()
            
            # Extract emitted signals for phase transitions
            emitted_signals = self._extract_signals(full_response)
            
            # Log signals for debugging
            if emitted_signals:
                print(f"📡 Signals emitted: {emitted_signals}")
            
            self._check_phase_transitions(emitted_signals)
            
            if clean_response:
                self.conversation_memory.add_message("assistant", clean_response)
            
            # NOTE: Don't set is_ai_speaking=False here - let AI_SPEECH_FINISHED event from reducer handle it
            # Just mark that AI has responded (for AI authority mode)
            self.state.ai_has_responded = True
            print(f"🎬 AI turn finished (ai_has_responded=True)")
                
        except Exception as e:
            print(f"❌ Error in AI turn generation: {e}")
            import traceback
            traceback.print_exc()
            # Even on error, mark that AI "responded" (failed) so human can interact and retry
            self.state.ai_has_responded = True
    
    def _extract_signals(self, response_text: str) -> List[str]:
        """Extract signal names from LLM response.
        
        Handles nested JSON, multiple signal blocks, and malformed inputs gracefully.
        """
        import re
        import json
        
        signal_names = []
        
        # Find all <signals>...</signals> blocks
        signal_blocks = re.findall(
            r"<signals>\s*(.*?)\s*</signals>",
            response_text,
            flags=re.DOTALL
        )
        
        for block in signal_blocks:
            # Try to extract and parse JSON from the block
            signals_dict = self._parse_signal_json(block.strip())
            if signals_dict:
                signal_names.extend(signals_dict.keys())
        
        return signal_names
    
    def _parse_signal_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from signal block with robust error handling.
        
        Tries multiple parsing strategies to handle:
        - Nested JSON objects with braces
        - Malformed JSON
        - Extra whitespace
        - Invalid JSON structures
        """
        import json
        
        if not text or not text.strip():
            return {}
        
        # Strategy 1: Direct JSON parse (works for well-formed JSON)
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Find the outermost braces and extract JSON
        text = text.strip()
        if text.startswith('{') and text.endswith('}'):
            try:
                # Count braces to find matching close brace
                brace_count = 0
                for i, char in enumerate(text):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                    
                    # When brace_count returns to 0, we found the matching close brace
                    if brace_count == 0 and i > 0:
                        json_str = text[:i+1]
                        try:
                            result = json.loads(json_str)
                            if isinstance(result, dict):
                                return result
                        except json.JSONDecodeError:
                            pass
                        break
            except Exception:
                pass
        
        # Strategy 3: Try to extract JSON-like structure more aggressively
        # Look for pattern: { ... "key": ... }
        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', text)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        
        # If all strategies fail, return empty dict
        return {}

    def _process_turn_async(self, audio_frames: List, reason: str) -> None:
        """Heavy lifting for turn processing (ASR -> LLM -> TTS)."""
        try:
            if not audio_frames:
                return
            
            # Skip if ASR is not available
            if self.asr is None:
                print(f"⚠️  ASR not available, skipping turn processing")
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
            messages = [{"role": "system", "content": self._get_current_system_prompt()}] + self.conversation_memory.get_messages()
            full_response = ""
            signals_started = False
            current_sentence = ""
            
            # Skip if LLM is not available
            if self.llm is None:
                print(f"⚠️  LLM not available, skipping response generation")
                return
            
            try:
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
                            # Strip any partial signal tags from current_sentence before sending
                            import re
                            clean_sentence = re.sub(r'<signals.*$', '', current_sentence, flags=re.DOTALL).strip()
                            if clean_sentence and self._is_valid_ai_sentence(clean_sentence):
                                self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": clean_sentence}))
                            current_sentence = ""
                            continue
                        
                        # If signals haven't started, process token as normal sentence
                        if not signals_started:
                            current_sentence += token
                            
                            # Check for sentence-ending punctuation
                            if token in ".!?":
                                if current_sentence.strip() and self._is_valid_ai_sentence(current_sentence.strip()):
                                    self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": current_sentence.strip()}))
                                current_sentence = ""
                        # else: signals_started = True, just accumulate silently
                
                # Handle any remaining sentence at end of stream (stream ended without period)
                if current_sentence.strip() and not signals_started and self._is_valid_ai_sentence(current_sentence.strip()):
                    self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": current_sentence.strip()}))
                
            except Exception as llm_error:
                # Handle LLM errors (e.g., invalid API key)
                error_msg = str(llm_error)
                if "401" in error_msg or "invalid_api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    print(f"\n❌ {LLM_BACKEND.upper()} API Authentication Error")
                    print(f"   Error: {error_msg}")
                    error_text = f"I apologize, but the {LLM_BACKEND} API encountered an authentication error. Please check your API key in .env or switch to a different backend."
                    self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": error_text}))
                    self.state.ai_has_responded = True
                    self.conversation_memory.add_message("assistant", error_text)
                else:
                    print(f"❌ LLM Error ({LLM_BACKEND}): {error_msg}")
                    error_text = "I apologize, but an error occurred while processing your request. Please try again."
                    self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": error_text}))
                    self.state.ai_has_responded = True
                    self.conversation_memory.add_message("assistant", error_text)
                return
            
            self.state.turn_llm_generation_ms = (time.time() - llm_start) * 1000
            self.state.turn_total_latency_ms = (time.time() - transcription_start) * 1000
            
            # Strip signal blocks from full response for memory storage
            import re
            clean_response = re.sub(r"<signals>\s*\{.*?\}\s*</signals>", "", full_response, flags=re.DOTALL).strip()
            
            # Extract emitted signals for phase transitions
            emitted_signals = self._extract_signals(full_response)
            self._check_phase_transitions(emitted_signals)
            
            if clean_response:
                self.conversation_memory.add_message("assistant", clean_response)
                self.state.ai_has_responded = True  # Mark that AI has responded (for AI authority mode)
                
        except Exception as e:
            print(f"❌ Error in turn processing: {e}")

    def _start_api_server(self) -> None:
        """Start FastAPI server in background thread for remote API access.
        
        This method registers the engine with the API server and starts uvicorn.
        Useful for custom entry points like run_html_app.py that need to start
        the API server programmatically.
        """
        try:
            import uvicorn
            from interactive_chat import server as api_server
            
            # Register engine with API server
            api_server.set_engine(self)
            
            def run_api():
                uvicorn.run(
                    api_server.app,
                    host="0.0.0.0",
                    port=8000,
                    log_level="warning",
                    access_log=False
                )
            
            api_thread = threading.Thread(target=run_api, daemon=True)
            api_thread.start()
            print("✅ API server started in background (http://localhost:8000)")
            time.sleep(3)  # Wait for API to fully start
            
        except Exception as e:
            print(f"⚠️  Could not start API server: {e}")
            print("   Run without API server capability")

    def run(self) -> None:
        """Main dispatcher loop (The Event Loop)."""
        print(f"🎙️ Event-Driven Engine started")
        print(f"📋 Profile: {self.profile_settings['name']} (Authority: {self.state.authority})")
        print(f"📍 Start mode: {self.profile_settings.get('start', 'human')}")
        
        # Get signal registry and attach optional consumer for logging
        signal_registry = get_signal_registry()
        signal_registry.register_all(handle_signal)  # Log all signals to stdout
        
        # Auto-start if profile specifies start="ai"
        if self.profile_settings["start"] == "ai":
            print("\n🤖 AI-initiated conversation - starting AI greeting...")
            print(f"   is_ai_speaking={self.state.is_ai_speaking}")
            print(f"   authority={self.state.authority}")
            print(f"   Spawning _generate_ai_turn() thread...")
            threading.Thread(target=self._generate_ai_turn, daemon=True).start()
        else:
            print(f"\n👤 Human-initiated conversation - waiting for speech...")

        try:
            event_count = 0
            while not self.shutdown_event.is_set():
                try:
                    event = self.event_queue.get(timeout=0.1)
                    event_count += 1
                    
                    # Log every 100th event to reduce noise but keep visibility
                    if event_count % 100 == 0 or event.type in [EventType.VAD_SPEECH_START, EventType.VAD_SPEECH_STOP, "PROCESS_TURN", "RESET_TURN"]:
                        print(f"📥 Event #{event_count}: {event.type}")
                    
                    # Core Transition with exception handling
                    try:
                        self.state, actions = Reducer.reduce(self.state, event)
                    except Exception as reduction_error:
                        print(f"\n❌ ERROR in state reduction: {reduction_error}")
                        import traceback
                        traceback.print_exc()
                        print(f"   Event type: {event.type}")
                        print(f"   Last event: {event}")
                        print(f"   Skipping this event and continuing...\n")
                        continue
                    
                    # Handle Side-Effects with exception handling
                    try:
                        for action in actions:
                            self._handle_action(action)
                    except Exception as action_error:
                        print(f"\n❌ ERROR handling action: {action_error}")
                        import traceback
                        traceback.print_exc()
                        print(f"   Skipping this action and continuing...\n")
                        continue
                    
                    # Dispatch signals to listeners (non-blocking, listeners are optional)
                    # Note: Signal emission happens in Reducer and _handle_action;
                    # this is just a reference point. Actual signals are emitted via emit_signal()
                    # from within the event_driven_core and this handler.
                        
                except queue.Empty:
                    # Drive state machine forward for timeouts even without external events
                    self.event_queue.put(Event(EventType.TICK, time.time()))
                except Exception as loop_error:
                    # Catch any other unexpected errors in the main loop
                    print(f"\n❌ CRITICAL ERROR in event loop: {loop_error}")
                    import traceback
                    traceback.print_exc()
                    print(f"   Attempting to continue event loop...\n")
                    continue
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self._request_shutdown()
        except Exception as fatal_error:
            # Catch any fatal errors in the main loop
            print(f"\n❌ FATAL ERROR: {fatal_error}")
            import traceback
            traceback.print_exc()
            print(f"   App terminating abnormally\n")
        finally:
            # Ensure resources are stopped and analytics saved even for graceful exits
            if self.audio_manager is not None:
                self.audio_manager.stop()
            self.session_analytics.save_summary()
            print("✅ Goodbye!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive Chat AI Engine")
    parser.add_argument('--no-api', action='store_true', help='Skip API server (run engine only)')
    parser.add_argument('--no-gradio', action='store_true', help='Skip Gradio (API/Engine only)')
    parser.add_argument('--api-only', action='store_true', help='Run API server only (no engine)')
    args = parser.parse_args()
    
    # Create engine instance FIRST (before API server)
    engine = ConversationEngine()
    
    # Set global engine for API access
    set_global_engine(engine)
    
    # Start API server in background thread (unless --no-api or --api-only flag)
    if not args.no_api and not args.api_only:
        try:
            import uvicorn
            from interactive_chat import server as api_server
            
            # Register engine with API server BEFORE starting uvicorn
            api_server.set_engine(engine)
            
            def run_api():
                uvicorn.run(
                    api_server.app,
                    host="0.0.0.0",
                    port=8000,
                    log_level="warning",  # Reduce log verbosity
                    access_log=False
                )
            
            api_thread = threading.Thread(target=run_api, daemon=True)
            api_thread.start()
            print("✅ API server started in background (http://localhost:8000)")
            time.sleep(3)  # Wait for API to fully start
        except Exception as e:
            print(f"⚠️  Could not start API server: {e}")
            print("   Run with --no-api to skip API server")
    
    # Launch Gradio (unless --no-gradio flag)
    if not args.no_gradio:
        try:
            from gradio_demo import GradioDemoApp
            
            # Give user instructions
            print("\n" + "="*60)
            print("🎤 INTERACTIVE CHAT AI - Gradio Interface")
            print("="*60)
            print("\n✅ API Server:  http://localhost:8000")
            print("✅ Gradio Demo: http://localhost:7860")
            print("\n💡 Complete Gradio-controlled solution:")
            print("   Start:  Gradio interface launches")
            print("   Use:    Gradio buttons and text inputs")
            print("   Stop:   Close Gradio window or Ctrl+C")
            print("\n" + "="*60 + "\n")
            
            # Create and launch Gradio app
            app = GradioDemoApp()
            interface = app.build_interface()
            
            # Launch in blocking mode (this becomes the main thread)
            interface.launch(
                server_name="127.0.0.1",
                server_port=7860,
                share=False,
                inbrowser=True  # Automatically open browser
            )
        except ImportError:
            print("⚠️  Gradio not available, running engine only")
            print("   Install Gradio: pip install gradio")
            # Run engine in background since Gradio wasn't started
            engine.run()
        except Exception as e:
            print(f"⚠️  Could not start Gradio: {e}")
            # Run engine in background since Gradio failed to start
            engine.run()
    else:
        # No Gradio requested, run engine directly
        engine.run()
