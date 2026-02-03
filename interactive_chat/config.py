"""Centralized configuration for interactive chat system."""
import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

# Paths
PROJECT_ROOT = Path(r"D:\Work\Projects\AI\interactive-chat-ai")
MODELS_ROOT = PROJECT_ROOT / "models"

# Audio Configuration
SAMPLE_RATE = 16000
VAD_MIN_SAMPLES = 512
VOSK_MIN_SAMPLES = 3200  # 0.2 sec @ 16kHz
POCKET_SAMPLE_RATE = 24000

# Turn-taking Configuration
PAUSE_MS = 600
END_MS = 1200
SAFETY_TIMEOUT_MS = 2500
ENERGY_FLOOR = 0.015
WHISPER_WINDOW_SEC = 3.0
CONFIDENCE_THRESHOLD = 1.2
INTERRUPT_DEBOUNCE_MS = 250

# ASR Configuration
# Real-time ASR: Uses Vosk for low-latency streaming partials (closed-caption updates)
VOSK_MODEL_PATH = str(MODELS_ROOT / "vosk-model-small-en-us-0.15")

# Turn-end ASR: Options for final transcription
# - "local": WhisperLocalASR (local Whisper model, slower but free)
# - "cloud": WhisperCloudASR (OpenAI API, requires OPENAI_API_KEY, faster and more accurate)
TURN_END_ASR_MODE = "cloud"  # Choose "local" or "cloud"
WHISPER_MODEL_PATH = str(MODELS_ROOT / "whisper" / "distil-small.en")
WHISPER_CLOUD_MODEL = "gpt-4o-mini-transcribe"  # For cloud: gpt-4o-mini-transcribe, gpt-4o-transcribe

# LLM Configuration
LLM_BACKEND = "groq"  # Options: "local", "groq", "deepseek", "openai"
GGUF_MODEL_PATH = str(MODELS_ROOT / "llm" / "qwen2.5-3b-instruct-q5_k_m.gguf")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

OPENAI_BASE_URL = "https://api.openai.com/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

OPENAI_MODEL = "gpt-4o-mini"
GROQ_MODELS = {
    "best": "llama-3.1-70b-versatile",
    "fast": "llama-3.1-8b-instant",
    "cheap": "mixtral-8x7b-32768",
}
GROQ_MODEL = GROQ_MODELS["fast"]
DEEPSEEK_MODEL = "deepseek-chat"

# TTS Configuration
TTS_MODE = "pocket"  # Options: "pocket" (neural) or "powershell" (system)
POCKET_VOICE = "alba"  # Options: alba, marius, javert, jean, fantine, cosette

# Interruption Configuration
INTERRUPTION_SENSITIVITY = 0.0  # 0.0 = strict speech, 1.0 = energy-only
MIN_WORDS_FOR_INTERRUPT = 1

# Conversation Memory
MAX_MEMORY_TURNS = 24


class InstructionProfile(BaseModel):
    """Pydantic model for instruction profile configuration.
    
    Can be used standalone or as part of a PhaseProfile.
    When part of a PhaseProfile, additional context will be injected.
    """
    name: str
    start: str
    voice: str
    max_tokens: int
    temperature: float
    pause_ms: int
    end_ms: int
    safety_timeout_ms: int
    interruption_sensitivity: float
    authority: str  # "ai" (closed mic when AI speaking) or "human" (open mic always)
    human_speaking_limit_sec: Optional[int] = None
    acknowledgments: List[str] = []
    instructions: str
    signals: dict[str, str] = {}  # Signal name -> description mapping for profile

    class Config:
        frozen = True  # Make instances immutable


class PhaseTransition(BaseModel):
    """Defines a transition between two phases based on signal triggers.
    
    Transitions are checked after each turn when signals are emitted.
    """
    from_phase: str  # Phase ID to transition from
    to_phase: str    # Phase ID to transition to
    trigger_signals: List[str]  # Signal names that can trigger this transition
    require_all: bool = False   # If True, all signals must be received; if False, any one triggers
    
    class Config:
        frozen = True


