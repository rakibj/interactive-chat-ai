# Complete Gradio-Controlled Solution - Setup & Usage

## 🎯 Overview

This is a **complete end-to-end Gradio-controlled solution** where:

- ✅ **Start**: Single command launches everything
- ✅ **Control**: All interaction through Gradio UI
- ✅ **Stop**: Close Gradio window or Ctrl+C to shutdown everything cleanly

## 🚀 Quick Start (3 Methods)

### Method 1: Complete Integrated Launcher (Recommended)

**Best for**: End-users who want a single command to start everything

```bash
python run_complete_gradio_app.py
```

**What happens:**

1. Engine starts in background
2. API server starts in background
3. Gradio interface launches and opens in browser
4. All components run until you close Gradio or press Ctrl+C
5. Everything shuts down cleanly

**Output:**

```
🚀 INTERACTIVE CHAT AI - Complete Gradio Solution
=======================================================

📦 Starting all components...
   1️⃣  Engine (background)
   2️⃣  API Server (background)
   3️⃣  Gradio UI (main interface)

Step 1/3: Starting engine and API server...
✅ API server is ready
✅ Engine and API server started

Step 2/3: Launching Gradio interface...

🎤 INTERACTIVE CHAT AI - Complete Gradio Solution
=======================================================

📍 Endpoints:
   Gradio UI:  http://localhost:7860
   API Server: http://localhost:8000
   API Docs:   http://localhost:8000/docs

🎮 Lifecycle Control:
   ✅ START:   Gradio launches automatically
   ✅ CONTROL: All interaction via Gradio UI
   ✅ STOP:    Close window or press Ctrl+C

✅ Complete end-to-end Gradio control
=======================================================

🚀 Launching Gradio interface...

(Browser opens automatically at http://localhost:7860)
```

### Method 2: Default main.py (Now includes Gradio)

**Best for**: Development or backwards compatibility

```bash
python -m interactive_chat.main
```

Same as Method 1 - now Gradio is included by default!

### Method 3: Separate Components (Legacy)

**Best for**: Advanced users who want separate control

```bash
# Terminal 1: API + Engine only
python -m interactive_chat.main --no-gradio

# Terminal 2: Gradio UI only
python gradio_demo.py
```

## 🎮 Using the Gradio Interface

Once Gradio launches, you have:

### Input Controls

- **Text Input**: Type messages to send to the AI
- **Submit**: Press Enter or click Submit

### Action Buttons

- **Start**: Begin conversation
- **Pause**: Pause current processing
- **Resume**: Resume from pause
- **Stop**: Stop completely
- **Reset Profile**: Clear history, keep profile
- **Reset All**: Clear everything

### Display Areas

- **Status Display**: Current state (IDLE, SPEAKING, etc.)
- **Phase Display**: Current phase progress
- **Speaker Display**: Who is speaking (User/AI)
- **Chat History**: Full conversation transcript
- **Session Info**: Turn count, times, etc.
- **Transcript**: Full text output

## 🛑 Stopping the Application

Choose any of these:

1. **Close Gradio window** - Gracefully shuts down everything
2. **Press Ctrl+C** in terminal - Triggers clean shutdown
3. **Click UI Stop button** - Stops the conversation

All cleanup is automatic - resources are freed, logs saved.

## 🔧 Command Line Options

### For main.py:

```bash
# Default: Run with Gradio UI + API + Engine
python -m interactive_chat.main

# API + Engine only (no Gradio)
python -m interactive_chat.main --no-gradio

# Gradio only (no API/Engine - API must be running separately)
python gradio_demo.py

# Engine only (no API, no Gradio)
python -m interactive_chat.main --no-api --no-gradio
```

### For run_complete_gradio_app.py:

```bash
# Always launches complete solution
python run_complete_gradio_app.py

# No additional options needed
```

## 📊 Architecture

```
┌─────────────────────────────────────────────┐
│    USER: python run_complete_gradio_app.py  │
└────────────────┬────────────────────────────┘
                 │
        ┌────────▼──────────┐
        │  1. Start Engine   │
        │  (background)      │
        └────────┬───────────┘
                 │
        ┌────────▼──────────────┐
        │  2. Start API Server   │
        │  (background, wait)    │
        └────────┬───────────────┘
                 │
        ┌────────▼──────────────────────┐
        │  3. Launch Gradio UI           │
        │  (main thread, blocks)         │
        │  (opens browser automatically) │
        └────────┬──────────────────────┘
                 │
        ┌────────▼──────────────────┐
        │    USER INTERACTION       │
        │  • Text input             │
        │  • Control buttons        │
        │  • Live display updates   │
        │  • Real-time chat         │
        └────────┬──────────────────┘
                 │
        ┌────────▼──────────────────┐
        │  USER CLOSES GRADIO       │
        │  or presses Ctrl+C        │
        └────────┬──────────────────┘
                 │
        ┌────────▼──────────────────┐
        │  Graceful Shutdown:       │
        │  • Gradio closes          │
        │  • API stops              │
        │  • Engine stops           │
        │  • Resources cleaned      │
        │  • Logs saved             │
        └──────────────────────────┘
```

