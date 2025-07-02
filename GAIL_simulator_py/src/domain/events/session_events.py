# src/domain/events/session_events.py
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

from .event_types import EventType, DomainEvent


class SessionEventType(Enum):
    """Event types specific to gaming sessions."""
    SESSION_STARTED = auto()
    SESSION_ENDED = auto()
    SESSION_ENDED_BY_PLAYER = auto()        # 玩家主动结束
    SESSION_ENDED_BY_BALANCE = auto()       # 余额不足结束
    SESSION_ENDED_BY_LIMIT = auto()         # 达到系统限制
    SESSION_ENDED_BY_ERROR = auto()         # 发生错误结束
    SPIN_COMPLETED = auto()
    FREE_SPINS_TRIGGERED = auto()
    FREE_SPINS_ENDED = auto()
    BIG_WIN = auto()
    JACKPOT_WIN = auto()
    BALANCE_LOW = auto()
    BALANCE_DEPLETED = auto()


@dataclass
class SessionEvent(DomainEvent):
    """Event representing something that happened during a gaming session."""
    session_id: str = ""
    player_id: str = ""
    machine_id: str = ""
    
    def __post_init__(self):
        """Initialize base class and ensure data dictionary exists."""
        super().__post_init__()
        
        # Add IDs to data for consistency
        self.data["session_id"] = self.session_id
        self.data["player_id"] = self.player_id
        self.data["machine_id"] = self.machine_id