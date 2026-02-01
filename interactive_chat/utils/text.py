"""Utility functions for text processing."""
from config import (
    TRAILING_CONJUNCTIONS,
    OPEN_ENDED_PREFIXES,
    QUESTION_LEADINS,
    SELF_REPAIR_MARKERS,
    FILLER_ENDINGS,
)


def lexical_bias(text: str) -> float:
    """Calculate lexical bias score for turn-taking confidence."""
    if not text:
        return 0.0
    
    t = text.lower().strip()
    words = t.split()
    score = 0.0
    
    if words and words[-1] in TRAILING_CONJUNCTIONS:
        score -= 1.0
    if any(t.startswith(p) for p in OPEN_ENDED_PREFIXES):
        score -= 0.6
    if any(t.startswith(q) for q in QUESTION_LEADINS):
        score -= 0.5
    if any(m in t[-20:] for m in SELF_REPAIR_MARKERS):
        score -= 0.4
    if words and words[-1] in FILLER_ENDINGS:
        score -= 0.7
    
    return score


def energy_decay_score(energy_history: list) -> float:
    """Calculate energy decay score for turn-taking."""
    import numpy as np
    
    if len(energy_history) < 5:
        return 0.0
    
    x = np.arange(len(energy_history))
    y = np.array(energy_history)
    slope = np.polyfit(x, y, 1)[0]
    
    return 0.8 if slope < -0.00015 else 0.0
