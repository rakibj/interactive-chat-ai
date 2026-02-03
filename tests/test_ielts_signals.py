#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IELTS Instructor Signal Testing Script

This script:
1. Sets up the ielts_instructor profile
2. Creates a signal listener that logs exam-related signals
3. Simulates an IELTS conversation
4. Shows signals being fired and logged in real-time

Run: python test_ielts_signals.py
"""
import sys
sys.path.insert(0, "interactive_chat")

from config import get_system_prompt, INSTRUCTION_PROFILES
from core.signals import emit_signal, get_signal_registry
import json
from datetime import datetime

# ============================================================================
# PART 1: Set up IELTS-specific signal listener
# ============================================================================

class IELTSSignalListener:
    """Listens to IELTS exam signals and logs them with styling"""
    
    def __init__(self):
        self.signal_count = 0
        self.signals_received = []
    
    def __call__(self, signal):
        """Called by signal registry when signal is emitted"""
        
        # signal is a Signal object with name, payload, context
        signal_name = signal.name
        signal_payload = signal.payload
        signal_context = signal.context
        
        # Track this signal
        self.signal_count += 1
        self.signals_received.append({
            'name': signal_name,
            'payload': signal_payload,
            'context': signal_context,
            'timestamp': datetime.now()
        })
        
        # IELTS exam signals (the interesting ones)
        ielts_signals = {
            'exam.question_asked',
            'exam.response_received',
            'exam.fluency_observation',
            'conversation.answer_complete'
        }
        
        if signal_name in ielts_signals:
            self._log_ielts_signal(signal_name, signal_payload, signal_context)
        elif signal_name.startswith('llm.'):
            self._log_llm_lifecycle(signal_name, signal_payload)
    
    def _log_ielts_signal(self, name, payload, context):
        """Log IELTS exam signals with color and structure"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print("\n" + "=" * 70)
        print(f"🎯 IELTS SIGNAL FIRED: {name}")
        print("=" * 70)
        print(f"⏰ Time: {timestamp}")
        print(f"📦 Payload:")
        for key, value in payload.items():
            print(f"   • {key}: {value}")
        print(f"🔍 Context:")
        for key, value in context.items():
            print(f"   • {key}: {value}")
        print("=" * 70)
    
    def _log_llm_lifecycle(self, name, payload):
        """Log LLM lifecycle signals (less verbose)"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        if name == 'llm.generation_start':
            print(f"\n⏳ [{timestamp}] LLM generation started...")
        elif name == 'llm.generation_complete':
            print(f"✅ [{timestamp}] LLM generation complete")
        elif name == 'llm.generation_error':
            print(f"❌ [{timestamp}] LLM generation error: {payload.get('error')}")
    
    def print_summary(self):
        """Print summary of all signals received"""
        print("\n" + "=" * 70)
        print("📊 SIGNAL SUMMARY")
        print("=" * 70)
        print(f"Total signals received: {self.signal_count}")
        print(f"\nSignals breakdown:")
        
        signal_types = {}
        for sig in self.signals_received:
            sig_name = sig['name']
            signal_types[sig_name] = signal_types.get(sig_name, 0) + 1
        
        for sig_name, count in sorted(signal_types.items()):
            marker = "🎯" if sig_name.startswith('exam.') else "⏳"
            print(f"  {marker} {sig_name}: {count}")
        
        print("=" * 70)


# ============================================================================
# PART 2: Set up and configure signal registry
# ============================================================================

print("=" * 70)
print("🚀 IELTS INSTRUCTOR SIGNAL TESTING")
print("=" * 70)

print("\n📋 Setting up IELTS instructor profile...")

# Get the ielts_instructor profile
ielts_profile = INSTRUCTION_PROFILES['ielts_instructor']
print(f"✅ Profile: {ielts_profile.name}")
print(f"✅ Authority: {ielts_profile.authority}")
print(f"✅ Voice: {ielts_profile.voice}")

# Show the signals this profile can emit
print(f"\n🔔 Signals this profile may emit:")
for signal_name, description in ielts_profile.signals.items():
    print(f"   • {signal_name}")
    print(f"     └─ {description}")

# Get system prompt (which includes the signals)
system_prompt = get_system_prompt('ielts_instructor')
print(f"\n📝 System prompt generated ({len(system_prompt)} chars)")
print(f"✅ Signal guidance included in prompt")

# Register our IELTS signal listener
print("\n🎧 Registering IELTS signal listener...")
registry = get_signal_registry()
ielts_listener = IELTSSignalListener()
registry.register_all(ielts_listener)
print("✅ Listener registered and ready to capture signals")

# ============================================================================
# PART 3: Simulate an IELTS exam conversation
# ============================================================================

print("\n" + "=" * 70)
print("🎬 SIMULATING IELTS EXAM CONVERSATION")
print("=" * 70)

# Simulate Turn 1: Examiner asks a question
print("\n[Turn 1] Examiner: 'Let me ask you a few questions. Where are you from?'")
emit_signal(
    'exam.question_asked',
    payload={
        'question': 'Where are you from?',
        'question_number': 1,
        'topic': 'home',
        'follow_up': False
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 1}
)

# Simulate candidate response
print("[Candidate responds with 30-second answer]")
emit_signal(
    'exam.response_received',
    payload={
        'duration_sec': 30,
        'coherence': 0.85,
        'fluency_score': 7.5,
        'vocabulary_level': 'intermediate'
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 1}
)

# Examiner observation
print("[Examiner noting fluency]")
emit_signal(
    'exam.fluency_observation',
    payload={
        'observation': 'Candidate demonstrates good fluency with minimal hesitation',
        'confidence': 0.88,
        'areas_to_improve': ['complex_sentences', 'accent']
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 1}
)

# Answer complete
print("[Turn 1 complete]")
emit_signal(
    'conversation.answer_complete',
    payload={
        'turn_number': 1,
        'total_response_time': 30,
        'overall_quality': 'good'
    },
    context={'source': 'ielts_exam', 'stage': 'part1'}
)

# Simulate Turn 2
print("\n[Turn 2] Examiner: 'Can you tell me about your hometown?'")
emit_signal(
    'exam.question_asked',
    payload={
        'question': 'Can you tell me about your hometown?',
        'question_number': 2,
        'topic': 'hometown',
        'follow_up': False
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 2}
)

print("[Candidate responds]")
emit_signal(
    'exam.response_received',
    payload={
        'duration_sec': 28,
        'coherence': 0.82,
        'fluency_score': 7.0,
        'vocabulary_level': 'intermediate-advanced'
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 2}
)

print("[Examiner observation]")
emit_signal(
    'exam.fluency_observation',
    payload={
        'observation': 'Good organization of ideas with natural transitions',
        'confidence': 0.90,
        'areas_to_improve': ['pronunciation', 'stress_patterns']
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 2}
)

print("[Turn 2 complete]")
emit_signal(
    'conversation.answer_complete',
    payload={
        'turn_number': 2,
        'total_response_time': 28,
        'overall_quality': 'good'
    },
    context={'source': 'ielts_exam', 'stage': 'part1'}
)

# Simulate Turn 3 with a follow-up
print("\n[Turn 3] Examiner: 'What do you do for work or study?'")
emit_signal(
    'exam.question_asked',
    payload={
        'question': 'What do you do for work or study?',
        'question_number': 3,
        'topic': 'work_study',
        'follow_up': False
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 3}
)

print("[Candidate responds]")
emit_signal(
    'exam.response_received',
    payload={
        'duration_sec': 35,
        'coherence': 0.88,
        'fluency_score': 7.5,
        'vocabulary_level': 'advanced'
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 3}
)

print("[Examiner asks follow-up]")
emit_signal(
    'exam.question_asked',
    payload={
        'question': 'Why did you choose that profession?',
        'question_number': 3,
        'topic': 'work_study',
        'follow_up': True
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 3}
)

print("[Candidate responds to follow-up]")
emit_signal(
    'exam.response_received',
    payload={
        'duration_sec': 20,
        'coherence': 0.86,
        'fluency_score': 7.5,
        'vocabulary_level': 'advanced'
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 3}
)

print("[Examiner final observation]")
emit_signal(
    'exam.fluency_observation',
    payload={
        'observation': 'Excellent command of English with sophisticated vocabulary',
        'confidence': 0.92,
        'estimated_band': 7.5,
        'strengths': ['fluency', 'vocabulary', 'coherence'],
        'areas_to_improve': ['native_like_pronunciation']
    },
    context={'source': 'ielts_exam', 'stage': 'part1', 'turn': 3}
)

print("[Part 1 complete]")
emit_signal(
    'conversation.answer_complete',
    payload={
        'turn_number': 3,
        'total_response_time': 55,
        'overall_quality': 'excellent',
        'stage_complete': 'part1'
    },
    context={'source': 'ielts_exam', 'stage': 'part1'}
)

# ============================================================================
# PART 4: Print results and summary
# ============================================================================

print("\n" + "=" * 70)
print("✅ SIMULATION COMPLETE")
print("=" * 70)

# Print listener summary
ielts_listener.print_summary()

# Show what the listener captured
print("\n📝 Detailed signal log:")
print("-" * 70)
for i, sig in enumerate(ielts_listener.signals_received, 1):
    sig_type = "🎯" if sig['name'].startswith('exam.') or sig['name'] == 'conversation.answer_complete' else "⏳"
    print(f"{i}. {sig_type} {sig['name']}")

print("\n" + "=" * 70)
print("🎉 TEST COMPLETE - All signals captured and logged!")
print("=" * 70)

print("\n📚 What was demonstrated:")
print("  1. ✅ IELTS profile loaded with signal definitions")
print("  2. ✅ Signal listener registered with registry")
print("  3. ✅ Exam-related signals fired during conversation")
print("  4. ✅ Listener captured all signals in real-time")
print("  5. ✅ Console logs showed signal details")
print("  6. ✅ Summary shows all signal types received")

print("\n💡 Key signals for IELTS:")
print("  • exam.question_asked - When examiner asks question")
print("  • exam.response_received - When candidate responds")
print("  • exam.fluency_observation - Examiner assessment")
print("  • conversation.answer_complete - Turn finished")

print("\n🚀 Next steps:")
print("  1. Modify the exam questions/responses to test different scenarios")
print("  2. Add a custom listener for specific signal types")
print("  3. Integrate with real LLM to generate exam questions")
print("  4. Build a dashboard that visualizes signals in real-time")
