"""Quick config helper to set profile and starter."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import INSTRUCTION_PROFILES


def show_profiles():
    """Display available profiles."""
    print("\n" + "=" * 70)
    print("📋 AVAILABLE CONVERSATION PROFILES")
    print("=" * 70 + "\n")
    
    for i, (key, profile) in enumerate(INSTRUCTION_PROFILES.items(), 1):
        print(f"{i}. {profile['name']}")
        print(f"   Key: {key}")
        print()


def show_config():
    """Display current configuration."""
    from config import CONVERSATION_START, ACTIVE_PROFILE
    
    print("\n" + "=" * 70)
    print("⚙️  CURRENT CONFIGURATION")
    print("=" * 70)
    print(f"\nCONVERSATION_START = \"{CONVERSATION_START}\"")
    print(f"ACTIVE_PROFILE = \"{ACTIVE_PROFILE}\"")
    print("\n")


if __name__ == "__main__":
    show_profiles()
    show_config()
    
    print("✏️  TO CHANGE SETTINGS:")
    print("   Edit interactive_chat/config.py and modify:")
    print("   - CONVERSATION_START (\"human\" or \"ai\")")
    print("   - ACTIVE_PROFILE (see keys above)")
    print("\n   Then run: uv run python .\interactive_chat\main.py")
    print("=" * 70)
