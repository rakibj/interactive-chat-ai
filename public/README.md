# Interactive Chat AI - HTML/CSS Web Demo

A lightweight, responsive web interface for Interactive Chat AI built with vanilla HTML, CSS, and JavaScript (no framework dependencies).

## Quick Start

### Single Entry Point

```bash
# Start everything with one command
uv run python run_html_app.py

# Or with specific profile
uv run python run_html_app.py --profile ielts_instructor

# See all options
uv run python run_html_app.py --help
```

This will automatically start:
- 🌐 **Web Interface**: http://localhost:7860
- 📡 **API Server**: http://localhost:8000
- 🎙️ **ConversationEngine**: Real-time voice processing

Open your browser to http://localhost:7860 and start chatting!

## Architecture

```
Browser (HTML/CSS/JS)
    ↓
WebSocket (Real-time updates)
REST API (State polling fallback)
    ↓
FastAPI Server (Python)
    ↓
ConversationEngine (Event loop, ASR, LLM, TTS)
```

## Features

✅ **Real-Time Updates** - WebSocket streaming with automatic reconnect  
✅ **Responsive Design** - Works on desktop, tablet, mobile  
✅ **Session Management** - Automatic session creation and recovery  
✅ **Phase Tracking** - Visual phase progress indicator  
✅ **Latency Metrics** - ASR, LLM, and total latency display  
✅ **Speaker Status** - Visual indicator of who's speaking  
✅ **Event Buffering** - Automatic catch-up on reconnect  
✅ **Fallback Polling** - REST API polling if WebSocket disconnected  
✅ **Error Handling** - Graceful error messages and recovery  

## Options

```bash
uv run python run_html_app.py [OPTIONS]

Options:
  --profile PROFILE    Profile to use (default: negotiator)
  --no-api             Skip API server (engine only)
  --no-browser         Don't open browser automatically
  --help               Show this help message
```

### Available Profiles

- `negotiator` - Price haggling scenario
- `ielts_instructor` - IELTS speaking test
- `confused_customer` - Customer service training
- `technical_support` - IT troubleshooting
- `language_tutor` - English conversation
- `curious_friend` - Casual chat

### Examples

```bash
# IELTS Speaking Test
uv run python run_html_app.py --profile ielts_instructor

# No automatic browser open
uv run python run_html_app.py --no-browser

# Engine only (no API)
uv run python run_html_app.py --no-api

# Custom profile
uv run python run_html_app.py --profile confused_customer
```

## File Structure

```
interactive-chat-ai/
├── run_html_app.py              # Single entry point ⭐
├── public/                       # Static web files
│   ├── index.html               # Main UI (5.9 KB)
│   ├── css/
│   │   ├── styles.css           # Design system (9.2 KB)
│   │   └── responsive.css       # Mobile optimization (5.9 KB)
│   └── js/
│       ├── app.js               # App orchestration (6.8 KB)
│       ├── state.js             # Client state management (4.4 KB)
│       ├── ui.js                # DOM updates (10.0 KB)
│       └── websocket.js         # Real-time streaming (8.1 KB)
└── ... (backend Python code)
```

**Total Web Bundle**: ~58 KB (uncompressed)

## How It Works

### 1. Page Load
```
Browser loads index.html
↓
JavaScript initializes (app.js)
↓
Check backend health (/api/health)
↓
Load initial state (/api/state)
↓
Connect WebSocket (/ws)
↓
Render UI with current state
```

### 2. User Speaks
```
ConversationEngine detects speech (VAD)
↓
Emits VAD_SPEECH_STARTED via WebSocket
↓
js/websocket.js receives event
↓
js/ui.js updates speaker indicator: "🎤 You're speaking"
```

### 3. AI Responds
```
ConversationEngine receives VAD_SPEECH_ENDED
↓
Transcribes via Whisper
↓
Sends to LLM
↓
Streams LLM tokens → TTS
↓
Emits TTS_SPEAKING_STARTED via WebSocket
↓
js/websocket.js receives event  
↓
js/ui.js streams AI response to chat
↓
Emits TTS_SPEAKING_ENDED
↓
Speaker indicator returns to "⏸️ Listening"
```

### 4. Real-Time Updates

**Via WebSocket** (Primary):
- VAD_SPEECH_STARTED / VAD_SPEECH_ENDED
- TTS_SPEAKING_STARTED / TTS_SPEAKING_ENDED
- TURN_COMPLETED (with metrics)
- PHASE_TRANSITION_COMPLETE
- ANALYTICS_TURN_METRICS

**Via REST Polling** (Fallback):
- If WebSocket disconnects, `app.js` polls `/api/state` every 2s
- Automatic reconnect with exponential backoff

## JavaScript Modules

### state.js
Client-side state management (no external dependencies)
```javascript
appState = { currentPhase, activeSpeaker, turns, wsConnected, ... }
on('speakerChanged', callback)      // Subscribe to state changes
updateSpeaker('human' | 'ai' | 'silence')  // Update speaker
addTurn(turn)                        // Add conversation turn
```

