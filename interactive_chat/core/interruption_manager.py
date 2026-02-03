"""DEPRECATED: Interruption logic has been moved to event_driven_core.Reducer.

This module is kept for reference but is no longer used. All interruption detection
logic (energy-based, speech-based, sensitivity levels) is now handled in the
centralized Reducer.reduce() function via _check_interruption() method.

See: core/event_driven_core.py, Reducer._check_interruption() and Reducer.reduce()
"""
import time
from typing import Tuple, Optional
from config import (
    INTERRUPT_DEBOUNCE_MS,
    INTERRUPTION_SENSITIVITY,
    MIN_WORDS_FOR_INTERRUPT,
)


class InterruptionManager:
    """Manages interruption detection and authority permissions."""
    
    def __init__(self):
        self.last_interrupt_time = 0
        self.sensitivity = INTERRUPTION_SENSITIVITY
        self.authority = "human"  # Default authority mode
    
    def set_profile_settings(self, sensitivity: float, authority: str) -> None:
        """Update settings from active profile."""
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        self.authority = authority
        
    def can_listen_continuously(self, ai_speaking: bool) -> bool:
        """
        Determine if the system should be listening to the microphone.
        
        In 'ai' authority mode, we close the mic (effectively) while AI is speaking
        to prevent any interruptions or noise processing.
        """
        if self.authority == "ai" and ai_speaking:
            return False
        return True

    def is_turn_processing_allowed(self, ai_speaking: bool) -> bool:
        """
        Determine if we should process a completed turn.
        
        SAFEGUARD: In 'ai' authority mode, never process user speech if AI is speaking.
        """
        if self.authority == "ai" and ai_speaking:
            return False
        return True
    
    def should_interrupt(
        self,
        ai_speaking: bool,
        current_time: float,
        energy_condition: bool,
        detected_words: str = "",
    ) -> Tuple[bool, str]:
        """
        Determine if human should interrupt AI.
        
        Returns:
            (should_interrupt, reason_string)
        """
        # 1. Authority Check: If AI has authority, NO interruptions allowed (unless we stay permissive for 'Stop')
        # CURRENT IMPL: logical deafness in main loop usually prevents us getting here in 'ai' mode,
        # but as a safeguard:
        if self.authority == "ai":
            return False, "authority is ai"

        now_ms = current_time * 1000
        
        # Only consider interruption when AI is actually speaking
        if not ai_speaking:
            return False, "AI not speaking"
        
        # Debounce repeated interruptions
        if now_ms - self.last_interrupt_time <= INTERRUPT_DEBOUNCE_MS:
            return False, "debounce"
        
        word_count = len(detected_words.split()) if detected_words else 0
        speech_condition = word_count >= MIN_WORDS_FOR_INTERRUPT
        
        should_interrupt = False
        reason = ""
        
        if self.sensitivity >= 0.9:
            # Pure energy mode
            should_interrupt = energy_condition
            reason = f"energy spike (sustained={energy_condition})"
        
        elif self.sensitivity <= 0.1:
            # Strict speech mode
            should_interrupt = speech_condition
            reason = f"speech detected: '{detected_words}' ({word_count} words)"
        
        else:
            # Hybrid mode
            if not energy_condition:
                should_interrupt = False
                reason = "no energy spike"
            else:
                if speech_condition:
                    should_interrupt = True
                    reason = f"energy + speech '{detected_words}'"
                else:
                    should_interrupt = self.sensitivity > 0.5
                    if should_interrupt:
                        reason = f"energy-only (sensitivity={self.sensitivity:.1f})"
                    else:
                        reason = f"energy but no speech (sensitivity={self.sensitivity:.1f})"
        
        if should_interrupt:
            self.last_interrupt_time = now_ms
        
        return should_interrupt, reason

