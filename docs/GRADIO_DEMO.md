# Gradio Demo - Interactive Chat AI

## Quick Start

### Prerequisites

- Python 3.10+
- Gradio 4.0+ (or Gradio 6.0+ with latest compatibility)
- API server available on http://localhost:8000

### 1. Start the API Server

First, ensure the API server is running (it should be running from Phase 1 & 2 implementation):

```bash
# From the project root
python -m interactive_chat.main --no-gradio
```

Expected output:

```
✓ INFO: Uvicorn running on http://0.0.0.0:8000
```

### 2. Launch the Gradio Demo

In a separate terminal:

```bash
# From the project root
python gradio_demo.py
```

Expected output:

```
🎤 Interactive Chat AI - Gradio Demo
==================================================

📍 API Base URL: http://localhost:8000/api

⚠️  Make sure the API server is running:
   python -m interactive_chat.main --no-gradio

🚀 Launching Gradio interface...
   👉 Open browser at: http://localhost:7860
```

### 3. Open in Browser

Navigate to: **http://localhost:7860**

You should see the interactive demo with real-time updates.

---

## User Interface Overview

### Main Display Sections

#### 1. Phase Progress (📊)

Shows the current phase of the conversation with visual indicators:

- **✅ Completed** - Phases that have finished
- **🔵 Active** - Currently executing phase (highlighted, marked with "← Current")
- **⭕ Upcoming** - Phases that will run next

Each phase shows duration in seconds for completed phases.

Example:

```
📊 Phase Progress (2/3)

✅ Warmup (1.5s)
🔵 **Main** (3.2s) ← Current
⭕ Conclusion
```

#### 2. Current Speaker (Current Speaker Label)

Real-time indicator of who is currently speaking:

- **🎤 HUMAN Speaking** - User is speaking
- **🤖 AI Speaking** - AI system is generating response
- **⏸️ SILENCE (Waiting)** - No active speaker, system is waiting
- **❓ Unknown** - Speaker status not available

#### 3. Live Captions (Live Captions Textbox)

Shows the most recent transcript in real-time:

```
🤖 AI: "That's an interesting question. Let me think about that..."
```

Updates every 500ms to reflect the latest spoken text.

#### 4. Conversation History (Conversation History)

Full color-coded conversation display with metadata:

- **🎤 HUMAN** (blue background) - User messages
- **🤖 AI** (green background) - AI responses

Each turn includes:

- Turn number
- Phase ID
- Timestamp
- Duration (for completed turns)
- Latency (API response time in ms)

Example:

```
🎤 HUMAN
"Hello, how are you?"
Turn #1 • warmup • 12:34:56 • 1.2s

🤖 AI
"I'm doing great, thanks for asking!"
Turn #2 • main • 12:34:57 • 2.1s • 150ms latency
```

#### 5. Session Information (JSON display)

Real-time statistics about the current session:

```json
{
  "connected": true,
  "current_turn_id": 5,
  "is_processing": false,
  "total_turns": 9,
  "current_phase": "main",
  "phase_progress": "2/3",
  "current_speaker": "ai",
  "latest_turn_latency_ms": 150
}
```

### Expandable Sections

#### Full Transcript (📋)

Click "Full Transcript" to expand and see the complete plaintext transcript:

```
[Turn 1 - warmup] HUMAN: Hello
[Turn 2 - warmup] AI: Hi there!
[Turn 3 - main] HUMAN: How does this work?
[Turn 4 - main] AI: Great question...
```

Can be copied directly to clipboard.

#### API Information (ℹ️)

Shows API connection details and instructions:

- Current API Base URL
- How to start the server
- Troubleshooting tips

### Controls

- **🔄 Refresh Now** - Manually fetch latest state from API
- **📋 Copy Transcript** - Copy full transcript to expandable section

### Status Bar

Bottom status indicator shows:

- ✅ **Connected** - API is responding normally
- 🔴 **Error message** - Connection or API issues
- Turn count and processing status

Example: `✅ Connected | 12 turns (Processing turn...)`

---

## API Integration

### Endpoints Used

The Gradio demo consumes these Phase 1 & 2 API endpoints:

#### `/api/state` (Primary Endpoint)

Returns complete conversation state.

**Request:**

```bash
GET http://localhost:8000/api/state
```

**Response:**

```json
{
  "phase": {
    "phase_index": 1,
    "total_phases": 3,
    "current_phase_id": "main",
    "progress": [
      { "name": "Warmup", "status": "completed", "duration_sec": 2.1 },
      { "name": "Main", "status": "active", "duration_sec": null },
      { "name": "Conclusion", "status": "upcoming", "duration_sec": null }
    ]
  },
  "speaker": {
    "speaker": "ai"
  },
  "history": [
    {
      "turn_id": 1,
      "speaker": "human",
      "transcript": "Hello",
      "phase_id": "warmup",
      "timestamp": 1609459200,
      "latency_ms": 50,
      "duration_sec": 1.0
    }
  ],
  "turn_id": 5,
  "is_processing": false
}
```

#### `/api/limitations` (Optional)

Get information about API constraints.

**Request:**