class PhaseProfile(BaseModel):
    """Container for multi-phase conversations with deterministic transitions.
    
    PhaseProfiles orchestrate multiple InstructionProfiles, passing additional
    context to each phase and defining signal-based transitions between them.
    
    Example use cases:
    - IELTS exam (greeting → part1 → part2 → part3 → closing)
    - Sales call (opening → discovery → pitch → objection handling → close)
    - Customer support (intake → diagnosis → solution → verification → farewell)
    """
    name: str                                        # Display name for the phase profile
    phases: dict[str, InstructionProfile]            # phase_id -> InstructionProfile mapping
    transitions: List[PhaseTransition]               # Ordered list of possible transitions
    initial_phase: str                               # Starting phase ID
    phase_context: Optional[str] = None              # Global context for all phases
    per_phase_context: Optional[dict[str, str]] = None  # Phase-specific additional context
    
    class Config:
        frozen = True
    
    def get_phase(self, phase_id: str) -> Optional[InstructionProfile]:
        """Get an InstructionProfile by phase ID."""
        return self.phases.get(phase_id)
    
    def get_phase_context(self, phase_id: str) -> str:
        """Get the full context for a specific phase (global + phase-specific)."""
        context_parts = []
        
        if self.phase_context:
            context_parts.append(self.phase_context)
        
        if self.per_phase_context and phase_id in self.per_phase_context:
            context_parts.append(self.per_phase_context[phase_id])
        
        return "\n\n".join(context_parts) if context_parts else ""
    
    def find_transition(self, current_phase: str, emitted_signals: List[str]) -> Optional[str]:
        """Find the next phase based on current phase and emitted signals.
        
        Returns the next phase_id if a transition is triggered, None otherwise.
        """
        for transition in self.transitions:
            if transition.from_phase != current_phase:
                continue
            
            if transition.require_all:
                # All signals must be present
                if all(sig in emitted_signals for sig in transition.trigger_signals):
                    return transition.to_phase
            else:
                # Any one signal triggers
                if any(sig in emitted_signals for sig in transition.trigger_signals):
                    return transition.to_phase
        
        return None


# Conversation Configuration
CONVERSATION_START = "human"  # Options: "human" or "ai" (can be overridden per profile)
ACTIVE_PROFILE = "negotiator"  # Select which profile to use
ACTIVE_PHASE_PROFILE: Optional[str] = None  # If set, use a PhaseProfile instead of single profile
ACTIVE_PHASE_PROFILE = "ielts_full_exam"  # Example: set to "ielts_full_exam" to use that profile
# simple_test, ielts_full_exam, sales_call, customer_support, language_tutor, negotiation_scenario

# Default LLM Parameters (can be overridden per profile)
LLM_MAX_TOKENS = 80
LLM_TEMPERATURE = 0.5

# Default Turn-taking Parameters (can be overridden per profile)
PAUSE_MS = 600
END_MS = 1200
SAFETY_TIMEOUT_MS = 2500
INTERRUPTION_SENSITIVITY = 0.0  # 0.0 = strict speech, 1.0 = energy-only

# Default TTS Voice (can be overridden per profile)
POCKET_VOICE = "alba"  # Options: alba, marius, javert, jean, fantine, cosette

# System Prompt Base (general behavior)
SYSTEM_PROMPT_BASE = """
You are in a live spoken conversation.
- Respond naturally and conversationally.
- Keep responses concise (1-2 sentences typically).
- No disclaimers or meta-commentary.
- No emojis or excessive filler.

OPTIONAL STRUCTURED SIGNALS (FOR THE SYSTEM):

- You may optionally include structured signals at the VERY END of your response.
- Signals describe observations about the conversation or user intent.
- Signals do NOT perform actions.
- If you are unsure, omit the signals entirely.
- The spoken response must ALWAYS come first.

IMPORTANT: Prefix profile-specific signals with "custom." (e.g., "custom.user_action").

FORMAT:

Wrap signals in <signals></signals> tags.
The content inside must be valid JSON.

Each signal:
- Uses a string key (namespaced, e.g. "intake.user_data_collected" or "custom.user_action").
- Has a JSON object as its value.
- May include parameters such as confidence, fields, or notes.

Do NOT include any text outside JSON inside <signals>.

EXAMPLES:

Example 1 — Generic custom signal:

That's an interesting observation.

<signals>
{
  "custom.user_observation": {
    "confidence": 0.88,
    "category": "relevant"
  }
}
</signals>

---

Example 2 — User data collected:

Thanks, I've got everything I need.

<signals>
{
  "intake.user_data_collected": {
    "confidence": 0.92,
    "fields": ["name", "email"]
  }
}
</signals>

---

Example 3 — User appears confused:

I'm not entirely sure what you're asking.

<signals>
{
  "conversation.user_confused": {
    "confidence": 0.81
  }
}
</signals>

---

Example 4 — Answer complete:

That covers the main points I wanted to discuss.

<signals>
{
  "conversation.answer_complete": {
    "confidence": 0.84,
    "needs_followup": true
  }
}
</signals>

---

Example 5 — Multiple signals at once:

Yes, I understand your concern completely.

<signals>
{
  "custom.user_acknowledged": {
    "confidence": 0.9
  },
  "conversation.answer_complete": {
    "confidence": 0.77
  }
}
</signals>

---

Example 6 — No signals (perfectly valid):

That sounds interesting. Could you tell me more?
"""

