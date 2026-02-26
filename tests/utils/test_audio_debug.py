#!/usr/bin/env python3
"""
Debug script to test audio input issues with the name_age_test profile.
"""
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Fix sys path for imports
from interactive_chat.core.audio_manager import AudioManager

def test_audio_manager():
    """Test if AudioManager can initialize and capture audio."""
    print("="*60)
    print("TESTING AUDIO MANAGER INITIALIZATION")
    print("="*60)
    
    try:
        print("\n1. Creating AudioManager...")
        audio_mgr = AudioManager()
        print("   ✓ AudioManager created successfully")
        
        print("\n2. Testing get_audio_chunk()...")
        for i in range(5):
            chunk = audio_mgr.get_audio_chunk()
            print(f"   Chunk {i}: size={chunk.size}, dtype={chunk.dtype}")
            time.sleep(0.2)
        
        print("\n3. Checking if stream is active...")
        if audio_mgr.stream:
            print(f"   Stream active: {audio_mgr.stream.active}")
            print(f"   Stream samplerate: {audio_mgr.stream.samplerate}")
        else:
            print("   ✗ Stream is None!")
        
        print("\n4. Listening for 3 seconds...")
        print("   Try speaking into the microphone...")
        for i in range(15):  # 15 * 0.2 = 3 seconds
            chunk = audio_mgr.get_audio_chunk()
            if chunk.size > 0:
                print(f"   ✓ Got audio chunk at {i*200}ms: {chunk.size} samples")
                speech, rms = audio_mgr.detect_speech(chunk)
                print(f"     Speech: {speech}, RMS: {rms:.4f}")
            time.sleep(0.2)
        
        audio_mgr.stop()
        print("\n✓ Audio manager test complete")
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_audio_manager()
    sys.exit(0 if success else 1)