```bash
GET http://localhost:8000/api/limitations
```

**Response:**

```json
[
  {
    "category": "concurrency",
    "limitation": "Single concurrent session",
    "rationale": "Engine limitation in current phase"
  },
  {
    "category": "event_buffer",
    "limitation": "Last 100 events per session",
    "rationale": "Memory efficiency"
  }
]
```

### Response Error Handling

The Gradio demo handles these API error scenarios:

| Error Type         | Display                                         | Recovery                             |
| ------------------ | ----------------------------------------------- | ------------------------------------ |
| Connection Error   | "Cannot connect to API (http://localhost:8000)" | Shows placeholder UI                 |
| Timeout            | "API request timed out"                         | Retries on next auto-refresh (500ms) |
| HTTP Error         | "API error: 503"                                | Keeps last valid state, shows error  |
| Malformed Response | "Error: Invalid JSON"                           | Shows error banner                   |

### Auto-Refresh Behavior

The UI loads the initial state when you open the page. Use the "🔄 Refresh Now" button for manual updates.

For continuous auto-refresh behavior:

```python
# In Gradio 6.0+, use manual refresh or implement custom polling:
# Option 1: Use refresh button (default)
# Option 2: Implement client-side JavaScript polling
# Option 3: Use browser auto-refresh (F5)
```

When the API is unavailable:

- Error message appears in status bar
- UI shows last known state
- Click "🔄 Refresh Now" to retry
- Normal operation resumes when API recovers

---

## Configuration

### Custom API URL

To connect to an API server on a different host/port:

```python
from gradio_demo import GradioDemoApp

app = GradioDemoApp(api_base="http://your-host:9000/api")
interface = app.build_interface()
interface.launch()
```

### Custom Gradio Server Settings

In `gradio_demo.py`, modify the `main()` function:

```python
interface.launch(
    server_name="0.0.0.0",      # Listen on all interfaces
    server_port=7860,            # Port
    share=True,                  # Create public link
    show_error=True,             # Show error popup
    show_api=False               # Hide API documentation
)
```

#### Launch Options

