import os
PROJECT_ROOT = r"D:\Work\Projects\AI\interactive-chat-ai"
path = os.path.join(PROJECT_ROOT, "models", "tts", "piper-voices",
                    "en_US", "lessac", "medium", "en_US-lessac-medium.onnx")

print("Checking:", path)
print("Exists?", os.path.exists(path))
print("Size:", os.path.getsize(path) if os.path.exists(path) else "N/A")

json_path = path + ".json"
print("JSON exists?", os.path.exists(json_path))
print("JSON size:", os.path.getsize(json_path) if os.path.exists(json_path) else "N/A")