# Custom Instruction Profiles with per-profile settings
INSTRUCTION_PROFILES = {
    "negotiator": InstructionProfile(
        name="Negotiation (Buyer)",
        start="human",
        voice="alba",
        max_tokens=80,
        temperature=0.5,
        pause_ms=600,
        end_ms=1200,
        safety_timeout_ms=2500,
        interruption_sensitivity=0.6,
        authority="default",
        human_speaking_limit_sec=5,
        acknowledgments=[
            "Okay.",
            "Noted.",
        ],
        signals={
            "negotiation.counteroffer_made": "User made a counter-offer with a price or term.",
            "negotiation.objection_raised": "User raised an objection or concern about the offer.",
            "conversation.answer_complete": "User has completed their turn and is waiting for a response.",
        },
        instructions="""ROLE: You are the BUYER in a negotiation.

KEY RULE: Respond in ONE LINE ONLY. Never more than a single sentence.

OBJECTIVE: Pay as little as possible.

BEHAVIOR: Push back on price, question value claims, counteroffer firmly. Stay in character.

TONE: Confident, skeptical.

IMPORTANT: Keep every response to exactly one line.""",
    ),
    
    "ielts_instructor": InstructionProfile(
        name="IELTS Speaking Instructor (Part 1)",
        start="ai",
        voice="jean",
        max_tokens=120,
        temperature=0.6,
        pause_ms=800,
        end_ms=1500,
        safety_timeout_ms=3500,
        interruption_sensitivity=0.3,
        authority="ai",
        human_speaking_limit_sec=5,
        acknowledgments=[
            "Thank you.",
            "Good.",
            "I see.",
            "Excellent.",
            "Right.",
            "Got it.",
        ],
        signals={
            "exam.question_asked": "Examiner has asked a Part 1 question.",
            "exam.response_received": "Candidate has responded to the question.",
            "exam.fluency_observation": "Examiner made an observation about candidate fluency.",
            "conversation.answer_complete": "Candidate has completed their answer.",
        },
        instructions="""ROLE: IELTS Instructor (Part 1 only).

KEY RULE: One question or brief comment per turn. NEVER more than one sentence.

TASK: Ask personal questions on familiar topics (home, family, hobbies, work, studies).

BEHAVIOR: Ask one question at a time. Keep it short and clear. Do NOT transition to Part 2 or 3.

TONE: Professional, encouraging.

IMPORTANT: Every response must be exactly one sentence only.""",
    ),
    
    "confused_customer": InstructionProfile(
        name="Confused Customer",
        start="human",
        voice="marius",
        max_tokens=90,
        temperature=0.7,
        pause_ms=700,
        end_ms=1400,
        safety_timeout_ms=2800,
        interruption_sensitivity=0,
        authority="human",
        human_speaking_limit_sec=5,
        acknowledgments=[
            "I understand.",
            "Okay, let me clarify.",
            "Right, I get it.",
            "So basically...",
            "Got it.",
            "Let me check that.",
        ],
        signals={
            "conversation.user_confused": "Customer expresses confusion about a policy or process.",
            "customer_service.clarification_needed": "Customer is asking for clarification on a previous statement.",
            "conversation.answer_complete": "Customer has completed their question or concern.",
        },
        instructions="""ROLE: Confused customer trying to return an item.

KEY RULE: Respond in ONE LINE ONLY.

CHARACTERISTICS: Don't understand policy, slightly frustrated, ask clarifying questions.

OBJECTIVE: Get issue resolved.

TONE: Confused, frustrated, but reasonable.

IMPORTANT: Keep every response to one sentence.""",
    ),
    
    "technical_support": InstructionProfile(
        name="Technical Support Agent",
        start="ai",
        voice="cosette",
        max_tokens=100,
        temperature=0.4,
        pause_ms=500,
        end_ms=1000,
        safety_timeout_ms=2200,
        interruption_sensitivity=0.2,
        authority="ai",
        human_speaking_limit_sec=30,
        acknowledgments=[
            "Got it.",
            "Let me help with that.",
            "Understood.",
            "One moment.",
            "I see the issue.",
            "Okay, try that.",
        ],
        signals={
            "support.issue_identified": "Support agent has identified the customer's issue.",
            "support.solution_offered": "Agent has offered a potential solution or troubleshooting step.",
            "support.escalation_needed": "Agent has determined the issue requires escalation.",
            "conversation.answer_complete": "Agent has completed their response.",
        },
        instructions="""ROLE: Technical support agent.

KEY RULE: One question or suggestion per turn. ONE LINE ONLY.

BEHAVIOR: Ask diagnostic questions, suggest common solutions, be patient. Keep explanations simple.

TONE: Patient, knowledgeable, professional.

IMPORTANT: Every response must be a single sentence.""",
    ),
    
    "language_tutor": InstructionProfile(
        name="English Language Tutor",
        start="ai",
        voice="fantine",
        max_tokens=110,
        temperature=0.6,
        pause_ms=700,
        end_ms=1400,
        safety_timeout_ms=3000,
        interruption_sensitivity=0.1,
        authority="human",
        human_speaking_limit_sec=None,
        acknowledgments=[
            "Great!",
            "Excellent point.",
            "I see.",
            "Well said.",
            "Nice usage.",
            "Perfect.",
        ],
        signals={
            "language_learning.vocabulary_introduced": "Tutor has introduced or explained a new vocabulary word or phrase.",
            "language_learning.grammar_note": "Tutor has provided feedback or explanation on grammar usage.",
            "conversation.answer_complete": "Student has completed their response.",
        },
        instructions="""ROLE: English language tutor.

KEY RULE: Respond in ONE SENTENCE ONLY. Never more than one line.

BEHAVIOR: Ask questions, gently correct errors, encourage speaking. Keep it natural and short.

TONE: Friendly, encouraging, educational.

IMPORTANT: Keep every response to exactly one line.""",
    ),

    "curious_friend": InstructionProfile(
        name="Curious Friend",
        start="ai",
        voice="alba",
        max_tokens=95,
        temperature=0.75,
        pause_ms=750,
        end_ms=1300,
        safety_timeout_ms=2800,
        interruption_sensitivity=0.4,
        authority="human",
        human_speaking_limit_sec=None,
        acknowledgments=[
            "That's cool!",
            "Oh, interesting!",
            "I see.",
            "No way!",
            "That makes sense.",
            "Tell me more!",
        ],
        signals={
            "conversation.shared_interest": "Friend has identified a shared interest or common experience.",
            "conversation.follow_up_question": "Friend is following up naturally on something mentioned.",
            "conversation.answer_complete": "Friend has completed their turn.",
        },
        instructions="""ROLE: Curious friend in casual conversation.

KEY RULE: ONE LINE ONLY per response. Single sentence.

BEHAVIOR: Ask genuine questions, express interest, remember details. Be warm and natural.

TONE: Warm, engaged, interested.

IMPORTANT: Every response must be exactly one sentence.""",
    ),
}


