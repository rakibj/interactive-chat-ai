"""Interactive CLI to select conversation profile and start the chat."""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config import INSTRUCTION_PROFILES


def select_profile() -> str:
    """Prompt user to select a conversation profile."""
    print("\n" + "=" * 60)
    print("🎭 SELECT CONVERSATION PROFILE")
    print("=" * 60 + "\n")
    
    profiles = list(INSTRUCTION_PROFILES.keys())
    
    for i, key in enumerate(profiles, 1):
        profile = INSTRUCTION_PROFILES[key]
        print(f"{i}. {profile['name']}")
    
    while True:
        try:
            choice = input(f"\nSelect profile (1-{len(profiles)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(profiles):
                return profiles[idx]
            else:
                print(f"❌ Please enter a number between 1 and {len(profiles)}")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")


def select_starter() -> str:
    """Prompt user to choose who starts the conversation."""
    print("\n" + "=" * 60)
    print("👥 WHO STARTS THE CONVERSATION?")
    print("=" * 60 + "\n")
    
    print("1. You (human)")
    print("2. AI")
    
    while True:
        choice = input("\nSelect (1 or 2): ").strip()
        if choice == "1":
            return "human"
        elif choice == "2":
            return "ai"
        else:
            print("❌ Invalid input. Please enter 1 or 2.")


def update_config(profile: str, starter: str) -> None:
    """Update config.py with selected settings."""
    config_path = Path(__file__).parent / "config.py"
    content = config_path.read_text()
    
    # Update ACTIVE_PROFILE
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('ACTIVE_PROFILE = '):
            lines[i] = f'ACTIVE_PROFILE = "{profile}"'
        elif line.startswith('CONVERSATION_START = '):
            lines[i] = f'CONVERSATION_START = "{starter}"'
    
    config_path.write_text('\n'.join(lines))


def main():
    """Main entry point."""
    profile = select_profile()
    starter = select_starter()
    
    update_config(profile, starter)
    
    print(f"\n✅ Configuration updated!")
    print(f"   Profile: {profile}")
    print(f"   Starter: {starter}")
    print(f"\n🚀 Starting conversation...\n")
    
    # Import and run main
    from main import ConversationEngine
    
    engine = ConversationEngine()
    engine.run()


if __name__ == "__main__":
    main()
