"""Interruption manager with sensitivity-aware logic."""
import time
import threading
from typing import Tuple
from config import (
    INTERRUPT_DEBOUNCE_MS,
    INTERRUPTION_SENSITIVITY,
    MIN_WORDS_FOR_INTERRUPT,
    TRANSCRIPTION_MODE,
)


class InterruptionManager:
    """Manages interruption detection with sensitivity control."""
    
    def __init__(self):
        self.last_interrupt_time = 0
        self.sensitivity = INTERRUPTION_SENSITIVITY
        self.transcription_mode = TRANSCRIPTION_MODE
    
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
    
    def set_sensitivity(self, sensitivity: float) -> None:
        """Set interruption sensitivity (0.0 = strict, 1.0 = responsive)."""
        self.sensitivity = max(0.0, min(1.0, sensitivity))