# ============================================================================
# PHASE PROFILES - Multi-phase conversations with deterministic transitions
# ============================================================================

PHASE_PROFILES = {
    "ielts_full_exam": PhaseProfile(
        name="IELTS Speaking Test (Full)",
        initial_phase="greeting",
        phase_context="""CONTEXT: This is a full IELTS Speaking test simulation.
The test consists of three parts with specific timing and structure.
Maintain professional examiner demeanor throughout all phases.
Track time informally and transition when appropriate signals are detected.""",
        
        phases={
            "greeting": InstructionProfile(
                name="IELTS - Greeting",
                start="ai",
                voice="jean",
                max_tokens=60,
                temperature=0.5,
                pause_ms=800,
                end_ms=1500,
                safety_timeout_ms=3500,
                interruption_sensitivity=0.3,
                authority="ai",
                human_speaking_limit_sec=30,
                acknowledgments=["Thank you.", "Good.", "Right."],
                signals={
                    "exam.greeting_complete": "Examiner has completed greeting and ID verification.",
                },
                instructions="""IELTS test greeting - ONE LINE ONLY.

TASK: Greet warmly, ask name and ID, explain Part 1 starts next.

KEEP TO ONE SENTENCE. Then emit:
<signals>
{
  "custom.exam.greeting_complete": {}
}
</signals>"""
            ),
            
            "part1": InstructionProfile(
                name="IELTS - Part 1",
                start="ai",
                voice="jean",
                max_tokens=120,
                temperature=0.6,
                pause_ms=800,
                end_ms=1500,
                safety_timeout_ms=3500,
                interruption_sensitivity=0.3,
                authority="ai",
                human_speaking_limit_sec=45,
                acknowledgments=["Thank you.", "Good.", "I see.", "Excellent."],
                signals={
                    "exam.questions_completed": "Asked 4-5 questions, ready to transition to Part 2.",
                },
                instructions="""IELTS Part 1 - ONE LINE PER RESPONSE.

TASK: Ask one personal question at a time (home, family, work, hobbies, daily life).

After 4-5 questions, emit:
<signals>
{
  "custom.exam.questions_completed": {}
}
</signals>

Keep ALL responses to one sentence."""
            ),
            
            "part2": InstructionProfile(
                name="IELTS - Part 2",
                start="ai",
                voice="jean",
                max_tokens=150,
                temperature=0.6,
                pause_ms=1000,
                end_ms=2000,
                safety_timeout_ms=4000,
                interruption_sensitivity=0.2,
                authority="ai",
                human_speaking_limit_sec=120,
                acknowledgments=["Thank you.", "Time's up."],
                signals={
                    "exam.topic_given": "Topic card has been presented.",
                    "exam.monologue_complete": "Candidate finished 1-2 minute monologue.",
                },
                instructions="""IELTS Part 2 - ONE LINE PER RESPONSE.

TASK: Give topic card, let candidate speak 1-2 minutes, ask 1-2 follow-ups.

Example topic: "Describe a memorable trip."

When done, emit:
<signals>
{
  "custom.exam.monologue_complete": {}
}
</signals>

Keep all responses to one sentence."""
            ),
            
            "part3": InstructionProfile(
                name="IELTS - Part 3",
                start="ai",
                voice="jean",
                max_tokens=120,
                temperature=0.7,
                pause_ms=800,
                end_ms=1500,
                safety_timeout_ms=3500,
                interruption_sensitivity=0.3,
                authority="ai",
                human_speaking_limit_sec=60,
                acknowledgments=["Thank you.", "Interesting.", "I see."],
                signals={
                    "exam.discussion_complete": "Abstract discussion complete, ready to close.",
                },
                instructions="""IELTS Part 3 - ONE LINE PER RESPONSE.

TASK: Ask 3-4 abstract discussion questions on society, culture, trends, opinions.

When done, emit:
<signals>
{
  "custom.exam.discussion_complete": {}
}
</signals>

Keep every response to exactly one sentence."""
            ),
            
            "closing": InstructionProfile(
                name="IELTS - Closing",
                start="ai",
                voice="jean",
                max_tokens=60,
                temperature=0.5,
                pause_ms=800,
                end_ms=1500,
                safety_timeout_ms=3000,
                interruption_sensitivity=0.3,
                authority="ai",
                human_speaking_limit_sec=20,
                acknowledgments=["Thank you.", "Goodbye."],
                signals={
                    "exam.test_complete": "Test has concluded.",
                },
                instructions="""IELTS test closing - ONE LINE ONLY.

TASK: Thank them, say test is complete, wish good luck.

Keep to ONE SENTENCE. Then emit:
<signals>
{
  "custom.exam.test_complete": {}
}
</signals>"""
            ),
        },
        
        per_phase_context={
            "greeting": "This is the introduction phase. Be warm but efficient.",
            "part1": "This is Part 1 (Introduction and Interview). Keep questions simple and personal.",
            "part2": "This is Part 2 (Long Turn). Give them space to speak for 1-2 minutes uninterrupted.",
            "part3": "This is Part 3 (Two-way Discussion). Ask thought-provoking, abstract questions.",
            "closing": "This is the conclusion. Be brief and professional.",
        },
        
        transitions=[
            PhaseTransition(
                from_phase="greeting",
                to_phase="part1",
                trigger_signals=["custom.exam.greeting_complete"],
                require_all=False
            ),
            PhaseTransition(
                from_phase="part1",
                to_phase="part2",
                trigger_signals=["custom.exam.questions_completed"],
                require_all=False
            ),
            PhaseTransition(
                from_phase="part2",
                to_phase="part3",
                trigger_signals=["custom.exam.monologue_complete"],
                require_all=False
            ),
            PhaseTransition(
                from_phase="part3",
                to_phase="closing",
                trigger_signals=["custom.exam.discussion_complete"],
                require_all=False
            ),
        ],
    ),
    
    "sales_call": PhaseProfile(
        name="Sales Call (Discovery to Close)",
        initial_phase="opening",
        phase_context="""CONTEXT: This is a structured sales call.
You are selling a B2B SaaS product (project management software).
Your goal is to understand needs, present value, handle objections, and close.
Transition through phases based on customer signals.""",
        
        phases={
            "opening": InstructionProfile(
                name="Sales - Opening",
                start="ai",
                voice="alba",
                max_tokens=80,
                temperature=0.6,
                pause_ms=600,
                end_ms=1200,
                safety_timeout_ms=2500,
                interruption_sensitivity=0.6,
                authority="default",
                signals={
                    "sales.rapport_established": "Initial rapport built, ready for discovery.",
                },
                instructions="""Sales opening - ONE LINE ONLY.

TASK: Greet, introduce, confirm time, set agenda, build rapport.

Keep to ONE SENTENCE. Then emit:
<signals>
{
  "custom.sales.rapport_established": {}
}
</signals>"""
            ),
            
            "discovery": InstructionProfile(
                name="Sales - Discovery",
                start="ai",
                voice="alba",
                max_tokens=100,
                temperature=0.6,
                pause_ms=600,
                end_ms=1200,
                safety_timeout_ms=2500,
                interruption_sensitivity=0.6,
                authority="default",
                signals={
                    "sales.pain_points_identified": "Customer pain points identified.",
                    "sales.needs_understood": "Customer needs are clear.",
                },
                instructions="""Sales discovery - ONE LINE PER RESPONSE.

TASK: Ask about current process, identify pain points, understand goals.

When needs are clear, emit:
<signals>
{
  "custom.sales.needs_understood": {}
}
</signals>

Keep every response to one sentence."""
            ),
            
            "pitch": InstructionProfile(
                name="Sales - Pitch",
                start="ai",
                voice="alba",
                max_tokens=120,
                temperature=0.6,
                pause_ms=600,
                end_ms=1200,
                safety_timeout_ms=2500,
                interruption_sensitivity=0.6,
                authority="default",
                signals={
                    "sales.value_presented": "Value proposition presented.",
                    "sales.objection_raised": "Customer raised objection or concern.",
                },
                instructions="""Sales pitch - ONE LINE PER RESPONSE.

TASK: Connect features to pain points, focus on benefits, use their language.

If objection: emit objection_raised
If ready to close: emit value_presented

<signals>
{
  "custom.sales.value_presented": {}
}
</signals>

Keep all responses to one sentence."""
            ),
            
            "objection_handling": InstructionProfile(
                name="Sales - Objection Handling",
                start="human",
                voice="alba",
                max_tokens=100,
                temperature=0.7,
                pause_ms=600,
                end_ms=1200,
                safety_timeout_ms=2500,
                interruption_sensitivity=0.6,
                authority="default",
                signals={
                    "sales.objection_resolved": "Objection addressed satisfactorily.",
                    "sales.needs_more_info": "Customer needs more information.",
                },
                instructions="""Sales objection handling - ONE LINE PER RESPONSE.

TASK: Listen, validate, address concern. Check if resolved.

If resolved: emit objection_resolved
If more info needed: emit needs_more_info

<signals>
{
  "custom.sales.objection_resolved": {}
}
</signals>

Keep all responses to one sentence."""
            ),
            
            "close": InstructionProfile(
                name="Sales - Close",
                start="ai",
                voice="alba",
                max_tokens=80,
                temperature=0.6,
                pause_ms=600,
                end_ms=1200,
                safety_timeout_ms=2500,
                interruption_sensitivity=0.6,
                authority="default",
                signals={
                    "sales.deal_closed": "Customer agreed to next steps.",
                    "sales.follow_up_scheduled": "Follow-up meeting scheduled.",
                },
                instructions="""Sales close - ONE LINE ONLY.

TASK: Summarize value, propose next steps, schedule follow-up.

Keep to ONE SENTENCE. Then emit:
<signals>
{
  "custom.sales.follow_up_scheduled": {}
}
</signals>"""
            ),
        },
        
        transitions=[
            PhaseTransition(
                from_phase="opening",
                to_phase="discovery",
                trigger_signals=["custom.sales.rapport_established"],
                require_all=False
            ),
            PhaseTransition(
                from_phase="discovery",
                to_phase="pitch",
                trigger_signals=["custom.sales.needs_understood"],
                require_all=False
            ),
            PhaseTransition(
                from_phase="pitch",
                to_phase="objection_handling",
                trigger_signals=["custom.sales.objection_raised"],
                require_all=False
            ),
            PhaseTransition(
                from_phase="pitch",
                to_phase="close",
                trigger_signals=["custom.sales.value_presented"],
                require_all=False
            ),
            PhaseTransition(
                from_phase="objection_handling",
                to_phase="pitch",
                trigger_signals=["custom.sales.needs_more_info"],
                require_all=False
            ),
            PhaseTransition(
                from_phase="objection_handling",
                to_phase="close",
                trigger_signals=["custom.sales.objection_resolved"],
                require_all=False
            ),
        ],
    ),
    
    "simple_test": PhaseProfile(
        name="Simple Two-Question Test",
        initial_phase="question1",
        phase_context="This is a simple test of the phase system. Ask one question per phase, then transition when user answers.",
        
        phases={
            "question1": InstructionProfile(
                name="Question 1",
                start="ai",
                voice="alba",
                max_tokens=60,
                temperature=0.6,
                pause_ms=800,
                end_ms=1500,
                safety_timeout_ms=3000,
                interruption_sensitivity=0.3,
                authority="ai",
                human_speaking_limit_sec=30,
                acknowledgments=["Thank you.", "Got it.", "I see."],
                signals={
                    "test.answer_received": "User has answered the question.",
                },
                instructions="""You are conducting a simple test.

TASK: Ask the user ONE question: "What is your favorite color?"

IMPORTANT: After the user answers your question, you MUST emit ONLY this signal:
<signals>
{
  "custom.test.answer_received": {}
}
</signals>

Do NOT emit any other signals. Only emit answer_received when the user provides an answer."""
            ),
            
            "question2": InstructionProfile(
                name="Question 2",
                start="ai",
                voice="alba",
                max_tokens=60,
                temperature=0.6,
                pause_ms=800,
                end_ms=1500,
                safety_timeout_ms=3000,
                interruption_sensitivity=0.3,
                authority="ai",
                human_speaking_limit_sec=30,
                acknowledgments=["Thank you.", "Got it.", "I see."],
                signals={
                    "test.complete": "User has answered the second question.",
                },
                instructions="""You are conducting a simple test - second question.

TASK: Ask the user ONE question: "What is your favorite animal?"

IMPORTANT: After the user answers your question, you MUST emit ONLY this signal:
<signals>
{
  "custom.test.complete": {}
}
</signals>

Then thank them for participating. Do NOT emit any other signals."""
            ),
        },
        
        transitions=[
            PhaseTransition(
                from_phase="question1",
                to_phase="question2",
                trigger_signals=["custom.test.answer_received"],
                require_all=False
            ),
        ],
    ),
}


