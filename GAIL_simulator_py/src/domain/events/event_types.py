# src/domain/events/event_types.py
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


class EventType(Enum):
    """Base enum for all event types."""
    # Generic events
    GENERIC = auto()
    

# src/domain/events/base_event.py
@dataclass
class DomainEvent:
    """Base class for all domain events."""
    type: EventType
    timestamp: datetime = None
    data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
            
        if self.data is None:
            self.data = {}
            
    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.__class__.__name__}(type={self.type.name}, timestamp={self.timestamp})"