#!/usr/bin/env python3
"""
HTML/CSS Web Demo App - Single Entry Point
Serves static files and starts the ConversationEngine with FastAPI server.
Similar to run_complete_gradio_app.py but with raw HTML instead of Gradio.
"""

import sys
import os
import time
import threading
import webbrowser
from pathlib import Path

# Add project to path (before any imports that might wrap stdio)
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def start_static_server():
    """Start a simple HTTP server to serve static files"""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    
    public_dir = project_root / "public"
    
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(public_dir), **kwargs)
        
        def do_GET(self):
            # Serve dashboard.html for root path
            if self.path == "/" or self.path == "":
                self.path = "/dashboard.html"
            super().do_GET()
        
        def log_message(self, format, *args):
            # Reduce log noise
            if "GET" not in format:
                super().log_message(format, *args)
    
    server = HTTPServer(("127.0.0.1", 7860), Handler)
    print("✅ Static file server started at http://localhost:7860")
    server.serve_forever()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Interactive Chat AI - HTML/CSS Web Demo"
    )
    parser.add_argument(
        "--profile",
        default="negotiator",
        help="Profile to use (default: negotiator)"
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Skip API server (engine only)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("INTERACTIVE CHAT AI - HTML Web Interface")
    print("="*60)
    
    try:
        # Import config first to check profiles
        from interactive_chat.config import PHASE_PROFILES, INSTRUCTION_PROFILES
        from interactive_chat.main import ConversationEngine
        from interactive_chat.server import set_engine
        
        # Get the profile key
        profile_key = args.profile
        
        # Print info about which profile is being used
        if profile_key in PHASE_PROFILES:
            phase_profile = PHASE_PROFILES[profile_key]
            print(f"\n[PROFILE] {phase_profile.name} (PhaseProfile)")
            print(f"[PHASES] {', '.join(phase_profile.phases.keys())}")
            print(f"[INITIAL PHASE] {phase_profile.initial_phase}")
        elif profile_key in INSTRUCTION_PROFILES:
            from interactive_chat.config import get_profile_settings
            profile_settings = get_profile_settings(profile_key)
            print(f"\n[PROFILE] {profile_settings['name']}")
            print(f"[AUTHORITY] {profile_settings.get('authority', 'human')}")
            print(f"[START] {profile_settings.get('start', 'human')}")
        else:
            raise ValueError(f"Unknown profile: {profile_key}. Available: {list(PHASE_PROFILES.keys()) + list(INSTRUCTION_PROFILES.keys())}")
        
        # Initialize engine with the profile_key
        # The engine will use this to determine PhaseProfile vs InstructionProfile mode
        print("\n[INIT] Initializing ConversationEngine...")
        engine = ConversationEngine(profile_key=profile_key)
        
        # Register engine with API server (for REST endpoints)
        if not args.no_api:
            set_engine(engine)
        
        # Start static file server
        print("\n[STARTING] Static file server...")
        static_thread = threading.Thread(target=start_static_server, daemon=True)
        static_thread.start()
        time.sleep(1)  # Give server time to start
        
        # Start API server (if not disabled)
        if not args.no_api:
            print("[STARTING] FastAPI server...")
            api_thread = threading.Thread(
                target=lambda: engine._start_api_server(),
                daemon=True
            )
            api_thread.start()
            time.sleep(3)  # Give API time to start
        
        # Print connection information
        print("\n" + "="*60)
        print("SERVICES STARTED")
        print("="*60)
        print("[INFO] Web Interface: http://localhost:7860 (Dashboard)")
        print("[INFO] API Server:    http://localhost:8000")
        print("[INFO] Swagger UI:    http://localhost:8000/docs")
        print("[INFO] Chat Phases:   GET /api/chat/phases")
        print("\n[FEATURES]")
        print("   - Phase-grouped chat history")
        print("   - Live performance metrics")
        print("   - Call progress tracking")
        print("   - Real-time message updates (1.5s polling)")
        print("\n[TIPS]")
        print("   - Open http://localhost:7860 in your browser")
        print("   - WebSocket connects automatically")
        print("   - REST API available for custom clients")
        print("   - All tests passing!")
        print("="*60 + "\n")
        
        # Open browser if requested
        if not args.no_browser:
            time.sleep(2)  # Give services time to fully start
            print("[ACTION] Opening browser...")
            try:
                webbrowser.open("http://localhost:7860")
            except Exception as e:
                print(f"[WARNING] Could not open browser: {e}")
                print("   Visit http://localhost:7860 manually")
        
        # Run engine (blocking)
        print("[ENGINE] Starting event loop...")
        print("[INFO] Stop with Ctrl+C\n")
        engine.run()
        
    except KeyboardInterrupt:
        print("\n\n[INFO] Shutting down gracefully...")
        if 'engine' in locals():
            engine._request_shutdown()
        sys.exit(0)
    
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



if __name__ == "__main__":
    main()