def get_profile_settings(profile_key: str = None, profile_obj: InstructionProfile = None) -> dict:
    """
    Get all settings for a profile.
    
    Args:
        profile_key: Profile name from INSTRUCTION_PROFILES. Uses ACTIVE_PROFILE if None.
        profile_obj: Direct InstructionProfile object (used for PhaseProfile phases).
    
    Returns:
        Dictionary with all profile settings.
    """
    if profile_obj:
        # Direct profile object provided (from PhaseProfile)
        profile = profile_obj
    else:
        # Load from INSTRUCTION_PROFILES
        profile_key = profile_key or ACTIVE_PROFILE
        
        if profile_key not in INSTRUCTION_PROFILES:
            raise ValueError(f"Unknown profile: {profile_key}. Available: {list(INSTRUCTION_PROFILES.keys())}")
        
        profile: InstructionProfile = INSTRUCTION_PROFILES[profile_key]
    
    return {
        "name": profile.name,
        "start": profile.start,
        "voice": profile.voice,
        "max_tokens": profile.max_tokens,
        "temperature": profile.temperature,
        "pause_ms": profile.pause_ms,
        "end_ms": profile.end_ms,
        "safety_timeout_ms": profile.safety_timeout_ms,
        "interruption_sensitivity": profile.interruption_sensitivity,
        "authority": profile.authority,
        "human_speaking_limit_sec": profile.human_speaking_limit_sec,
        "acknowledgments": profile.acknowledgments,
        "instructions": profile.instructions,
    }


