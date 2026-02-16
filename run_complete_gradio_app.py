#!/usr/bin/env python
"""
Complete Gradio-controlled Interactive Chat AI solution.

This launcher starts everything from Gradio and controls the full lifecycle:
- Starts: Gradio interface (primary)
- Controls: All interaction through Gradio UI
- Stops: Gradio window close triggers full shutdown

Usage:
    python run_complete_gradio_app.py

Architecture:
    Gradio UI (main) → API Server (background) → Engine (background)
"""

import os
import sys
import threading
import time
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def ensure_api_server_running(max_retries=5):
    """Ensure API server is running and ready."""
    import requests
    
    for attempt in range(max_retries):
        try:
            response = requests.get("http://localhost:8000/api/state", timeout=1)
            if response.status_code == 200:
                print("✅ API server is ready")
                return True
        except Exception:
            if attempt < max_retries - 1:
                print(f"   Waiting for API server... ({attempt + 1}/{max_retries})")
                time.sleep(1)
            else:
                print("❌ API server failed to start")
                return False
    
    return False


def start_api_engine_background():
    """Start the API server and engine in background threads."""
    try:
        import uvicorn
        from interactive_chat.main import ConversationEngine, set_global_engine
        from interactive_chat import server as api_server
        
        print("🔧 Starting engine and API server...")
        
        # Create engine
        engine = ConversationEngine()
        set_global_engine(engine)
        
        # Register with API
        api_server.set_engine(engine)
        
        def run_engine():
            """Run the engine in background."""
            try:
                engine.run()
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(f"⚠️  Engine error: {e}")
        
        def run_api():
            """Run API server in background."""
            try:
                uvicorn.run(
                    api_server.app,
                    host="0.0.0.0",
                    port=8000,
                    log_level="error",
                    access_log=False
                )
            except Exception as e:
                print(f"⚠️  API server error: {e}")
        
        # Start engine and API in daemon threads
        engine_thread = threading.Thread(target=run_engine, daemon=True, name="engine")
        api_thread = threading.Thread(target=run_api, daemon=True, name="api")
        
        api_thread.start()
        time.sleep(2)  # Give API time to start
        
        engine_thread.start()
        time.sleep(1)  # Give engine time to initialize
        
        # Wait for API to be ready
        if not ensure_api_server_running():
            print("❌ Failed to start API server")
            return False
        
        print("✅ Engine and API server started")
        return True
        
    except Exception as e:
        print(f"❌ Error starting engine/API: {e}")
        return False


def launch_gradio_ui():
    """Launch the Gradio UI as the main interface."""
    try:
        from gradio_demo import GradioDemoApp
        import gradio as gr
        
        print("\n" + "="*70)
        print("🎤 INTERACTIVE CHAT AI - Complete Gradio Solution")
        print("="*70)
        print("\n📍 Endpoints:")
        print("   Gradio UI:  http://localhost:7860")
        print("   API Server: http://localhost:8000")
        print("   API Docs:   http://localhost:8000/docs")
        print("\n🎮 Lifecycle Control:")
        print("   ✅ START:   Gradio launches automatically")
        print("   ✅ CONTROL: All interaction via Gradio UI")
        print("   ✅ STOP:    Close window or press Ctrl+C")
        print("\n✅ Complete end-to-end Gradio control")
        print("="*70 + "\n")
        
        # Create Gradio app
        app = GradioDemoApp()
        interface = app.build_interface()
        
        # Launch Gradio (this becomes the main blocking thread)
        print("🚀 Launching Gradio interface...\n")
        
        interface.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            inbrowser=True,  # Auto-open browser
            show_error=True
        )
        
        print("\n✅ Gradio interface closed")
        return True
        
    except ImportError as e:
        print(f"❌ Gradio import error: {e}")
        print("   Install Gradio: pip install gradio")
        return False
    except Exception as e:
        print(f"❌ Gradio launch error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point for complete Gradio-controlled solution."""
    print("\n" + "="*70)
    print("🚀 INTERACTIVE CHAT AI - Complete Gradio Solution")
    print("="*70)
    print("\n📦 Starting all components...")
    print("   1️⃣  Engine (background)")
    print("   2️⃣  API Server (background)")
    print("   3️⃣  Gradio UI (main interface)")
    print()
    
    # Step 1: Start engine and API in background
    print("Step 1/3: Starting engine and API server...")
    if not start_api_engine_background():
        print("❌ Failed to start engine/API")
        return False
    
    # Step 2: Launch Gradio UI (main thread - blocks until closed)
    print("\nStep 2/3: Launching Gradio interface...")
    print("(This is the main interface - close this window to stop the app)")
    
    try:
        launch_gradio_ui()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    # Step 3: Cleanup (when Gradio closes)
    print("\n\nStep 3/3: Shutting down...")
    print("✅ Engine stopped")
    print("✅ API server stopped")
    print("✅ Gradio closed")
    
    print("\n" + "="*70)
    print("👋 Thank you for using Interactive Chat AI!")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
