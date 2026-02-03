# Copywriting: Voice & Tone Guidelines

When generating text, adhere to this brand persona.

## Brand Personality Keywords
* Technical but accessible
* Conversational and natural
* Real-time and responsive
* Precision-focused
* Developer-friendly

## Grammar & Mechanics Rules
* **Headings:** Use Title Case for main headings (H1, H2). Use sentence case for subheadings (H3+).
* **Punctuation:** Use periods for complete sentences. Avoid exclamation points except in user-facing logs for emphasis.
* **Clarity:** Prefer active voice. Use present tense for real-time actions ("AI is speaking" not "AI was speaking").
* **Technical Terms:** Define on first use, then use consistently (e.g., "Voice Activity Detection (VAD)").
* **Code References:** Always use backticks for code elements, file names, and technical terms.

## Logging Style
* **Emoji Prefixes:** Use consistent emoji for log categories:
  - 🎤 User speech/microphone
  - 🤖 AI responses/TTS
  - ⚡ Interruptions
  - 🛑 Safeguards/rejections
  - ⏱️ Timing/latency
  - 📊 Analytics
* **Format:** `[EMOJI] [CONTEXT]: [MESSAGE]` (e.g., `🎤 TURN START: Human speaking`)
* **Conciseness:** Keep logs single-line, scannable at a glance

## Documentation Style
* **Architecture Docs:** Lead with "Purpose" and "Key Responsibilities" sections
* **Code Comments:** Explain *why*, not *what* (code should be self-documenting)
* **Examples:** Provide concrete code snippets with realistic values
* **Metrics:** Always include units (ms, Hz, samples, tokens)

## Terminology Guide

| Do Not Use | Use Instead | Context |
| :--- | :--- | :--- |
| "Utilize" | "Use" | General |
| "In order to..." | "To..." | General |
| "Speech recognition" | "ASR" or "Automatic Speech Recognition" | After first definition |
| "Text-to-speech" | "TTS" | After first definition |
| "Voice detection" | "VAD" or "Voice Activity Detection" | Technical contexts |
| "Conversation" | "Turn" | When referring to single exchange |
| "Stop talking" | "End turn" | State machine language |
| "Cut off" | "Interrupt" | User action |
| "Timeout" | "Safety timeout" | When referring to forced turn end |
| "Latency" | "Latency (ms)" | Always include units |
| "Model" | Specific name (e.g., "Silero VAD", "Faster-Whisper") | When possible |

## Persona-Specific Language
When writing instructions for AI personas (e.g., IELTS examiner, language tutor):
* Use second person ("You are...") for system prompts
* Be directive and specific about behavior
* Include example phrases the AI should use
* Specify authority mode and interruption behavior explicitly
