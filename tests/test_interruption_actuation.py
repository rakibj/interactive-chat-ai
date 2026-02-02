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
    """Simulates TTS by sleeping."""
    def speak(self, text: str):
        print(f"   [MockTTS] speaking: '{text[:15]}...' (2.0s)")
        time.sleep(2.0)

def tts_worker(tts):
    """Worker thread that consumes text and speaks it, checking for interrupts."""
    print("👷 Worker: Started")
    
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
                # We already cleared queue above, so just drop this one
                continue
            
            print(f"🔊 Worker: Speaking '{text[:30]}...'")
            tts.speak(text)
            
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


def main():
    print("🔌 Initializing MockTTS...")
    tts = MockTTS()

    # Start Worker
    worker = threading.Thread(target=tts_worker, args=(tts,), daemon=True)
    worker.start()
    
    # Text content
    s1 = "Sentence 1"
    s2 = "Sentence 2"
    s3 = "Sentence 3"
    
    print("\n🎬 SCENARIO START")
    print(f"   [1] Queuing 3 sentences.")
    response_queue.put(s1)
    response_queue.put(s2)
    response_queue.put(s3)
    
    # Let Sentence 1 play (MockTTS takes 2s)
    # We sleep 1s, so S1 is halfway done.
    print(f"   [2] Sleeping 1.0s (S1 is playing)...")
    time.sleep(1.0)
    
    # Interrupt!
    print(f"⚡ [3] EVENT: INTERRUPT TRIGGERED!")
    human_interrupt_event.set()
    
    # Wait 2.5s.
    # Timeline:
    # T=0: Worker starts S1 (ends at T=2.0)
    # T=1: Interrupt Set.
    # T=2.0: Worker finishes S1. Loops. Sees Interrupt.
    #        Worker should drop S2? Or if it pulled S2 already...
    #        Actually, 'text = get()' happened at T=0.
    #        S2 is is Queue.
    #        Worker finishes S1. Loops.
    #        Checks Interrupt -> Clears S2, S3.
    # T=3.5: We check.
    print(f"   [4] Sleeping 2.5s (Waiting for S1 to finish and logic to run)...")
    time.sleep(2.5)
    
    print(f"   [5] Checking queue size...")
    if response_queue.empty():
        print(f"✅ Success: Queue is empty.")
    else:
        print(f"❌ Failure: Queue still has {response_queue.qsize()} items.")
    
    # Reset for clean exit
    human_interrupt_event.clear()
    stop_worker_event.set()
    worker.join(timeout=1.0)
    print("🎬 SCENARIO END")

if __name__ == "__main__":
    main()
