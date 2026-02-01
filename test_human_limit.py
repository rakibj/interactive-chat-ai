"""Quick test of human speaking limit logic."""
import time
import random

# Config
profiles = {
    "ielts": {
        "human_speaking_limit_sec": 5,
        "acknowledgments": ["Thank you.", "Good.", "I see.", "Excellent.", "Right.", "Got it."],
    }
}

profile = profiles["ielts"]

# Simulate human speaking durations (in seconds)
test_durations = [2, 4, 6, 8, 10, 3, 5.5, 7]

for i, duration in enumerate(test_durations, 1):
    human_speech_start_time = time.time()
    human_speaking_limit_ack_sent = False
    
    print(f"\nTurn {i}: Simulating human speaking for {duration}s")
    
    # Simulate frames coming in every 32ms (1 frame = 512 samples @ 16kHz)
    frame_interval = 0.032
    elapsed = 0
    
    while elapsed < duration:
        now = time.time() - (time.time() - human_speech_start_time) + elapsed
        
        # Check limit
        limit_sec = profile.get("human_speaking_limit_sec")
        if limit_sec is not None and not human_speaking_limit_ack_sent:
            speaking_duration = elapsed
            if speaking_duration > limit_sec:
                ack = random.choice(profile["acknowledgments"])
                print(f"  ⏰ LIMIT EXCEEDED ({speaking_duration:.1f}s > {limit_sec}s) → will prepend: '{ack}'")
                human_speaking_limit_ack_sent = True
        
        elapsed += frame_interval
        time.sleep(frame_interval * 0.1)  # Speed up simulation
    
    print(f"  ✓ Turn ended (final duration: {duration}s, ack_sent={human_speaking_limit_ack_sent})")

print("\n✅ Test complete!")
