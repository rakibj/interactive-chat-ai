"""Quick start guide for Phase 1 API."""

# Phase 1 API - Demo Dashboard Integration

## Files Created

```
interactive_chat/
├── api/
│   ├── __init__.py          # API package exports
│   └── models.py            # Pydantic models (Turn, PhaseState, etc.)
├── server.py                # FastAPI app with 5 endpoints

tests/
└── test_api_endpoints.py    # 24 TDD tests (all passing ✅)
```

## Quick Start

### 1. Install Dependencies

```bash
uv pip install fastapi uvicorn
# or they may already be in your environment
```

### 2. Run the API Server

```bash
# Option A: Direct FastAPI
cd interactive_chat
python -m uvicorn server:app --reload --port 8000

# Option B: From main.py integration (coming in Phase 2)
python main.py  # Will start on port 8000
```

### 3. Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 4. Test Endpoints

```bash
# Health check
curl http://localhost:8000/api/health

# Get current phase
curl http://localhost:8000/api/state/phase

# Get speaker status
curl http://localhost:8000/api/state/speaker

# Get full state
curl http://localhost:8000/api/state

# Get conversation history (last 20 turns)
curl http://localhost:8000/api/conversation/history
```

## Pydantic Models

All responses use Pydantic models with automatic validation and JSON schema generation:

### Request/Response Models

```python
# Response format for /api/state/phase
PhaseState(
    current_phase_id="part1",      # str
    phase_index=1,                 # int
    total_phases=5,                # int
    phase_name="Part 1 Questions", # str
    phase_profile="ielts_full_exam", # str
    progress=[                      # List[PhaseProgress]
        {
            "id": "greeting",
            "name": "Greeting Phase",
            "status": "completed",  # "completed" | "active" | "upcoming"
            "duration_sec": 5.2
        },
        {
            "id": "part1",
            "name": "Part 1",
            "status": "active",
            "duration_sec": 0
        }
    ]
)

# Response format for /api/state/speaker
SpeakerStatus(
    speaker="ai",               # "human" | "ai" | "silence"
    timestamp=1707052800.789,   # Unix timestamp
    phase_id="part1"            # str
)

# Response format for /api/conversation/history
{
    "turns": [
        Turn(
            turn_id=0,
            speaker="ai",
            transcript="Hello, what's your name?",
            timestamp=1707052800.123,
            phase_id="greeting",
            duration_sec=2.5,
            latency_ms=1250
        ),
        Turn(...)
    ],
    "total": 2
}

# Response format for /api/state (complete)
ConversationState(
    phase=PhaseState(...),
    speaker=SpeakerStatus(...),
    turn_id=5,
    history=[Turn(...), Turn(...)],
    is_processing=False
)
```

## Test Coverage

### 24 Tests (All Passing ✅)

**Health Check** (3 tests):

- ✅ Returns 200 with status
- ✅ Shows engine_running=True/False
- ✅ Handles missing engine

**Phase State** (3 tests):

- ✅ Returns current phase
- ✅ Progress includes all phases with status
- ✅ Returns 503 when engine not initialized

**Speaker Status** (2 tests):

- ✅ Returns current speaker (human/ai/silence)
- ✅ Includes phase_id

**Conversation History** (4 tests):

- ✅ Returns recent turns
- ✅ Includes all turn fields
- ✅ Respects limit parameter
- ✅ Defaults to limit=50

**Full State** (5 tests):

- ✅ Returns complete state
- ✅ Phase section has progress
- ✅ Speaker section is present
- ✅ History section included
- ✅ is_processing flag reflects engine state

**Error Cases** (2 tests):

- ✅ All endpoints return 503 when engine not set
- ✅ Invalid limit parameter handling

**Pydantic Models** (5 tests):

- ✅ EventPayload validates
- ✅ PhaseState validates
- ✅ SpeakerStatus validates
- ✅ Turn validates
- ✅ ConversationState validates

## API Response Examples

### GET /api/health

```json
{
  "status": "healthy",
  "timestamp": "2026-02-04T12:34:56.789123",
  "engine_running": true
}
```

### GET /api/state/speaker

```json
{
  "speaker": "ai",
  "timestamp": 1707052800.456,
  "phase_id": "part1"
}
```

### GET /api/state/phase

```json
{
  "current_phase_id": "part1",
  "phase_index": 1,
  "total_phases": 5,
  "phase_name": "Part 1 Questions",
  "phase_profile": "ielts_full_exam",
  "progress": [
    {
      "id": "greeting",
      "name": "Greeting Phase",
      "status": "completed",
      "duration_sec": 5.2
    },
    {
      "id": "part1",
      "name": "Part 1 Questions",
      "status": "active",
      "duration_sec": 0
    },
    {
      "id": "part2",
      "name": "Part 2 Long Turn",
      "status": "upcoming",
      "duration_sec": null
    }
  ]
}
```

## Key Design Decisions

### Why Pydantic?

- ✅ Automatic JSON schema generation for `/docs`
- ✅ Type validation on responses
- ✅ Serializable to JSON automatically
- ✅ Better than @dataclass for API contracts

### Single User (Phase 1)

- ✅ Simpler architecture (no session management)
- ✅ Faster to implement and test
- ✅ Good for demo/development
- ⚠️ NOT production-ready for multiple users
- ⚠️ See "API Limitations" in project_description.md

### No Authentication (Phase 1)

- ✅ Demo simplicity
- ⚠️ Production needs JWT/session tokens (Phase 2)

## Next Steps (Phase 2)

- [ ] WebSocket streaming for real-time signals
- [ ] Session management for multi-user
- [ ] Authentication (JWT)
- [ ] Rate limiting
- [ ] Caching layer
- [ ] Integration with main.py event loop

## Running Tests

```bash
# All API tests
pytest tests/test_api_endpoints.py -v

# Full test suite (101 tests)
pytest tests/ -v

# Quick check
pytest tests/ -q
```

## Debugging

**Common Issues**:

1. **"Engine not initialized"** (503)
   - Make sure `set_engine(engine_instance)` called before requests
   - Verify engine is running in separate thread

2. **Mock validation errors in tests**
   - Mock objects must have proper `.name` attributes set
   - See test fixture setup for examples

3. **CORS errors**
   - Update CORS middleware origins in `server.py`
   - Default allows all (`*`) - OK for localhost

## Production Checklist

Before deploying:

- [ ] Remove `*` CORS origin restriction
- [ ] Add request logging and monitoring
- [ ] Set `debug=False` in Pydantic models
- [ ] Add rate limiting
- [ ] Implement session management (Phase 2)
- [ ] Add authentication middleware
- [ ] Use production ASGI server (gunicorn, uvicorn with workers)
- [ ] Add health check monitoring