def get_system_prompt(profile_key: str = None) -> str:
    """
    Get the complete system prompt for a profile.
    
    Args:
        profile_key: Profile name. Uses ACTIVE_PROFILE if None.
    
    Returns:
        Complete system prompt combining base and profile instructions.
    """
    profile_key = profile_key or ACTIVE_PROFILE
    
    if profile_key not in INSTRUCTION_PROFILES:
        raise ValueError(f"Unknown profile: {profile_key}. Available: {list(INSTRUCTION_PROFILES.keys())}")
    
    profile: InstructionProfile = INSTRUCTION_PROFILES[profile_key]
    
    # Build signal hints if profile defines signals
    # Prefix profile-specific signals with "custom." for emission
    signal_hint = ""
    if profile.signals:
        signal_hint = "\n\nSIGNALS YOU MAY EMIT:\n"
        for signal_name, signal_desc in profile.signals.items():
            # Add "custom." prefix to profile-defined signals
            prefixed_name = f"custom.{signal_name}"
            signal_hint += f"- {prefixed_name}: {signal_desc}\n"
    
    return SYSTEM_PROMPT_BASE + signal_hint + "\n\n" + profile.instructions


def get_system_prompt_with_phase_context(
    profile: InstructionProfile, 
    phase_context: str = ""
) -> str:
    """Build system prompt for a profile with optional phase context.
    
    Used when running an InstructionProfile as part of a PhaseProfile.
    The phase_context is injected between the base prompt and profile instructions.
    """
    # Build signal hints
    signal_hint = ""
    if profile.signals:
        signal_hint = "\n\nSIGNALS YOU MAY EMIT:\n"
        for signal_name, signal_desc in profile.signals.items():
            prefixed_name = f"custom.{signal_name}"
            signal_hint += f"- {prefixed_name}: {signal_desc}\n"
    
    # Inject phase context if provided
    phase_section = ""
    if phase_context:
        phase_section = f"\n\n=== PHASE CONTEXT ===\n{phase_context}\n===================\n"
    
    return SYSTEM_PROMPT_BASE + signal_hint + phase_section + "\n\n" + profile.instructions


# Backwards compatibility
SYSTEM_PROMPT = get_system_prompt()

# Turn-taking Rules
TRAILING_CONJUNCTIONS = {"and", "or", "but", "because", "so", "that", "which", "who", "when", "if", "though", "while"}
OPEN_ENDED_PREFIXES = ("i think", "i guess", "i'm not sure", "the thing is", "it depends")
QUESTION_LEADINS = ("do you think", "would you say", "is it possible", "can you")
SELF_REPAIR_MARKERS = ("i mean", "actually", "sorry", "no wait")
FILLER_ENDINGS = ("uh", "um", "like", "you know", "kind of")
