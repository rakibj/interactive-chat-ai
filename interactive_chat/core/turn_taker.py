"""DEPRECATED: Turn-taking logic has been moved to event_driven_core.Reducer.

This module is kept for reference but is no longer used. All turn-taking state
machine logic (IDLE -> SPEAKING -> PAUSING -> PROCESSING) is now handled in the
centralized Reducer.reduce() function as part of the event-driven architecture.

See: core/event_driven_core.py, Reducer.reduce()
"""
import numpy as np
from collections import deque
from typing import Tuple
from utils.text import lexical_bias, energy_decay_score
from config import (
    PAUSE_MS,
    END_MS,
    ENERGY_FLOOR,
    CONFIDENCE_THRESHOLD,
    SAFETY_TIMEOUT_MS,
)


class TurnTaker:
    """State machine for turn-taking (IDLE/SPEAKING/PAUSING)."""
    
    def __init__(self):
        self.state = "IDLE"
        self.last_voice_time = None
        self.energy_history = deque(maxlen=15)
        self.micro_spike_times = deque(maxlen=5)
        self.last_ai_interrupted = False
        
        # Profile-specific settings (can be overridden after init)
        self.pause_ms = PAUSE_MS
        self.end_ms = END_MS
        self.safety_timeout_ms = SAFETY_TIMEOUT_MS
    
    def update_energy(self, rms: float) -> None:
        """Update energy history."""
        self.energy_history.append(rms)
    
    def should_force_end(self, authority: str, elapsed_ms: float) -> bool:
        """Determine if turn should be force-ended based on authority.
        
        Args:
            authority: "human", "ai", or "default"
            elapsed_ms: Time since last voice activity
        
        Returns:
            True if turn should be force-ended
        """
        if authority == "human":
            # Human authority: Never force end
            return False
        
        # Default and AI authority: Use safety timeout
        return elapsed_ms >= self.safety_timeout_ms
    
    def process_state(
        self,
        speech_started: bool,
        sustained: bool,
        current_time: float,
        current_partial_text: str = "",
        authority: str = "default",
    ) -> Tuple[str, bool]:
        """
        Process turn-taking state machine.
        Returns: (new_state, should_end_turn)
        """
        should_end_turn = False
        
        if self.state == "IDLE":
            if speech_started or sustained:
                self.state = "SPEAKING"
                self.last_voice_time = current_time
                print("🟢 Speech started")
        
        elif self.state == "SPEAKING":
            if speech_started or sustained:
                self.last_voice_time = current_time
            else:
                elapsed_ms = (current_time - self.last_voice_time) * 1000
                if elapsed_ms >= self.pause_ms:
                    self.state = "PAUSING"
                    print(f"🟡 Pause {int(elapsed_ms)} ms")
        
        elif self.state == "PAUSING":
            elapsed_ms = (current_time - self.last_voice_time) * 1000
            
            # SAFETY TIMEOUT: Force end if taking too long (authority-aware)
            if self.should_force_end(authority, elapsed_ms):
                print(f"🔴 SAFETY TIMEOUT: Forced turn end after {elapsed_ms:.0f}ms")
                should_end_turn = True
                self.reset()
            
            # Resume speech
            elif speech_started or sustained:
                self.state = "SPEAKING"
                self.last_voice_time = current_time
                print("🟢 Speech resumed")
            
            else:
                # Calculate confidence
                confidence = self._calculate_confidence(
                    elapsed_ms,
                    current_partial_text,
                )
                
                if confidence >= CONFIDENCE_THRESHOLD:
                    print(f"🔴 Turn ended (confidence={confidence:.2f}, silence={elapsed_ms:.0f}ms)")
                    should_end_turn = True
                    self.reset()
        
        return self.state, should_end_turn
    
    def _calculate_confidence(self, elapsed_ms: float, current_partial_text: str) -> float:
        """Calculate turn-end confidence score."""
        confidence = 0.0
        
        # Primary: Silence duration
        if elapsed_ms > self.end_ms:
            confidence += 1.0
        elif elapsed_ms > (self.end_ms * 0.75):
            confidence += 0.6  # Interim confidence at 75% of end_ms
        
        # Secondary: Energy floor check
        if len(self.energy_history) >= 8:
            recent_energies = list(self.energy_history)[-8:]
            if max(recent_energies) < ENERGY_FLOOR * 1.8:
                confidence += 0.7
        elif len(self.energy_history) >= 5:
            recent_energies = list(self.energy_history)[-5:]
            if max(recent_energies) < ENERGY_FLOOR * 1.8:
                confidence += 0.4  # Partial credit for energy
        
        # Micro-spikes penalty
        if elapsed_ms < 1000:
            recent_spikes = [t for t in self.micro_spike_times if len(self.micro_spike_times) > 0]
            if len(recent_spikes) >= 2:
                confidence -= 0.5
        
        # Lexical bias from partial text
        if elapsed_ms < 900 and current_partial_text:
            confidence += lexical_bias(current_partial_text) * 0.6
        
        # AI interruption penalty
        if self.last_ai_interrupted:
            confidence -= 0.5
        
        return confidence
    
    def reset(self) -> None:
        """Reset turn-taking state."""
        self.state = "IDLE"
        self.last_voice_time = None
        self.energy_history.clear()
        self.micro_spike_times.clear()
        self.last_ai_interrupted = False