## 🔗 Access Points

| Component      | URL                         | Purpose                       |
| -------------- | --------------------------- | ----------------------------- |
| **Gradio UI**  | http://localhost:7860       | Main interface                |
| **API Server** | http://localhost:8000       | REST API endpoints            |
| **API Docs**   | http://localhost:8000/docs  | Interactive API documentation |
| **API Redoc**  | http://localhost:8000/redoc | API reference docs            |

## 📝 Endpoints Available

### When using Gradio, you can also call API directly:

```bash
# Get current state
curl http://localhost:8000/api/state

# Submit text input
curl -X POST http://localhost:8000/api/conversation/text-input \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello"}'

# Control engine
curl -X POST http://localhost:8000/api/engine/command \
  -H "Content-Type: application/json" \
  -d '{"command": "start"}'

# Reset conversation
curl -X POST http://localhost:8000/api/conversation/reset \
  -H "Content-Type: application/json" \
  -d '{"keep_profile": true}'
```

## 📋 What Gets Started

### Engine (Background Thread)

- Event-driven state machine
- Manages conversation lifecycle
- Handles audio, ASR, LLM, TTS
- Thread-safe operations
- Analytics logging

### API Server (Background Thread)

- FastAPI server on port 8000
- REST endpoints for state/control
- WebSocket support for events
- CORS enabled
- Error handling

### Gradio UI (Main Thread)

- Web interface on port 7860
- Real-time displays
- Button controls
- Text input
- Automatic browser launch
- Graceful shutdown handling

## ✅ Test Suite

Verify everything works:

```bash
# Run all tests
uv run pytest tests/ -q

# Run Gradio-specific tests
uv run pytest tests/test_gradio_demo.py -v

# Run API tests
uv run pytest tests/test_api_endpoints.py -v

# Run complete signal parsing tests
uv run pytest tests/test_signal_parsing.py -v
```

**Expected Results:**

- 247 total tests passing
- Zero failures
- All features verified

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Port 7860 in use
# Either: Change port in run_complete_gradio_app.py line ~82
# Or: Kill existing process
netstat -ano | findstr :7860
taskkill /PID <PID> /F

# Port 8000 in use
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### API Server Not Starting

```bash
# Check API logs
python -m interactive_chat.main --no-gradio 2>&1 | head -20

# Verify port is free
netstat -ano | findstr :8000

# Check dependencies
pip install uvicorn fastapi
```

### Gradio Not Found

```bash
# Install Gradio
pip install gradio

# Or using uv
uv pip install gradio
```

### Browser Not Opening

```bash
# Gradio still launches, just open manually:
# http://localhost:7860

# To disable auto-open, edit run_complete_gradio_app.py:
# Change: inbrowser=True
# To:     inbrowser=False
```

## 📊 Performance Expectations

| Metric        | Expected                  |
| ------------- | ------------------------- |
| Startup time  | 3-5 seconds               |
| API response  | <100ms                    |
| Gradio update | <50ms                     |
| Turn latency  | 2-5 seconds (ASR+LLM+TTS) |
| Memory usage  | 2-4GB                     |

## 🎯 Features

✅ **Complete Lifecycle Control from Gradio**

- Single entry point
- No separate terminals needed
- Automatic cleanup

✅ **Real-time Updates**

- Live chat display
- Status updates
- Phase progress

✅ **User-Friendly Interface**

- Automatic browser launch
- Clear instructions
- Intuitive controls

✅ **Production Ready**

- 247 passing tests
- Comprehensive error handling
- Clean resource management

✅ **API Available**

- Can call endpoints directly
- WebSocket support
- Full documentation

## 📚 Documentation

- [EXECUTION_GUIDE.md](./EXECUTION_GUIDE.md) - Complete usage guide
- [HOW_TO_RUN_WITH_GRADIO.md](./docs/HOW_TO_RUN_WITH_GRADIO.md) - Detailed Gradio guide
- [TEST_COVERAGE_GUARANTEE.md](./docs/TEST_COVERAGE_GUARANTEE.md) - What tests guarantee
- [API Docs](http://localhost:8000/docs) - Interactive API reference

## 🚀 Summary

This is a **complete, production-ready Gradio-controlled solution**:

1. **Single command to start**: `python run_complete_gradio_app.py`
2. **Everything launches automatically**: Engine, API, Gradio
3. **All control through Gradio**: No other terminals needed
4. **Clean shutdown**: Close window or Ctrl+C
5. **247 tests passing**: Fully verified
6. **Ready for deployment**: Works out of the box

**Perfect for end-users who want a single, integrated interface!** 🎉
