# download_piper.py
from huggingface_hub import hf_hub_download
import os

print("Downloading Piper TTS voice from correct repo...")

# Create target directory
local_dir = "models/tts/piper-voices/en_US/lessac/medium"
os.makedirs(local_dir, exist_ok=True)

# Correct repo_id and full subfolder path
repo_id = "rhasspy/piper-voices"  # ← NOT rhasspy/piper-voices!
subfolder = "en/en_US/lessac/medium"

files = [
    "en_US-lessac-medium.onnx",
    "en_US-lessac-medium.onnx.json"
]

for fname in files:
    try:
        print(f"📥 Downloading {fname} from {subfolder}...")
        local_path = hf_hub_download(
            repo_id=repo_id,
            filename=fname,
            subfolder=subfolder,      # ← Critical: tells HF where to look
            repo_type="model",
            local_dir=local_dir
        )
        print(f"✅ Saved to: {local_path}")
    except Exception as e:
        print(f"❌ Failed for {fname}: {e}")

print("\n🎉 Done!")