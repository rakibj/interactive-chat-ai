#!/usr/bin/env python3
"""
Test Interruption Actuation
---------------------------
Verifies that setting the 'interrupt' event actually stops the TTS output pipeline.
Mimics the threading model of the main ConversationEngine.
Uses MockTTS to ensure deterministic timing logic.
"""
import os
import sys
import time
import queue
import threading

# Mock Global State
response_queue = queue.Queue()
human_interrupt_event = threading.Event()
stop_worker_event = threading.Event()

class MockTTS:
    """Simulates TTS by sleeping in chunks to allow mid-sentence interruption."""
    
    def speak(self, text: str, interrupt_event: threading.Event = None):
        print(f"   [MockTTS] speaking: '{text[:15]}...' (Duration: 2.0s)")
        
        # Simulate 2.0s duration in 0.1s chunks
        for _ in range(20):
            if interrupt_event and interrupt_event.is_set():
                print("   [MockTTS] 🛑 HALT: Immediate Interruption triggered inside TTS!")
                return
            time.sleep(0.1)
        
        print("   [MockTTS] Finished speaking.")

def tts_worker(tts, authority_mode="human"):
    """Worker thread that consumes text and speaks it, checking for interrupts."""
    print(f"👷 Worker: Started (Authority: {authority_mode})")
    
    while not stop_worker_event.is_set():
        try:
            # Check interrupt before getting (fast exit)
            if human_interrupt_event.is_set():
                with response_queue.mutex:
                    if response_queue.qsize() > 0:
                        print(f"🛑 Worker: Queue not empty ({response_queue.qsize()}), clearing...")
                        response_queue.queue.clear()
            
            text = response_queue.get(timeout=0.1)
            
            # 1. Pre-speech check
            if human_interrupt_event.is_set():
                print(f"🛑 Worker: Interrupt detected BEFORE speaking '{text[:15]}...' - Dropping")
                continue
            
            print(f"🔊 Worker: Speaking '{text[:30]}...'")
            
            # Determine logic based on authority
            event_to_pass = None
            if authority_mode == "human":
                event_to_pass = human_interrupt_event
                
            start_time = time.time()
            tts.speak(text, interrupt_event=event_to_pass)
            duration = time.time() - start_time
            print(f"   -> Speech Duration: {duration:.2f}s")
            
            # 2. Post-speech check
            if human_interrupt_event.is_set():
                print(f"🛑 Worker: Interrupt detected AFTER speaking - Clearing remaining queue")
                with response_queue.mutex:
                    response_queue.queue.clear()
                
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ Worker Error: {e}")

    print("👷 Worker: Stopped")


def run_test(authority_mode):
    print(f"\n==================================================")
    print(f"🎬 TEST SCENARIO: Authority = {authority_mode}")
    print(f"==================================================")
    
    # Reset State
    with response_queue.mutex:
        response_queue.queue.clear()
    human_interrupt_event.clear()
    stop_worker_event.clear()
    
    tts = MockTTS()
    worker = threading.Thread(target=tts_worker, args=(tts, authority_mode), daemon=True)
    worker.start()
    
    # Queue items
    response_queue.put("Sentence 1 (Target)")
    response_queue.put("Sentence 2 (Skipped)")
    
    # Allow S1 to start (MockTTS takes 2.0s)
    print(f"   [1] Sleeping 0.5s (S1 starts)...")
    time.sleep(0.5)
    
    # Trigger Interrupt
    print(f"⚡ [2] INTERRUPT TRIGGERED!")
    human_interrupt_event.set()
    
    # Wait for S1 to "finish" (either early or late)
    time.sleep(2.0)
    
    stop_worker_event.set()
    worker.join(timeout=1.0)

def main():
    # TEST 1: HUMAN Authority (Immediate Stop)
    # Expected: S1 stops around 0.5s (immediate reaction)
    run_test("human")
    
    # TEST 2: DEFAULT Authority (Polite Stop)
    # Expected: S1 plays FULL 2.0s, THEN S2 is skipped
    run_test("default")

if __name__ == "__main__":
    main()