| Option        | Default     | Purpose                                           |
| ------------- | ----------- | ------------------------------------------------- |
| `server_name` | "127.0.0.1" | Interface to bind to (127.0.0.1 = localhost only) |
| `server_port` | 7860        | Port for Gradio server                            |
| `share`       | False       | Create public Gradio link (https://gradio.live)   |
| `show_error`  | True        | Show error messages in popup                      |
| `show_api`    | False       | Show OpenAPI documentation                        |

---

## Deployment Options

### 1. Local Development (Default)

```bash
python gradio_demo.py
```

- Runs on `http://localhost:7860`
- Only accessible on your machine
- Great for testing and development

### 2. Network Access

Make the demo accessible on your local network:

```python
# In gradio_demo.py, modify the launch call:
interface.launch(
    server_name="0.0.0.0",    # Listen on all network interfaces
    server_port=7860,
    show_error=True
)
```

Then access from other machines on the same network:

```
http://<your-machine-ip>:7860
```

### 3. Public Sharing (Temporary)

Create a public link automatically:

```python
interface.launch(
    share=True  # Enables public Gradio link
)
```

This generates a temporary public URL (valid for ~72 hours):

```
Running on public URL: https://12345.gradio.live
```

### 4. Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.10

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install

COPY . .

EXPOSE 7860
EXPOSE 8000

CMD ["python", "gradio_demo.py"]
```

Build and run:

```bash
docker build -t interactive-chat-ai .
docker run -p 7860:7860 -p 8000:8000 interactive-chat-ai
```

### 5. Docker Compose

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  api:
    build: .
    command: python -m interactive_chat.main --no-gradio
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1

  gradio:
    build: .
    command: python gradio_demo.py
    ports:
      - "7860:7860"
    depends_on:
      - api
    environment:
      - PYTHONUNBUFFERED=1
      - GRADIO_API_BASE=http://api:8000/api
```

Run both services:

```bash
docker-compose up
```

---

## Troubleshooting

### "Cannot connect to API (http://localhost:8000)"

**Cause**: API server is not running.

**Solution**:

```bash
# In a new terminal, start the API
python -m interactive_chat.main --no-gradio
```

### "API request timed out"

**Cause**: API is slow or unresponsive.

**Solution**:

1. Check if the API server is running: `curl http://localhost:8000/health`
2. Check API logs for errors
3. Verify network connectivity: `ping localhost`

### "API error: 503"

**Cause**: API service unavailable (likely no engine running).

**Solution**:

1. Ensure the conversation engine is properly initialized
2. Check API logs: Look at FastAPI console output
3. Verify API is responding: `curl http://localhost:8000/api/state`

### Demo shows no data but no error

**Cause**: API is responding but no conversation has started yet.

**Solution**:

- Start a conversation through another interface or API client
- Wait for turns to appear in the history
- Demo refreshes every 500ms, so data should appear quickly

### Custom API URL not connecting

**Cause**: URL mismatch or network issue.

**Solution**:

1. Verify the URL is correct
2. Test the URL in browser or curl: `curl http://your-url/api/state`
3. Check firewall settings if connecting across networks
4. Verify CORS settings on API server

### Gradio UI not updating

**Cause**: Auto-refresh disabled or API response issues.

**Solution**:

1. Click "🔄 Refresh Now" to manually update
2. Check browser console for JavaScript errors (F12)
3. Verify API is returning data: `curl http://localhost:8000/api/state | jq`

---

## Performance Notes

### Refresh Behavior

The demo uses manual refresh by default:

- **Refresh Button**: Click "🔄 Refresh Now" to manually update
- **Initial Load**: UI fetches state when page first loads
- **User Experience**: Responsive, user-controlled updates

For automated polling (requires custom implementation):

```python
# To add auto-refresh, implement client-side JavaScript
# or use threading with careful state management
```

### API Rate Limiting

The API enforces:

- **5 connections per IP address** (WebSocket limit)
- **1000 events per minute per session** (event rate)

The Gradio demo respects these limits with HTTP requests.

### Memory Usage

- **Event Buffer**: Last 100 events cached in memory
- **History Display**: Renders all turns (typical: 10-50 turns)
- **Session Info**: JSON metadata only

Typical memory footprint: **< 50MB** for normal usage.

---

## Development

### Running Tests

```bash
# Run all Gradio demo tests
pytest tests/test_gradio_demo.py -v

# Run specific test class
pytest tests/test_gradio_demo.py::TestPhaseFormatting -v

# Run with coverage
pytest tests/test_gradio_demo.py --cov=gradio_demo
```

Expected: **36 tests passing**

### Creating Custom Components

Extend `GradioDemoApp` to add custom displays:

```python
class CustomDemoApp(GradioDemoApp):
    """Extended demo with custom components."""

    def format_custom_display(self, state: Dict[str, Any]) -> str:
        """Add custom formatting logic."""
        return "Custom display"

    def build_interface(self) -> gr.Blocks:
        """Override to add custom components."""
        with gr.Blocks() as demo:
            # Original components
            super_demo = super().build_interface()

            # Add custom component
            custom = gr.Markdown(
                label="Custom",
                value="Custom content"
            )

        return demo
```

### Debugging

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

app = GradioDemoApp()
```

Monitor API calls:

```bash
# In one terminal
python gradio_demo.py

# In another, monitor HTTP traffic
tcpdump -i lo port 8000
```

---

## API Limitations & Constraints

See `/api/limitations` endpoint for complete list:

```bash
curl http://localhost:8000/api/limitations
```

Key limitations affecting the Gradio demo:

1. **Single User Only** (Phase 1-2)
   - Only one active conversation at a time
   - Additional connections will receive 429 errors
   - Workaround: Wait for previous session to timeout (30 minutes)

2. **Event Buffer Size**
   - Last 100 events stored
   - Older events not accessible
   - Reconnecting restores full event history

3. **WebSocket-Free Design**
   - Gradio demo uses polling (not WebSocket)
   - Polling interval: 500ms
   - Latency: <100ms typical

---

## Examples

### Example 1: Start Conversation, Watch Demo

**Terminal 1**: Start API

```bash
python -m interactive_chat.main --no-gradio
```

**Terminal 2**: Start Gradio demo

```bash
python gradio_demo.py
```

**Browser**: Open `http://localhost:7860`

**Action**: Start a conversation through API or another client. Watch the Gradio demo update in real-time as conversation progresses through phases.

### Example 2: Connect to Remote API

Modify `gradio_demo.py`:

```python
if __name__ == "__main__":
    app = GradioDemoApp(api_base="http://192.168.1.100:8000/api")
    interface = app.build_interface()
    interface.launch()
```

Run and connect to remote system.

### Example 3: Docker Multi-Container

```bash
# Start both API and Gradio in containers
docker-compose up

# Access at http://localhost:7860
```

---

## Future Enhancements (Phase 4+)

Potential improvements for future phases:

1. **WebSocket Integration** - Real-time streaming instead of polling
2. **Session Management UI** - Create/manage multiple sessions
3. **Analytics Dashboard** - Statistics and metrics
4. **Export Functionality** - Save conversations as JSON/PDF
5. **Real-time Visualization** - Phase progress animation
6. **Theme Customization** - User-selectable color schemes
7. **Accessibility Modes** - High contrast, screen reader optimization
8. **Performance Monitoring** - Show latency graphs, event rates

---

## Support & Resources

### Quick Commands

```bash
# Start everything
make demo                    # Requires Makefile

# Manual start
python -m interactive_chat.main --no-gradio &
sleep 2
python gradio_demo.py

# Test API connectivity
curl http://localhost:8000/health
curl http://localhost:8000/api/state

# View logs
tail -f logs/session_*.jsonl
```

### Documentation Links

- [Phase 1 REST API](./PHASE_1_COMPLETION.md)
- [Phase 2 WebSocket](./PHASE_2.md)
- [API Limitations](../project_description.md#api-limitations)
- [Gradio Framework](https://www.gradio.app/)

### Contact

For issues or questions about the Gradio demo, check:

1. This documentation (Troubleshooting section)
2. API logs: `logs/session_*.jsonl`
3. Gradio console output for errors
