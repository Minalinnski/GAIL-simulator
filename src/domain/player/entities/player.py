# src/domain/player/entities/player.py
import logging
import uuid
from typing import Dict, Any, Optional, Tuple


class Player:
    """
    Represents a player in the slot machine simulation.
    Simplified player entity with basic attributes and play logic.
    """
    def __init__(self, player_id: str, config: Dict[str, Any], initial_balance: float = 1000.0):
        """
        Initialize a player.
        
        Args:
            player_id: Unique identifier for this player
            config: Player configuration dictionary
            initial_balance: Starting balance for this player
        """
        self.id = player_id
        self.config = config
        self.balance = initial_balance
        self.logger = logging.getLogger(f"domain.player.{player_id}")
        
        # 基本玩家属性
        self.currency = config.get("currency", "CNY")
        self.instance_id = str(uuid.uuid4())
        
        # 从配置中获取模型版本
        self.model_version = config.get("model_version", "random")
        
        # 决策引擎实例，将在_initialize_decision_engine方法中创建
        self.decision_engine = None

        self._initialize_decision_engine()

        self.logger.info(f"Player {player_id} initialized with balance {initial_balance}, Using model version {self.model_version}")
    

    def _initialize_decision_engine(self):
        """初始化决策引擎，根据模型版本创建对应的引擎实例。"""
        from ..factories.decision_engine_factory import create_decision_engine
        
        # 使用工厂方法创建决策引擎
        self.decision_engine = create_decision_engine(
            self, 
            self.model_version, 
            self.config.get(f"model_config_{self.model_version}", {})
        )
        
        self.logger.debug(f"Created Decision Engine: {type(self.decision_engine).__name__}")
        
    
    def play(self, machine_id: str, session_data: Dict[str, Any]) -> Tuple[float, float]:
        """
        Make a play decision.
        
        Args:
            machine_id: ID of the machine being played
            session_data: Current session data
            
        Returns:
            Tuple of (bet_amount, delay_before_next_spin)
        """
        if not self.decision_engine:
            self.logger.error("No strategy available, using default values")
            return 1.0, 1.0
            
        # Let strategy decide the bet and delay
        bet, delay = self.decision_engine.decide(machine_id, session_data)

        # TODO 确保投注额不超过余额
        if bet > self.balance:
            self.logger.debug(f"调整投注额从 {bet} 到余额 {self.balance}")
            bet = self.balance
        
        self.logger.debug(f"Play decision: bet={bet}, delay={delay:.1f}s")
        return bet, delay
    
    def should_end_session(self, machine_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Determine if the player wants to end the current session.
        
        Args:
            machine_id: ID of the machine being played
            session_data: Current session information
            
        Returns:
            True if the player wants to end the session
        """
        if not self.decision_engine:
            return False
            
        return self.decision_engine.should_end_session(machine_id, session_data)
    
    def update_balance(self, amount: float):
        """
        Update the player's balance.
        
        Args:
            amount: Amount to add to balance (negative for deductions)
        """
        self.balance += amount
        self.logger.debug(f"Balance updated: {self.balance} ({amount:+})")
    
    def reset(self, balance: Optional[float] = None):
        """
        Reset player state for a new simulation.
        
        Args:
            balance: Optional new balance (defaults to initial balance)
        """
        if balance is not None:
            self.balance = balance
        else:
            self.balance = self.config.get("initial_balance", 1000.0)

        self._initialize_decision_engine()

        # 如果需要重制uid
        # self.instance_id = str(uuid.uuid4())
            
        self.logger.debug(f"Player reset with balance: {self.balance}")