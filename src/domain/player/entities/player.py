# src/domain/player/entities/player.py
import logging
import uuid
from typing import Dict, Any, Optional, Tuple
import random

class Player:
    """
    Represents a player in the slot machine simulation.
    """
    def __init__(self, player_id: str, config: Dict[str, Any], initial_balance: float = 1000.0, rng_strategy=None):
        """
        Initialize a player.
        
        Args:
            player_id: Unique identifier for this player
            config: Player configuration dictionary
            rng_strategy: RNG strategy instance from infrastructure
        """
        self.id = player_id
        self.config = config
        self.logger = logging.getLogger(f"domain.player.{player_id}")
        self.rng = rng_strategy  # Infrastructure RNG strategy
        # 基本玩家属性
        self.currency = config.get("currency", "CNY")
        self.instance_id = str(uuid.uuid4())
        self.balance = self._initialize_balance(initial_balance)
        
        # 从配置中获取模型版本
        self.model_version = config.get("model_version", "random")
        
        # 决策引擎实例，将在_initialize_decision_engine方法中创建
        self.decision_engine = None
        self._initialize_decision_engine()



        self.logger.info(f"Player {player_id} initialized with balance {initial_balance}, Using model version {self.model_version}")
    


    def _initialize_balance(self, initial_balance=1000.0) -> float:
        """
        从配置初始化余额
        
        配置格式: initial_balance: {avg: 5000, std: 1000, min: 2000, max: 10000}
        
        Returns:
            实际初始余额
        """
        balance_config = self.config.get("initial_balance", {})
        
        # 获取平均值（必须字段）
        avg = balance_config.get("avg")
        if avg is None:
            # raise ValueError(f"Player {self.id}: initial_balance.avg is required")
            self.logger.warning(f"Player {self.id}: initial_balance.avg not set, fallback to default initial balance: {initial_balance}")
            return initial_balance
        
        # 获取其他参数
        std = balance_config.get("std", 0.0)
        min_balance = balance_config.get("min", avg * 0.1)
        max_balance = balance_config.get("max", avg * 10.0)
        
        if std > 0 and self.rng:
            try:
                dynamic_balance = self.rng.normal(avg, std)
                dynamic_balance = max(min_balance, min(max_balance, dynamic_balance))
                dynamic_balance = round(dynamic_balance, 2)
                
                self.logger.debug(f"Dynamic balance generated: {dynamic_balance:.2f} "
                                f"(avg={avg}, std={std}, bounds=[{min_balance}, {max_balance}])")
                return dynamic_balance

            except Exception as e:
                self.logger.warning(f"Dynamic balance generation failed: {e}, using average value {avg:.2f}")
                return round(avg, 2)
        else:
            # std=0 或没有RNG，使用平均值
            self.logger.debug(f"Using static balance: {avg:.2f}")
            return round(avg, 2)
            
    def _initialize_decision_engine(self):
        """初始化决策引擎，根据模型版本创建对应的引擎实例。"""
        from ..factories.decision_engine_factory import create_decision_engine
        
        # 使用工厂方法创建决策引擎
        self.decision_engine = create_decision_engine(
            self, 
            self.model_version, 
            self.config.get(f"model_config_{self.model_version}", {}),
            rng_strategy=self.rng
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
            self.logger.warning(f"投注额 {bet} 超过余额 {self.balance}, 将强制结束session...")
            bet = -1
        
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
        if self.balance <= 0:
            self.logger.debug("余额不足，结束会话")
            return True

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
            self.balance = self._initialize_balance()

        self._initialize_decision_engine()

        # 如果需要重制uid
        # self.instance_id = str(uuid.uuid4())
            
        self.logger.debug(f"Player reset with balance: {self.balance}")

    def get_info(self) -> Dict[str, Any]:
        """
        Get player information.
        
        Returns:
            Dictionary containing player information
        """
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "balance": self.balance,
            "currency": self.currency,
            "model_version": self.model_version
        }