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
        """Build the Gradio interface.
        
        Returns:
            Gradio Blocks interface
        """
        with gr.Blocks(
            title="Interactive Chat AI - Gradio Demo"
        ) as demo:
            # Title
            gr.Markdown(
                "# 🎤 Interactive Chat AI - Gradio Demo\n\n"
                "Real-time demonstration of multi-phase conversational AI"
            )
            
            with gr.Row():
                # Left column: Main displays
                with gr.Column(scale=3):
                    # Phase progress
                    phase_display = gr.Markdown(
                        label="Phase Progress",
                        value="Loading..."
                    )
                    
                    # Speaker status
                    speaker_display = gr.Label(
                        label="Current Speaker",
                        num_top_classes=1,
                        value="Waiting..."
                    )
                    
                    # Live captions
                    captions_display = gr.Textbox(
                        label="Live Captions",
                        lines=2,
                        interactive=False,
                        placeholder="Waiting for speech...",
                        value="Waiting for conversation to start..."
                    )
                
                # Right column: Session info
                with gr.Column(scale=2):
                    session_info = gr.Json(
                        label="Session Information",
                        value={"status": "Loading..."}
                    )
            
            # Conversation history
            history_display = gr.HTML(
                label="Conversation History",
                value="<div style='color: #999; padding: 20px;'>No conversation yet...</div>"
            )
            
            # Transcript section (collapsible)
            with gr.Accordion("📋 Full Transcript", open=False):
                transcript_display = gr.Textbox(
                    label="Plaintext Transcript",
                    lines=12,
                    interactive=False,
                    placeholder="Full transcript will appear here"
                )
            
            # API Status
            with gr.Accordion("ℹ️ API Information", open=False):
                api_info = gr.Markdown(
                    f"**API Base URL**: {self.api_base}\n\n"
                    "Make sure the server is running:\n"
                    "```bash\npython -m interactive_chat.main --no-gradio\n```"
                )
            
            # Controls
            with gr.Row():
                refresh_btn = gr.Button(
                    "🔄 Refresh Now",
                    variant="primary",
                    scale=1
                )
                copy_btn = gr.Button(
                    "📋 Copy Transcript",
                    scale=1
                )
            
            # ================================================================
            # PHASE 4: INTERACTIVE CONTROLS
            # ================================================================
            gr.Markdown("## 🎮 Interactive Controls")
            
            # Text input for sending messages
            with gr.Row():
                text_input = gr.Textbox(
                    label="Send Text Input (simulates voice transcription)",
                    placeholder="Type your message here...",
                    lines=2
                )
                send_btn = gr.Button(
                    "📤 Send",
                    variant="primary",
                    scale=0,
                    min_width=80
                )
            
            # Engine control buttons
            with gr.Row():
                start_btn = gr.Button(
                    "▶️ Start",
                    variant="primary",
                    scale=1
                )
                pause_btn = gr.Button(
                    "⏸️ Pause",
                    scale=1
                )
                resume_btn = gr.Button(
                    "▶️ Resume",
                    scale=1
                )
                stop_btn = gr.Button(
                    "⏹️ Stop",
                    variant="stop",
                    scale=1
                )
            
            # Conversation reset
            with gr.Row():
                reset_profile_btn = gr.Button(
                    "🔄 Reset (Keep Profile)",
                    scale=2
                )
                reset_all_btn = gr.Button(
                    "🔄 Reset (New Profile)",
                    variant="stop",
                    scale=2
                )
            
            # Status message
            status_display = gr.Textbox(
                label="Status",
                interactive=False,
                value="✅ Initializing...",
                lines=1
            )
            
            # Update function - fetches from API and updates all displays
            def update_all_displays():
                """Fetch state and update all displays."""
                state = self.get_full_state()
                
                phase_md = self.format_phase_progress(state)
                speaker_label, speaker_probs = self.format_speaker_status(state)
                captions = self.format_live_captions(state)
                session_json = self.format_session_info(state)
                history_html = self.format_conversation_history_html(state)
                transcript = self.get_transcript_text(state)
                
                # Status message
                if "error" in state:
                    status = f"🔴 {state['error']}"
                else:
                    turn_count = len(state.get("history", []))
                    is_processing = state.get("is_processing", False)
                    processing_str = " (Processing turn...)" if is_processing else ""
                    status = f"✅ Connected | {turn_count} turns{processing_str}"
                
                # Return values in correct order for Gradio 6.0
                # Note: speaker_label is the display value for the Label component
                return [
                    phase_md,
                    speaker_label,  # For gr.Label, just return the string directly
                    captions,
                    session_json,
                    history_html,
                    transcript,
                    status
                ]
            
            # ================================================================
            # PHASE 4: EVENT HANDLERS FOR CONTROLS
            # ================================================================
            
            def handle_text_submit(text: str):
                """Handle text input submission."""
                msg = self.send_text_input(text)
                # Update displays after sending
                time.sleep(0.2)  # Brief delay for engine processing
                displays = update_all_displays()
                return [msg] + displays + [""]  # Clear text input
            
            def handle_start():
                """Handle start button."""
                msg = self.send_engine_command("start")
                time.sleep(0.2)
                displays = update_all_displays()
                return [msg] + displays
            
            def handle_pause():
                """Handle pause button."""
                msg = self.send_engine_command("pause")
                time.sleep(0.2)
                displays = update_all_displays()
                return [msg] + displays
            
            def handle_resume():
                """Handle resume button."""
                msg = self.send_engine_command("resume")
                time.sleep(0.2)
                displays = update_all_displays()
                return [msg] + displays
            
            def handle_stop():
                """Handle stop button."""
                msg = self.send_engine_command("stop")
                time.sleep(0.2)
                displays = update_all_displays()
                return [msg] + displays
            
            def handle_reset_profile():
                """Handle reset with profile."""
                msg = self.reset_conversation(keep_profile=True)
                time.sleep(0.2)
                displays = update_all_displays()
                return [msg] + displays
            
            def handle_reset_all():
                """Handle reset all."""
                msg = self.reset_conversation(keep_profile=False)
                time.sleep(0.2)
                displays = update_all_displays()
                return [msg] + displays
            
            # Wire up control handlers
            send_btn.click(
                handle_text_submit,
                inputs=text_input,
                outputs=[
                    status_display,
                    phase_display,
                    speaker_display,
                    captions_display,
                    session_info,
                    history_display,
                    transcript_display,
                    text_input
                ]
            )
            
            start_btn.click(
                handle_start,
                outputs=[
                    status_display,
                    phase_display,
                    speaker_display,
                    captions_display,
                    session_info,
                    history_display,
                    transcript_display
                ]
            )
            
            pause_btn.click(
                handle_pause,
                outputs=[
                    status_display,
                    phase_display,
                    speaker_display,
                    captions_display,
                    session_info,
                    history_display,
                    transcript_display
                ]
            )
            
            resume_btn.click(
                handle_resume,
                outputs=[
                    status_display,
                    phase_display,
                    speaker_display,
                    captions_display,
                    session_info,
                    history_display,
                    transcript_display
                ]
            )
            
            stop_btn.click(
                handle_stop,
                outputs=[
                    status_display,
                    phase_display,
                    speaker_display,
                    captions_display,
                    session_info,
                    history_display,
                    transcript_display
                ]
            )
            
            reset_profile_btn.click(
                handle_reset_profile,
                outputs=[
                    status_display,
                    phase_display,
                    speaker_display,
                    captions_display,
                    session_info,
                    history_display,
                    transcript_display
                ]
            )
            
            reset_all_btn.click(
                handle_reset_all,
                outputs=[
                    status_display,
                    phase_display,
                    speaker_display,
                    captions_display,
                    session_info,
                    history_display,
                    transcript_display
                ]
            )
            
            # Refresh button
            refresh_btn.click(
                update_all_displays,
                outputs=[
                    phase_display,
                    speaker_display,
                    captions_display,
                    session_info,
                    history_display,
                    transcript_display,
                    status_display
                ]
            )
            
            # Copy transcript button
            def copy_transcript():
                """Return full transcript for manual copying."""
                state = self.get_full_state()
                return self.get_transcript_text(state)
            
            copy_btn.click(
                copy_transcript,
                outputs=transcript_display
            )
            
            # Initial load on page load
            demo.load(
                update_all_displays,
                outputs=[
                    phase_display,
                    speaker_display,
                    captions_display,
                    session_info,
                    history_display,
                    transcript_display,
                    status_display
                ]
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
            .phase-display { font-family: monospace; }
        """
    )


if __name__ == "__main__":
    main()
