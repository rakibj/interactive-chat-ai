"""Analytics module for conversation behavior tracking."""
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime


@dataclass
class TurnAnalytics:
    """Structured data for a single conversation turn."""
    
    # Metadata
    turn_id: int
    timestamp: float
    profile_name: str
    human_speech_duration_sec: float
    ai_speech_duration_sec: float
    silence_before_end_ms: float
    interrupt_attempts: int
    interrupts_accepted: int
    interrupts_blocked: int
    interrupt_trigger_reasons: List[str]
    end_reason: str  # "silence", "confidence", "safety_timeout", "forced_cutoff"
    authority_mode: str
    sensitivity_value: float
    partial_transcript_lengths: List[int]
    final_transcript_length: int
    confidence_score_at_cutoff: float
    transcription_ms: float
    llm_generation_ms: float
    total_latency_ms: float
    human_transcript: str
    ai_transcript: str
    transcript_timestamp: float  # When turn was processed
    
    # Optional: Current phase if using PhaseProfile, else None (NEW)
    phase_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class SessionAnalytics:
    """Manages analytics for a conversation session."""
    
    def __init__(self, profile_name: str, logs_dir: Path):
        self.profile_name = profile_name
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Generate session filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = f"session_{timestamp}"
        self.jsonl_path = self.logs_dir / f"{self.session_id}.jsonl"
        self.summary_path = self.logs_dir / f"{self.session_id}_summary.json"
        
        # Session tracking
        self.session_start = time.time()
        self.turns: List[TurnAnalytics] = []
        
        print(f"📊 Analytics enabled: {self.jsonl_path.name}")
    
    def log_turn(self, analytics: TurnAnalytics) -> None:
        """Append turn analytics to JSONL file."""
        self.turns.append(analytics)
        
        # Write to JSONL (append mode)
        with open(self.jsonl_path, 'a', encoding='utf-8') as f:
            json.dump(analytics.to_dict(), f)
            f.write('\n')
    
    def generate_summary(self) -> Dict:
        """Compute session summary statistics."""
        if not self.turns:
            return {}
        
        session_end = time.time()
        total_turns = len(self.turns)
        
        # Timing aggregates
        avg_human_speech = sum(t.human_speech_duration_sec for t in self.turns) / total_turns
        avg_ai_speech = sum(t.ai_speech_duration_sec for t in self.turns) / total_turns
        avg_silence = sum(t.silence_before_end_ms for t in self.turns) / total_turns
        
        # Interruption metrics
        total_interrupt_attempts = sum(t.interrupt_attempts for t in self.turns)
        total_interrupts_accepted = sum(t.interrupts_accepted for t in self.turns)
        interrupt_acceptance_rate = (
            total_interrupts_accepted / total_interrupt_attempts 
            if total_interrupt_attempts > 0 else 0.0
        )
        
        # End reason distribution
        end_reason_dist = {}
        for turn in self.turns:
            reason = turn.end_reason
            end_reason_dist[reason] = end_reason_dist.get(reason, 0) + 1
        
        # Latency aggregates
        avg_transcription = sum(t.transcription_ms for t in self.turns) / total_turns
        avg_llm_generation = sum(t.llm_generation_ms for t in self.turns) / total_turns
        avg_total_latency = sum(t.total_latency_ms for t in self.turns) / total_turns
        
        summary = {
            "session_id": self.session_id,
            "session_start": self.session_start,
            "session_end": session_end,
            "session_duration_sec": session_end - self.session_start,
            "profile_name": self.profile_name,
            "total_turns": total_turns,
            
            # Timing
            "avg_human_speech_sec": round(avg_human_speech, 2),
            "avg_ai_speech_sec": round(avg_ai_speech, 2),
            "avg_silence_before_end_ms": round(avg_silence, 1),
            
            # Interruptions
            "total_interrupt_attempts": total_interrupt_attempts,
            "total_interrupts_accepted": total_interrupts_accepted,
            "interrupt_acceptance_rate": round(interrupt_acceptance_rate, 2),
            
            # Turn decisions
            "end_reason_distribution": end_reason_dist,
            
            # Latency
            "avg_transcription_ms": round(avg_transcription, 1),
            "avg_llm_generation_ms": round(avg_llm_generation, 1),
            "avg_total_latency_ms": round(avg_total_latency, 1),
        }
        
        return summary
    
    def save_summary(self) -> None:
        """Generate and save session summary to JSON."""
        summary = self.generate_summary()
        
        if summary:
            with open(self.summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            
            print(f"\n📊 Session Summary:")
            print(f"   Total turns: {summary['total_turns']}")
            print(f"   Avg latency: {summary['avg_total_latency_ms']:.0f}ms")
            print(f"   Interrupt rate: {summary['interrupt_acceptance_rate']:.0%}")
            print(f"   Summary saved: {self.summary_path.name}")
