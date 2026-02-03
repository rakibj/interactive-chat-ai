"""Event buffer system for WebSocket session message history."""

from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Set
import json
from interactive_chat.api.models import WSEventMessage


class EventBuffer:
    """Ring buffer storing last N events per session for catch-up on reconnect."""
    
    def __init__(self, max_size: int = 100):
        """
        Initialize event buffer.
        
        Args:
            max_size: Maximum events to store (oldest are dropped when exceeded)
        """
        self.max_size = max_size
        self.events: deque = deque(maxlen=max_size)
        self.event_ids: Set[str] = set()  # For deduplication
        self.last_event_timestamp = 0.0
    
    def add_event(self, event: WSEventMessage) -> bool:
        """
        Add event to buffer.
        
        Args:
            event: WSEventMessage to store
            
        Returns:
            True if added, False if duplicate (by message_id)
        """
        # Check for duplicate
        if event.message_id in self.event_ids:
            return False
        
        # Add to buffer
        self.events.append(event)
        self.event_ids.add(event.message_id)
        self.last_event_timestamp = event.timestamp
        
        # When buffer reaches max_size, oldest events' IDs cleaned up automatically
        # by deque's maxlen behavior
        if len(self.events) == self.max_size:
            self._cleanup_old_ids()
        
        return True
    
    def get_events(self, since_timestamp: Optional[float] = None) -> List[WSEventMessage]:
        """
        Get events from buffer.
        
        Args:
            since_timestamp: Optional timestamp filter (events after this time)
            
        Returns:
            List of WSEventMessage objects
        """
        if since_timestamp is None:
            return list(self.events)
        
        return [e for e in self.events if e.timestamp >= since_timestamp]
    
    def get_events_by_message_id(self, last_received_id: Optional[str] = None) -> List[WSEventMessage]:
        """
        Get events after a specific message_id (for catch-up).
        
        Args:
            last_received_id: Get events after this message_id
            
        Returns:
            List of events after the specified message_id
        """
        if last_received_id is None:
            return list(self.events)
        
        # Find index of last_received_id
        events_list = list(self.events)
        for i, event in enumerate(events_list):
            if event.message_id == last_received_id:
                return events_list[i + 1:]
        
        # If not found, return all (client lost track)
        return events_list
    
    def clear(self) -> None:
        """Clear all events from buffer."""
        self.events.clear()
        self.event_ids.clear()
        self.last_event_timestamp = 0.0
    
    def size(self) -> int:
        """Get current number of events in buffer."""
        return len(self.events)
    
    def to_json(self) -> str:
        """
        Export buffer to JSON for logging/debugging.
        
        Returns:
            JSON string of all events
        """
        events_data = [
            {
                "message_id": e.message_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "payload": e.payload,
                "phase_id": e.phase_id,
                "turn_id": e.turn_id
            }
            for e in self.events
        ]
        return json.dumps(events_data, indent=2)
    
    def _cleanup_old_ids(self) -> None:
        """Remove message_ids of events no longer in buffer."""
        # Get current event ids in buffer
        current_ids = {e.message_id for e in self.events}
        # Remove ids no longer in buffer
        self.event_ids &= current_ids
