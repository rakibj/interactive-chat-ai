"""Gradio demo for Interactive Chat AI - Real-time conversation visualization."""

import gradio as gr
import requests
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import threading
import time


API_BASE_URL = "http://localhost:8000/api"


class GradioDemoApp:
    """Interactive Chat AI Gradio Demo with real-time updates."""
    
    def __init__(self, api_base: str = API_BASE_URL):
        """Initialize Gradio demo app.
        
        Args:
            api_base: Base URL for API (default: http://localhost:8000/api)
        """
        self.api_base = api_base
        self.last_state = {}
        self.last_history_length = 0
    
    def get_full_state(self) -> Dict[str, Any]:
        """Fetch complete state from API.
        
        Returns:
            Dictionary with phase, speaker, history, turn_id, is_processing
        """
        try:
            response = requests.get(
                f"{self.api_base}/state",
                timeout=2.0
            )
            response.raise_for_status()
            self.last_state = response.json()
            return self.last_state
        except requests.exceptions.ConnectionError:
            return {
                "error": "Cannot connect to API (http://localhost:8000)",
                "error_type": "connection",
                "phase": None,
                "speaker": None,
                "history": [],
                "turn_id": 0,
                "is_processing": False
            }
        except requests.exceptions.Timeout:
            return {
                "error": "API request timed out",
                "error_type": "timeout",
                "phase": None,
                "speaker": None,
                "history": [],
                "turn_id": 0,
                "is_processing": False
            }
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "Unknown"
            return {
                "error": f"API error: {status_code}",
                "error_type": "http",
                "phase": None,
                "speaker": None,
                "history": [],
                "turn_id": 0,
                "is_processing": False
            }
        except Exception as e:
            return {
                "error": f"Error: {str(e)}",
                "error_type": "unknown",
                "phase": None,
                "speaker": None,
                "history": [],
                "turn_id": 0,
                "is_processing": False
            }
    
    def get_api_limitations(self) -> List[Dict[str, str]]:
        """Get API limitations from /api/limitations endpoint.
        
        Returns:
            List of APILimitation objects
        """
        try:
            response = requests.get(
                f"{self.api_base}/limitations",
                timeout=2.0
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return []
    
    def format_phase_progress(self, state: Dict[str, Any]) -> str:
        """Format phase progress as markdown with visual indicators.
        
        Args:
            state: Full state from API
            
        Returns:
            Markdown-formatted phase progress
        """
        if "error" in state or state.get("phase") is None:
            return "### 📊 Phase Progress\n\n⚠️ **No phase data available**\n\nStart a conversation to see phases."
        
        phase_data = state.get("phase", {})
        progress = phase_data.get("progress", [])
        current_phase_name = phase_data.get("phase_name", "Unknown")
        phase_index = phase_data.get("phase_index", 0)
        total_phases = phase_data.get("total_phases", 0)
        
        markdown = f"### 📊 Phase Progress ({phase_index + 1}/{total_phases})\n\n"
        
        if not progress:
            markdown += "No phases available\n"
            return markdown
        
        for i, phase in enumerate(progress):
            status = phase.get("status", "unknown")
            phase_name = phase.get("name", "Unknown")
            duration = phase.get("duration_sec")
            
            # Status icons
            status_icons = {
                "completed": "✅",
                "active": "🔵",
                "upcoming": "⭕"
            }
            icon = status_icons.get(status, "❓")
            
            # Duration string
            duration_str = f" ({duration:.1f}s)" if duration else ""
            
            # Highlight active phase
            if status == "active":
                markdown += f"{icon} **{phase_name}**{duration_str} ← Current\n\n"
            else:
                markdown += f"{icon} {phase_name}{duration_str}\n\n"
        
        return markdown
    
    def format_speaker_status(self, state: Dict[str, Any]) -> Tuple[str, Dict[str, float]]:
        """Format speaker status for display.
        
        Args:
            state: Full state from API
            
        Returns:
            Tuple of (status_label, speaker_probs_dict)
        """
        if "error" in state or state.get("speaker") is None:
            return "Waiting for data...", {"unknown": 1.0}
        
        speaker_data = state.get("speaker", {})
        speaker = speaker_data.get("speaker", "unknown")
        
        # Create probability dict for gr.Label
        indicators = {
            "human": {"🎤 HUMAN Speaking": 1.0},
            "ai": {"🤖 AI Speaking": 1.0},
            "silence": {"⏸️ SILENCE (Waiting)": 1.0},
            "unknown": {"❓ Unknown": 1.0}
        }
        
        probs = indicators.get(speaker, indicators["unknown"])
        label = list(probs.keys())[0]
        
        return label, probs
    
    def format_live_captions(self, state: Dict[str, Any]) -> str:
        """Get latest transcript for live captions.
        
        Args:
            state: Full state from API
            
        Returns:
            Latest transcript or placeholder
        """
        if "error" in state:
            return f"🔴 {state.get('error', 'API Error')}"
        
        history = state.get("history", [])
        if not history:
            return "Waiting for conversation to start..."
        
        latest_turn = history[-1]
        speaker = latest_turn.get("speaker", "?").upper()
        transcript = latest_turn.get("transcript", "")
        
        speaker_prefix = "🎤" if speaker == "HUMAN" else "🤖"
        return f"{speaker_prefix} {speaker}: {transcript}"
    
    def format_conversation_history_html(self, state: Dict[str, Any]) -> str:
        """Format conversation history as HTML.
        
        Args:
            state: Full state from API
            
        Returns:
            HTML string for conversation display
        """
        if "error" in state:
            return f"<div style='color: red; padding: 20px;'><strong>Error:</strong> {state.get('error', 'Unknown error')}</div>"
        
        history = state.get("history", [])
        if not history:
            return "<div style='color: #999; padding: 20px;'>No conversation yet...</div>"
        
        html = "<div style='max-height: 600px; overflow-y: auto; padding: 10px;'>"
        
        for turn in history:
            speaker = turn.get("speaker", "unknown").upper()
            transcript = turn.get("transcript", "")
            phase_id = turn.get("phase_id", "?")
            timestamp = turn.get("timestamp", 0)
            latency = turn.get("latency_ms")
            duration = turn.get("duration_sec")
            turn_id = turn.get("turn_id", "?")
            
            # Format timestamp
            try:
                time_obj = datetime.fromtimestamp(timestamp)
                time_str = time_obj.strftime("%H:%M:%S")
            except:
                time_str = "?"
            
            # Color code by speaker
            if speaker == "HUMAN":
                speaker_color = "#0066cc"
                speaker_icon = "🎤"
                bg_color = "#f0f4ff"
            else:
                speaker_color = "#00aa00"
                speaker_icon = "🤖"
                bg_color = "#f0fff0"
            
            # Metadata
            metadata = f"Turn #{turn_id} • {phase_id} • {time_str}"
            if duration:
                metadata += f" • {duration:.1f}s"
            if latency:
                metadata += f" • {latency}ms latency"
            
            html += f"""
            <div style='
                margin: 12px 0;
                padding: 12px;
                border-left: 4px solid {speaker_color};
                background: {bg_color};
                border-radius: 4px;
            '>
                <div style='color: {speaker_color}; font-weight: bold; margin-bottom: 6px; font-size: 14px;'>
                    {speaker_icon} {speaker}
                </div>
                <div style='color: #333; word-wrap: break-word; margin-bottom: 6px; line-height: 1.4;'>
                    {transcript}
                </div>
                <div style='color: #999; font-size: 12px;'>
                    {metadata}
                </div>
            </div>
            """
        
        html += "</div>"
        return html
    
    def format_session_info(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format session info for JSON display.
        
        Args:
            state: Full state from API
            
        Returns:
            Dictionary with session information
        """
        if "error" in state:
            return {
                "status": "Error",
                "error": state.get("error"),
                "connected": False
            }
        
        history = state.get("history", [])
        phase = state.get("phase", {})
        speaker = state.get("speaker", {})
        
        return {
            "connected": True,
            "current_turn_id": state.get("turn_id", 0),
            "is_processing": state.get("is_processing", False),
            "total_turns": len(history),
            "current_phase": phase.get("current_phase_id", "?"),
            "phase_progress": f"{phase.get('phase_index', 0) + 1}/{phase.get('total_phases', 0)}",
            "current_speaker": speaker.get("speaker", "?"),
            "latest_turn_latency_ms": history[-1].get("latency_ms") if history else None
        }
    
    def get_transcript_text(self, state: Dict[str, Any]) -> str:
        """Extract full transcript as text.
        
        Args:
            state: Full state from API
            
        Returns:
            Plaintext transcript
        """
        if "error" in state or not state.get("history"):
            return "No transcript available.\n\nStart a conversation to see transcript."
        
        history = state.get("history", [])
        lines = []
        
        for turn in history:
            speaker = turn.get("speaker", "?").upper()
            transcript = turn.get("transcript", "")
            turn_id = turn.get("turn_id", "?")
            phase_id = turn.get("phase_id", "?")
            
            lines.append(f"[Turn {turn_id} - {phase_id}] {speaker}: {transcript}")
        
        return "\n".join(lines)
    
    # ========================================================================
    # PHASE 4: CONTROL METHODS
    # ========================================================================
    
    def send_text_input(self, text: str) -> str:
        """Send text input to engine via /api/conversation/text-input.
        
        Args:
            text: User input text
            
        Returns:
            Status message
        """
        if not text or not text.strip():
            return "❌ Please enter some text"
        
        try:
            response = requests.post(
                f"{self.api_base}/conversation/text-input",
                json={"text": text.strip()},
                timeout=5.0
            )
            response.raise_for_status()
            return "✅ Text sent to engine"
        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to API"
        except requests.exceptions.Timeout:
            return "❌ Request timeout"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def send_engine_command(self, command: str) -> str:
        """Send control command to engine.
        
        Args:
            command: Command: 'start', 'stop', 'pause', or 'resume'
            
        Returns:
            Status message
        """
        try:
            response = requests.post(
                f"{self.api_base}/engine/command",
                json={"command": command},
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            return f"✅ {data.get('message', 'Command executed')}"
        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to API"
        except requests.exceptions.Timeout:
            return "❌ Request timeout"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def reset_conversation(self, keep_profile: bool = True) -> str:
        """Reset conversation.
        
        Args:
            keep_profile: Keep current profile (True) or reset phase (False)
            
        Returns:
            Status message
        """
        try:
            response = requests.post(
                f"{self.api_base}/conversation/reset",
                json={"keep_profile": keep_profile},
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            return f"✅ {data.get('message', 'Conversation reset')}"
        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to API"
        except requests.exceptions.Timeout:
            return "❌ Request timeout"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def build_interface(self) -> gr.Blocks:
        """Build the Gradio interface (simplified).
        
        Returns:
            Gradio Blocks interface
        """
        with gr.Blocks(
            title="Interactive Chat AI"
        ) as demo:
            # Title
            gr.Markdown("# 🎤 Interactive Chat AI")
            
            # Speaker status
            speaker_display = gr.Label(
                label="🎤 Current Speaker",
                num_top_classes=1,
                value="Waiting..."
            )
            
            # Transcript
            transcript_display = gr.Textbox(
                label="📋 Transcript",
                lines=15,
                interactive=False,
                placeholder="Transcript will appear here",
                value="Start conversation to see transcript..."
            )
            
            # Control buttons - Start/Stop toggle
            with gr.Row():
                # State tracking for button visibility
                is_running = gr.State(False)
                
                start_btn = gr.Button(
                    "▶️ Start",
                    variant="primary",
                    scale=1,
                    visible=True
                )
                stop_btn = gr.Button(
                    "⏹️ Stop",
                    variant="stop",
                    scale=1,
                    visible=False
                )
                refresh_btn = gr.Button(
                    "🔄 Refresh",
                    scale=1
                )
            
            # Hidden components for auto-refresh
            timer = gr.State(value=0)
            auto_update = gr.Textbox(visible=False, value="0")
            
            # Update function - fetch transcript and speaker
            def update_display():
                """Fetch state and update displays."""
                state = self.get_full_state()
                speaker_label, _ = self.format_speaker_status(state)
                transcript = self.get_transcript_text(state)
                return [speaker_label, transcript]
            
            # Event handlers
            def handle_start():
                """Handle start button - send start command."""
                self.send_engine_command("start")
                time.sleep(0.3)
                speaker, transcript = update_display()
                # Return: speaker, transcript, new is_running state, start visible, stop visible
                return [speaker, transcript, True, gr.update(visible=False), gr.update(visible=True)]
            
            def handle_stop():
                """Handle stop button - send stop command."""
                self.send_engine_command("stop")
                time.sleep(0.3)
                speaker, transcript = update_display()
                # Return: speaker, transcript, new is_running state, start visible, stop visible
                return [speaker, transcript, False, gr.update(visible=True), gr.update(visible=False)]
            
            def handle_refresh(dummy_input):
                """Handle refresh - also updates auto_update to trigger refresh."""
                speaker, transcript = update_display()
                # Return speaker, transcript, and increment auto_update to trigger next refresh
                return [speaker, transcript, str(int(time.time()))]
            
            # Wire up button handlers
            start_btn.click(
                handle_start,
                outputs=[speaker_display, transcript_display, is_running, start_btn, stop_btn]
            )
            
            stop_btn.click(
                handle_stop,
                outputs=[speaker_display, transcript_display, is_running, start_btn, stop_btn]
            )
            
            # Refresh button updates auto_update which triggers auto-refresh
            refresh_btn.click(
                handle_refresh,
                inputs=[auto_update],
                outputs=[speaker_display, transcript_display, auto_update]
            )
            
            # Auto-refresh every 500ms - update display whenever auto_update changes
            auto_update.change(
                handle_refresh,
                inputs=[auto_update],
                outputs=[speaker_display, transcript_display, auto_update]
            )
            
            # Initial load and continuous refresh
            def initial_load():
                """Initial load and start auto-refresh timer."""
                speaker, transcript = update_display()
                # Start a background thread that updates auto_update every 500ms
                def refresh_loop():
                    while True:
                        time.sleep(0.5)
                        # This would ideally trigger auto_update change, but Gradio doesn't support this
                        # Instead, we'll rely on manual refresh or component updates
                        pass
                # Note: Gradio doesn't easily support server-side timed updates
                # The refresh button provides manual refresh capability
                return [speaker, transcript]
            
            demo.load(
                initial_load,
                outputs=[speaker_display, transcript_display]
            )

        
        return demo


def main():
    """Launch the Gradio demo."""
    print("🎤 Interactive Chat AI - Gradio Demo")
    print("=" * 50)
    print()
    print("📍 API Base URL: http://localhost:8000/api")
    print()
    print("⚠️  Make sure the API server is running:")
    print("   python -m interactive_chat.main --no-gradio")
    print()
    print("🚀 Launching Gradio interface...")
    print("   👉 Open browser at: http://localhost:7860")
    print()
    
    app = GradioDemoApp()
    interface = app.build_interface()
    
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        theme=gr.themes.Soft(),
        css="""
            .demo-title { text-align: center; font-size: 28px; margin-bottom: 10px; }
            .demo-subtitle { text-align: center; color: #666; margin-bottom: 20px; }
            .status-connected { color: #00aa00; font-weight: bold; }
            .status-error { color: #cc0000; font-weight: bold; }
        """,
        head="<script>setInterval(() => { let btn = document.querySelector('button:nth-child(3)'); if (btn && btn.textContent.includes('Refresh')) btn.click(); }, 500);</script>"
    )


if __name__ == "__main__":
    main()
