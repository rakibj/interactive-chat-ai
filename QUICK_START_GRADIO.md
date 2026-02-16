# 🚀 Quick Start - Complete Gradio Solution

## One Command to Start Everything

```bash
python run_complete_gradio_app.py
```

That's it! Here's what happens:

```
1. Engine starts (background)
   ↓
2. API server starts (background)
   ↓
3. Gradio opens in your browser
   ↓
4. Use the interface
   ↓
5. Close window or Ctrl+C to shutdown everything
```

## What You Get

| Component      | URL                        | Status                      |
| -------------- | -------------------------- | --------------------------- |
| **Gradio UI**  | http://localhost:7860      | Main interface (opens auto) |
| **API Server** | http://localhost:8000      | Background service          |
| **API Docs**   | http://localhost:8000/docs | Interactive reference       |

## Using Gradio Interface

### Text Controls

- **Text Input**: Type your message
- **Submit**: Press Enter or click Submit

### Action Buttons

- **Start** - Begin conversation
- **Pause** - Pause processing
- **Resume** - Resume from pause
- **Stop** - Stop completely
- **Reset Profile** - Clear chat, keep settings
- **Reset All** - Clear everything

### Display Panels

- **Status** - Current state (IDLE/SPEAKING/etc)
- **Phase** - Progress through conversation phases
- **Speaker** - Who is speaking (User/AI)
- **History** - Full chat transcript
- **Session Info** - Turn count, times, etc

## Stop the Application

Choose any:

1. **Close Gradio window** ← Recommended
2. **Press Ctrl+C** in terminal
3. **Click Stop button** in UI

All cleanup happens automatically!

## For Developers

```bash
# API + Engine only (no Gradio)
python -m interactive_chat.main --no-gradio

# Then in another terminal:
python gradio_demo.py

# Or use Gradio in default main:
python -m interactive_chat.main
```

## Verify It Works

```bash
# Run tests
uv run pytest tests/ -q

# Expected: 247 passed ✅
```

## Troubleshooting

### Port 7860 already in use?

```bash
netstat -ano | findstr :7860
taskkill /PID <PID> /F
```

### Gradio not found?

```bash
pip install gradio
```

### API won't start?

```bash
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

## That's All You Need!

```
python run_complete_gradio_app.py
         ↓
    Everything starts
         ↓
    Browser opens
         ↓
    Use interface
         ↓
    Close window
         ↓
    Everything stops
```

Simple, clean, complete! ✅
