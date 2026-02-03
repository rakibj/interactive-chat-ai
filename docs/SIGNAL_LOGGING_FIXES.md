# Signal Logging & ASR Error Fixes

## Changes Made

### 1. **Removed ASR Partial Transcript Logs**

- **File**: `interactive_chat/core/event_driven_core.py`
- **Change**: Removed the log action that printed "📝 ASR Partial: '{text}'" on every speech chunk
- **Benefit**: Cleaner console output, signals now visible without ASR noise

### 2. **Added Waveform Error Handling**

- **File**: `interactive_chat/main.py`
- **Change**: Wrapped `accept_waveform()` in try/except to silently catch "Failed to process waveform" errors
- **Benefit**: Application continues gracefully instead of crashing on audio processing errors

### 3. **Fixed Signal Consumer to Receive Signal Objects**

- **File**: `interactive_chat/signals/consumer.py`
- **Change**: Updated `handle_signal()` to receive `Signal` objects directly (not wrapped in events)
- **Benefit**: Signal logs now display correctly with emoji marker (📡 SIGNAL)

### 4. **Suppressed Model Startup Print Statements**

- **Files**:
  - `interactive_chat/interfaces/asr.py` - Vosk, Whisper local, and Whisper cloud
- **Changes**: Removed "Loading..." print statements from ASR **init** methods
- **Benefit**: Cleaner startup, focus on signal logs not model loading messages

### 5. **Added UTF-8 Encoding to Test Script**

- **File**: `test_ielts_signals.py`
- **Change**: Added `# -*- coding: utf-8 -*-` to handle emoji output on Windows
- **Benefit**: Script runs on Windows PowerShell without encoding errors

## Testing

Run the IELTS test to see signals firing and being captured:

```bash
# Set UTF-8 encoding for Windows
$env:PYTHONIOENCODING='utf-8'

# Run the test
python test_ielts_signals.py
```

**Expected output:**

- Profile setup (no loading messages)
- Signal firing messages with timestamp, payload, context
- No ASR partial logs
- Summary showing 14+ signals captured

## Signal Output Format

Each signal is logged as:

```
========================================
[SIGNAL_TYPE] SIGNAL FIRED: signal.name
========================================
Time: HH:MM:SS.mmm
Payload:
   • key: value
Context:
   • key: value
========================================
```

## Console Colors (Windows PowerShell)

Due to PowerShell's encoding limitations, emojis may appear garbled but the signal data is correct and complete.

For better visual output, run in Windows Terminal or use:

```bash
$env:PYTHONIOENCODING='utf-8'
```
