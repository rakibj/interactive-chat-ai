"""Conversation memory management using ephemeral deque buffer."""
from collections import deque
from typing import List, Dict
from config import MAX_MEMORY_TURNS


class ConversationMemory:
    """Ephemeral conversation history buffer with max turn limit."""
    
    def __init__(self, max_turns: int = MAX_MEMORY_TURNS):
        self.memory = deque(maxlen=max_turns)
    
    def add_message(self, role: str, content: str) -> None:
        """Add message to conversation history."""
        self.memory.append({"role": role, "content": content})
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get all messages in conversation history."""
        return list(self.memory)
    
    def clear(self) -> None:
        """Clear conversation history."""
        self.memory.clear()
    
    def __len__(self) -> int:
        return len(self.memory)
