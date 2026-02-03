"""Tests for Gradio demo application - Contract-based TDD."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from gradio_demo import GradioDemoApp, API_BASE_URL


class TestPhaseFormatting:
    """Test phase progress display formatting."""
    
    def test_format_phase_progress_no_data(self):
        """Should show placeholder when no phase data available."""
        app = GradioDemoApp()
        state = {"error": "No data"}
        
        result = app.format_phase_progress(state)
        
        assert "No phase data available" in result
        assert "⚠️" in result
    
    def test_format_phase_progress_completed_phase(self):
        """Should show completed phase with ✅ indicator."""
        app = GradioDemoApp()
        state = {
            "phase": {
                "phase_index": 0,
                "total_phases": 3,
                "progress": [
                    {"name": "Warmup", "status": "completed", "duration_sec": 1.5}
                ]
            }
        }
        
        result = app.format_phase_progress(state)
        
        assert "✅ Warmup (1.5s)" in result
        assert "Warmup" in result
    
    def test_format_phase_progress_active_phase(self):
        """Should highlight active phase with 🔵 indicator and arrow."""
        app = GradioDemoApp()
        state = {
            "phase": {
                "phase_index": 1,
                "total_phases": 3,
                "progress": [
                    {"name": "Warmup", "status": "completed", "duration_sec": 1.5},
                    {"name": "Main", "status": "active", "duration_sec": 2.0}
                ]
            }
        }
        
        result = app.format_phase_progress(state)
        
        assert "🔵 **Main**" in result
        assert "← Current" in result
        assert "**Main**" in result
    
    def test_format_phase_progress_upcoming_phase(self):
        """Should show upcoming phase with ⭕ indicator."""
        app = GradioDemoApp()
        state = {
            "phase": {
                "phase_index": 0,
                "total_phases": 2,
                "progress": [
                    {"name": "Phase 1", "status": "completed"},
                    {"name": "Phase 2", "status": "upcoming"}
                ]
            }
        }
        
        result = app.format_phase_progress(state)
        
        assert "⭕ Phase 2" in result
    
    def test_format_phase_progress_without_duration(self):
        """Should handle phases without duration data."""
        app = GradioDemoApp()
        state = {
            "phase": {
                "phase_index": 0,
                "total_phases": 1,
                "progress": [
                    {"name": "Test", "status": "active"}
                ]
            }
        }
        
        result = app.format_phase_progress(state)
        
        assert "🔵 **Test**" in result
        assert "(" not in result.split("**Test**")[1].split("\n")[0]


class TestSpeakerStatus:
    """Test speaker status formatting."""
    
    def test_format_speaker_status_human_speaking(self):
        """Should display human speaker indicator."""
        app = GradioDemoApp()
        state = {"speaker": {"speaker": "human"}}
        
        label, probs = app.format_speaker_status(state)
        
        assert "🎤" in label
        assert "HUMAN" in label
    
    def test_format_speaker_status_ai_speaking(self):
        """Should display AI speaker indicator."""
        app = GradioDemoApp()
        state = {"speaker": {"speaker": "ai"}}
        
        label, probs = app.format_speaker_status(state)
        
        assert "🤖" in label
        assert "AI" in label
    
    def test_format_speaker_status_silence(self):
        """Should display silence/waiting indicator."""
        app = GradioDemoApp()
        state = {"speaker": {"speaker": "silence"}}
        
        label, probs = app.format_speaker_status(state)
        
        assert "⏸️" in label
        assert "Waiting" in label
    
    def test_format_speaker_status_unknown_speaker(self):
        """Should display unknown speaker indicator."""
        app = GradioDemoApp()
        state = {"speaker": {"speaker": "invalid"}}
        
        label, probs = app.format_speaker_status(state)
        
        assert "❓" in label
    
    def test_format_speaker_status_no_data(self):
        """Should handle missing speaker data."""
        app = GradioDemoApp()
        state = {"error": "No speaker data"}
        
        label, probs = app.format_speaker_status(state)
        
        assert "Waiting" in label or "Unknown" in label


class TestHistoryDisplay:
    """Test conversation history HTML rendering."""
    
    def test_format_conversation_history_empty(self):
        """Should show placeholder for empty history."""
        app = GradioDemoApp()
        state = {"history": []}
        
        result = app.format_conversation_history_html(state)
        
        assert "No conversation yet" in result
        assert "<div" in result
    
    def test_format_conversation_history_with_turns(self):
        """Should render multiple conversation turns."""
        app = GradioDemoApp()
        state = {
            "history": [
                {
                    "turn_id": 1,
                    "speaker": "human",
                    "transcript": "Hello",
                    "phase_id": "warmup",
                    "timestamp": 1000000000,
                    "latency_ms": 50,
                    "duration_sec": 1.0
                },
                {
                    "turn_id": 2,
                    "speaker": "ai",
                    "transcript": "Hi there!",
                    "phase_id": "main",
                    "timestamp": 1000000002,
                    "latency_ms": 100,
                    "duration_sec": 2.0
                }
            ]
        }
        
        result = app.format_conversation_history_html(state)
        
        assert "Hello" in result
        assert "Hi there!" in result
        assert "🎤" in result
        assert "🤖" in result
        assert "Turn #1" in result
        assert "Turn #2" in result
    
    def test_format_conversation_history_color_coding(self):
        """Should apply different colors for human vs AI."""
        app = GradioDemoApp()
        state = {
            "history": [
                {"turn_id": 1, "speaker": "human", "transcript": "Hi", "phase_id": "1", "timestamp": 1000000000},
                {"turn_id": 2, "speaker": "ai", "transcript": "Hi!", "phase_id": "1", "timestamp": 1000000001}
            ]
        }
        
        result = app.format_conversation_history_html(state)
        
        # Check that both color codes are present
        assert "#0066cc" in result  # Human blue
        assert "#00aa00" in result  # AI green
    
    def test_format_conversation_history_with_error(self):
        """Should display error in conversation history."""
        app = GradioDemoApp()
        state = {"error": "Connection timeout"}
        
        result = app.format_conversation_history_html(state)
        
        assert "Connection timeout" in result
        assert "color: red" in result


class TestAPIIntegration:
    """Test API integration and data fetching."""
    
    @patch('gradio_demo.requests.get')
    def test_get_full_state_success(self, mock_get):
        """Should successfully fetch state from API."""
        app = GradioDemoApp()
        mock_response = Mock()
        mock_response.json.return_value = {
            "phase": {"phase_index": 0},
            "speaker": {"speaker": "human"},
            "history": [],
            "turn_id": 0,
            "is_processing": False
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = app.get_full_state()
        
        assert result["phase"]["phase_index"] == 0
        assert result["speaker"]["speaker"] == "human"
        mock_get.assert_called_once()
    
    @patch('gradio_demo.requests.get')
    def test_get_full_state_connection_error(self, mock_get):
        """Should handle connection errors gracefully."""
        app = GradioDemoApp()
        mock_get.side_effect = Exception("Connection refused")
        
        result = app.get_full_state()
        
        assert "error" in result
        assert result["phase"] is None
        assert result["history"] == []
    
    @patch('gradio_demo.requests.get')
    def test_get_full_state_timeout(self, mock_get):
        """Should handle timeout errors."""
        import requests
        app = GradioDemoApp()
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")
        
        result = app.get_full_state()
        
        assert "error" in result
        assert "timed out" in result["error"]
    
    @patch('gradio_demo.requests.get')
    def test_get_full_state_http_error(self, mock_get):
        """Should handle HTTP errors."""
        import requests
        app = GradioDemoApp()
        mock_response = Mock()
        mock_response.status_code = 503
        mock_error = requests.exceptions.HTTPError()
        mock_error.response = mock_response
        mock_response.raise_for_status.side_effect = mock_error
        mock_get.return_value = mock_response
        
        result = app.get_full_state()
        
        assert "error" in result
        assert "503" in result["error"]
    
    @patch('gradio_demo.requests.get')
    def test_get_api_limitations_success(self, mock_get):
        """Should fetch API limitations."""
        app = GradioDemoApp()
        mock_response = Mock()
        mock_response.json.return_value = [
            {"category": "concurrency", "limitation": "1 user"},
            {"category": "latency", "limitation": "<100ms"}
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = app.get_api_limitations()
        
        assert len(result) == 2
        assert result[0]["category"] == "concurrency"
    
    @patch('gradio_demo.requests.get')
    def test_get_api_limitations_error(self, mock_get):
        """Should handle errors fetching limitations."""
        app = GradioDemoApp()
        mock_get.side_effect = Exception("API error")
        
        result = app.get_api_limitations()
        
        assert result == []


class TestTranscriptExtraction:
    """Test transcript extraction and formatting."""
    
    def test_get_transcript_text_empty(self):
        """Should show placeholder for empty transcript."""
        app = GradioDemoApp()
        state = {"history": []}
        
        result = app.get_transcript_text(state)
        
        assert "No transcript" in result
    
    def test_get_transcript_text_with_history(self):
        """Should extract full transcript from history."""
        app = GradioDemoApp()
        state = {
            "history": [
                {"turn_id": 1, "speaker": "human", "transcript": "Hello", "phase_id": "warmup"},
                {"turn_id": 2, "speaker": "ai", "transcript": "Hi!", "phase_id": "main"}
            ]
        }
        
        result = app.get_transcript_text(state)
        
        assert "Hello" in result
        assert "Hi!" in result
        assert "HUMAN" in result
        assert "AI" in result
        assert "Turn 1" in result
        assert "Turn 2" in result
    
    def test_get_transcript_text_format(self):
        """Should format transcript with proper structure."""
        app = GradioDemoApp()
        state = {
            "history": [
                {"turn_id": 1, "speaker": "human", "transcript": "Test", "phase_id": "p1"}
            ]
        }
        
        result = app.get_transcript_text(state)
        
        assert "[Turn 1 - p1] HUMAN: Test" in result


class TestUIComponents:
    """Test individual UI component formatting."""
    
    def test_format_live_captions_no_history(self):
        """Should show waiting message when no history."""
        app = GradioDemoApp()
        state = {"history": []}
        
        result = app.format_live_captions(state)
        
        assert "Waiting" in result
    
    def test_format_live_captions_latest_turn(self):
        """Should show latest turn in captions."""
        app = GradioDemoApp()
        state = {
            "history": [
                {"speaker": "human", "transcript": "First"},
                {"speaker": "ai", "transcript": "Second"}
            ]
        }
        
        result = app.format_live_captions(state)
        
        assert "Second" in result
        assert "🤖" in result
    
    def test_format_session_info_connected(self):
        """Should format connected session info."""
        app = GradioDemoApp()
        state = {
            "turn_id": 5,
            "is_processing": False,
            "history": [{"turn_id": 1}, {"turn_id": 2}],
            "phase": {"current_phase_id": "main", "phase_index": 1, "total_phases": 3},
            "speaker": {"speaker": "ai"}
        }
        
        result = app.format_session_info(state)
        
        assert result["connected"] is True
        assert result["current_turn_id"] == 5
        assert result["total_turns"] == 2
        assert result["phase_progress"] == "2/3"  # phase_index starts at 0, so index 1 = phase 2
    
    def test_format_session_info_error(self):
        """Should format error session info."""
        app = GradioDemoApp()
        state = {"error": "Connection failed"}
        
        result = app.format_session_info(state)
        
        assert result["connected"] is False
        assert "Connection failed" in result["error"]


class TestErrorRecovery:
    """Test error handling and recovery."""
    
    @patch('gradio_demo.requests.get')
    def test_handles_api_down(self, mock_get):
        """Should gracefully handle API being down."""
        import requests
        app = GradioDemoApp()
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        result = app.get_full_state()
        
        assert "error" in result
        assert "Cannot connect" in result["error"]
        assert result["phase"] is None
    
    @patch('gradio_demo.requests.get')
    def test_handles_malformed_json(self, mock_get):
        """Should handle malformed API responses."""
        app = GradioDemoApp()
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = app.get_full_state()
        
        assert "error" in result
    
    def test_display_handles_missing_fields(self):
        """Should handle missing fields in state gracefully."""
        app = GradioDemoApp()
        minimal_state = {"speaker": {}}
        
        # Should not raise exceptions
        label, probs = app.format_speaker_status(minimal_state)
        assert label is not None


class TestAutoRefresh:
    """Test manual refresh functionality."""
    
    def test_refresh_button_available(self):
        """Should have manual refresh button."""
        # Gradio 6.0 uses manual refresh instead of every=0.5
        # Test verifies refresh mechanism exists
        app = GradioDemoApp()
        interface = app.build_interface()
        assert interface is not None
    
    @patch('gradio_demo.requests.get')
    def test_refresh_updates_all_displays(self, mock_get):
        """Should update all displays on manual refresh."""
        app = GradioDemoApp()
        mock_response = Mock()
        mock_response.json.return_value = {
            "phase": {"phase_index": 0, "total_phases": 1, "progress": []},
            "speaker": {"speaker": "human"},
            "history": [{"turn_id": 1, "speaker": "human", "transcript": "Hi", "phase_id": "1", "timestamp": 1000000000}],
            "turn_id": 1,
            "is_processing": False
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        phase = app.format_phase_progress(app.get_full_state())
        speaker_label, _ = app.format_speaker_status(app.get_full_state())
        history = app.format_conversation_history_html(app.get_full_state())
        
        assert phase is not None
        assert speaker_label is not None
        assert history is not None


class TestAccessibility:
    """Test accessibility features."""
    
    def test_html_has_semantic_structure(self):
        """Should use semantic HTML elements."""
        app = GradioDemoApp()
        state = {
            "history": [
                {"turn_id": 1, "speaker": "human", "transcript": "Hi", "phase_id": "1", "timestamp": 1000000000}
            ]
        }
        
        result = app.format_conversation_history_html(state)
        
        assert "<div" in result
        assert "style=" in result
    
    def test_speaker_indicator_has_visual_contrast(self):
        """Should use contrasting colors for different speakers."""
        app = GradioDemoApp()
        state = {"history": []}
        
        # Colors should be different for human vs AI
        state["history"] = [{"turn_id": 1, "speaker": "human", "transcript": "x", "phase_id": "1", "timestamp": 1000000000}]
        html_human = app.format_conversation_history_html(state)
        
        state["history"] = [{"turn_id": 1, "speaker": "ai", "transcript": "x", "phase_id": "1", "timestamp": 1000000000}]
        html_ai = app.format_conversation_history_html(state)
        
        assert "#0066cc" in html_human  # Human color
        assert "#00aa00" in html_ai     # AI color
    
    def test_labels_have_descriptive_text(self):
        """Should use descriptive labels for components."""
        app = GradioDemoApp()
        
        phase_label = app.format_phase_progress({"phase": {"progress": []}})
        assert "📊" in phase_label or "Phase" in phase_label
        
        speaker_label, _ = app.format_speaker_status({"speaker": {"speaker": "human"}})
        assert len(speaker_label) > 0


class TestInitialization:
    """Test app initialization."""
    
    def test_app_default_url(self):
        """Should use default API URL."""
        app = GradioDemoApp()
        assert app.api_base == API_BASE_URL
    
    def test_app_custom_url(self):
        """Should accept custom API URL."""
        custom_url = "http://custom:9000/api"
        app = GradioDemoApp(api_base=custom_url)
        assert app.api_base == custom_url
    
    def test_app_state_initialization(self):
        """Should initialize state tracking."""
        app = GradioDemoApp()
        assert app.last_state == {}
        assert app.last_history_length == 0


# Integration tests
class TestGradioDemoIntegration:
    """End-to-end integration tests."""
    
    @patch('gradio_demo.requests.get')
    def test_full_flow_with_active_conversation(self, mock_get):
        """Should handle complete flow with active conversation."""
        app = GradioDemoApp()
        
        # Mock API responses
        mock_response = Mock()
        mock_response.json.return_value = {
            "phase": {
                "phase_index": 1,
                "total_phases": 3,
                "progress": [
                    {"name": "Warmup", "status": "completed"},
                    {"name": "Main", "status": "active", "duration_sec": 5.0}
                ]
            },
            "speaker": {"speaker": "ai"},
            "history": [
                {"turn_id": 1, "speaker": "human", "transcript": "Hi", "phase_id": "warmup", "timestamp": 1000000000},
                {"turn_id": 2, "speaker": "ai", "transcript": "Hello!", "phase_id": "main", "timestamp": 1000000001}
            ],
            "turn_id": 2,
            "is_processing": False
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        state = app.get_full_state()
        
        # Verify all displays can be generated
        phase_display = app.format_phase_progress(state)
        speaker_display, _ = app.format_speaker_status(state)
        history_display = app.format_conversation_history_html(state)
        session_info = app.format_session_info(state)
        transcript = app.get_transcript_text(state)
        
        assert "Main" in phase_display
        assert "🤖" in speaker_display
        assert "Hello!" in history_display
        assert session_info["total_turns"] == 2
        assert "Hi" in transcript and "Hello!" in transcript