### ui.js
DOM manipulation and rendering
```javascript
UIManager.updateSpeakerIndicator(speaker)
UIManager.streamAIResponse(textChunk)
UIManager.displayTurnMetrics(metrics)
UIManager.updatePhaseInfo(phaseData)
```

### websocket.js
Real-time event streaming with reconnection logic
```javascript
wsManager.connect()                  // Connect to /ws
// Automatic reconnect on disconnect
// Signal dispatch to handlers
// Deduplication by message_id
```

### app.js
Application orchestration
```javascript
app.init()                          // Initialize app
app.checkBackendHealth()            // Verify backend running
app.loadInitialState()              // Load state from REST API
app.connectWebSocket()              // Connect WebSocket
app.startPolling()                  // Start fallback polling
```

## CSS Features

- **Dark theme** by default (light theme available via prefers-color-scheme)
- **CSS Grid** for responsive layout
- **Flexbox** for component organization
- **Animations** for speaker indicator, message arrival
- **Mobile-first** responsive design
- **Mobile breakpoints**: 480px, 600px, 768px, 1024px

## API Integration

The web app uses these FastAPI endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Check backend status |
| `/api/state` | GET | Get current phase, speaker, history |
| `/api/state/phase` | GET | Get phase progress details |
| `/api/state/speaker` | GET | Get who's speaking |
| `/api/conversation/history` | GET | Get conversation turns |
| `/ws` | WebSocket | Real-time event streaming |
| `/docs` | GET | Swagger API documentation |

All endpoints return JSON with proper status codes and error handling.

## Performance

- **Web Bundle**: ~58 KB (uncompressed)
- **Latency**: <100 ms for UI updates (WebSocket)
- **Memory**: ~5-10 MB browser footprint
- **CPU**: Minimal (event-driven updates only)
- **Mobile**: Optimized for 4G/5G networks

## Browser Compatibility

✅ Chrome/Chromium 90+  
✅ Firefox 88+  
✅ Safari 14+  
✅ Edge 90+  

## Troubleshooting

### WebSocket not connecting
- Check if API server is running: `curl http://localhost:8000/api/health`
- Check for CORS issues in browser console
- Try manual page refresh (browser cache)

### No WebSocket? Using REST polling instead
- Fallback polling works (/api/state every 2s)
- Slightly higher latency but still functional
- Logs "❌ WebSocket error" to console

### API server not starting
```bash
# Run without API server (engine only)
uv run python run_html_app.py --no-api
```

### Browser won't open
```bash
# Run with --no-browser and visit manually
uv run python run_html_app.py --no-browser
# Then visit http://localhost:7860
```

## Development

### Modify UI
1. Edit `public/index.html` for structure
2. Edit `public/css/styles.css` for styling
3. Edit `public/js/*.js` for functionality
4. Refresh browser to see changes

### Add New Features
1. Add state in `public/js/state.js`
2. Add state listeners in `public/js/ui.js`
3. Handle WebSocket signals in `public/js/websocket.js`
4. Update HTML template in `public/index.html`

### Debug
- Open browser DevTools (F12)
- Check Console tab for errors
- Check Network tab for WebSocket connection
- Check Application tab for localStorage/IndexedDB

## Comparison with Gradio

| Feature | Gradio | HTML/CSS |
|---------|--------|----------|
| **Dependencies** | Heavy framework | None (vanilla JS) |
| **Bundle Size** | ~2 MB | ~58 KB |
| **Customization** | Limited | Full control |
| **Mobile** | Basic | Responsive |
| **Real-time** | Polling | WebSocket + fallback |
| **Learning** | Python-only | HTML/CSS/JS required |
| **Latency** | ~2-5s | <100 ms |
| **Production** | Good | Excellent |

## Advantages of Raw HTML/CSS Approach

✅ **Lightweight** - No framework overhead  
✅ **Fast** - Direct DOM updates, minimal re-renders  
✅ **Responsive** - Built-in mobile support  
✅ **Customizable** - Full control over every pixel  
✅ **Maintainable** - Simple vanilla JavaScript  
✅ **Performance** - Suitable for demo + production  
✅ **Portable** - Can deploy on any static host (CDN, S3, etc.)  

## Deployment

### Local
```bash
uv run python run_html_app.py
```

### Docker
```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "run_html_app.py"]
```

### Production
- Serve `public/` directory from CDN (CloudFront, Cloudflare, etc.)
- Run backend API on separate server
- Update `API_BASE_URL` in `public/js/app.js`

## License

Same as Interactive Chat AI project

## Support

- 📝 See [docs/README.md](../docs/README.md) for full project documentation
- 🐛 Report issues on GitHub
- 💡 Contribute improvements via pull requests

---

**Made with ❤️ for Interactive Chat AI**
