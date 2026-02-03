# Garbage Output Fixes

## Problem Identified

The AI system was occasionally generating and speaking garbage responses like `...` or ellipsis-only output, cluttering the logs and creating poor user experience.

### Root Causes

1. **Incomplete sentence validation**: AI responses that were purely punctuation (dots, commas) were being sent to TTS without validation
2. **Empty sentences**: Whitespace-only or empty strings were passing through the validation checks
3. **End-of-stream handling**: Sentences at the end of the LLM stream (without ending punctuation) weren't being validated

## Solutions Implemented

### 1. Added `_is_valid_ai_sentence()` validation function

Location: `interactive_chat/main.py` (new method added)

This function filters out:

- Empty or whitespace-only strings
- Strings that are only punctuation marks (`.`, `,`, `!`, `?`, `;`, `:`, `…`, `-`)
- Strings with no alphanumeric characters

```python
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
```

### 2. Applied validation at sentence emission points

Two locations in `interactive_chat/main.py`:

#### Location 1: `_generate_ai_turn()` method

- Lines ~481-486: Check validation before queuing AI_SENTENCE_READY events
- Line ~492: Handle remaining sentence at end of stream with validation

#### Location 2: `_process_turn_async()` method

- Lines ~589-594: Check validation before queuing AI_SENTENCE_READY events
- Line ~600: Handle remaining sentence at end of stream with validation

### 3. Specific fixes applied

**Before:**

```python
if clean_sentence:
    self.event_queue.put(Event(EventType.AI_SENTENCE_READY, ...))
```

**After:**

```python
if clean_sentence and self._is_valid_ai_sentence(clean_sentence):
    self.event_queue.put(Event(EventType.AI_SENTENCE_READY, ...))
```

**Added end-of-stream handling:**

```python
# Handle any remaining sentence at end of stream (stream ended without period)
if current_sentence.strip() and not signals_started and self._is_valid_ai_sentence(current_sentence.strip()):
    self.event_queue.put(Event(EventType.AI_SENTENCE_READY, time.time(), "llm", {"text": current_sentence.strip()}))
```

## Results

### Before Fix

Logs showed garbage output like:

```
🤖 AI Sentence ready: ...
🤖 AI Sentence ready: (...just punctuation...)
```

### After Fix

All AI sentences now contain valid content:

```
🤖 AI Sentence ready: Good morning, and welcome to t...
🤖 AI Sentence ready: Can you please state your full...
🤖 AI Sentence ready: What do you like to do in your...
```

## Testing

- ✅ Ran full IELTS PhaseProfile simulation
- ✅ No garbage `...` outputs in logs
- ✅ All AI responses contain meaningful content
- ✅ No validation errors or edge cases

## Edge Cases Handled

1. ✅ Empty strings after signal tag stripping
2. ✅ Whitespace-only responses
3. ✅ Pure punctuation responses (e.g., "...")
4. ✅ End-of-stream responses without ending punctuation
5. ✅ Responses with only ellipsis characters

## Files Modified

- `interactive_chat/main.py` - Added validation function and applied checks at 2 sentence emission points
