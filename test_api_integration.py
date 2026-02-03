#!/usr/bin/env python3
"""Test API integration with ConversationEngine - with debugging"""
import subprocess
import time
import requests
import sys
import threading
import io

# Fix Windows Unicode console encoding
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

def read_output(proc, name):
    """Read process output in a separate thread"""
    if proc.stdout:
        for line in iter(proc.stdout.readline, ''):
            if line:
                print(f"[{name}] {line.rstrip()}")

def test_api_integration():
    """Start main.py and test API endpoints"""
    
    print("Starting ConversationEngine with API server...")
    print("-" * 60)
    
    # Start the main app
    proc = subprocess.Popen(
        [sys.executable, "-m", "interactive_chat.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Read output in a thread
    output_thread = threading.Thread(target=read_output, args=(proc, "APP"), daemon=True)
    output_thread.start()
    
    # Give it time to start
    print("\nWaiting for engine and API to initialize (10 seconds)...")
    time.sleep(10)
    
    print("-" * 60)
    print("\nTesting GET /api/state...")
    
    try:
        response = requests.get("http://localhost:8000/api/state", timeout=5)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   SUCCESS! Got state:")
            print(f"      - Current Phase: {data.get('phase', {}).get('current_phase_id')}")
            print(f"      - Speaker: {data.get('speaker', {}).get('speaker')}")
            print(f"      - Turn ID: {data.get('turn_id')}")
            print(f"      - Is Processing: {data.get('is_processing')}")
        else:
            print(f"   Error response: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"   Failed to connect to API server: {e}")
    except Exception as e:
        print(f"   Error: {e}")
    finally:
        # Stop the process
        print("\nStopping server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == "__main__":
    test_api_integration()
