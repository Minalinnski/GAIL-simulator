# src/domain/player/entities/player.py
import logging
import uuid
from typing import Dict, Any, Optional, Tuple
import random

class Player:
    """
    Represents a stateless player in the slot machine simulation.
    All state management is moved to GamingSession.
    """
    def __init__(self, player_id: str, config: Dict[str, Any], rng_strategy=None):
        """
        Initialize a stateless player.
        
        Args:
            player_id: Unique identifier for this player
            config: Player configuration dictionary
            rng_strategy: RNG strategy instance from infrastructure
        """
        self.id = player_id
        self.config = config
        self.logger = logging.getLogger(f"domain.player.{player_id}")
        self.rng = rng_strategy  # Infrastructure RNG strategy
        
        # 基本玩家属性（配置，不是状态）
        self.currency = config.get("currency", "CNY")
        self.instance_id = str(uuid.uuid4())
        
        # 从配置中获取模型版本
        self.model_version = config.get("model_version", "random")
        
        # 决策引擎实例，将在_initialize_decision_engine方法中创建
        self.decision_engine = None
        self._initialize_decision_engine()

        self.logger.info(f"Stateless Player {player_id} initialized, model version {self.model_version}")

    def generate_initial_balance(self) -> float:
        """
        根据配置生成初始余额（供Session使用）
        
        配置格式: initial_balance: {avg: 5000, std: 1000, min: 2000, max: 10000}
        
        Returns:
            生成的初始余额
        """
        balance_config = self.config.get("initial_balance", {})
        
        # 如果 initial_balance 是简单数值，直接返回
        if isinstance(balance_config, (int, float)):
            self.logger.debug(f"Player {self.id} - Using simple initial balance: {float(balance_config)}")
            return float(balance_config)
        
        # 如果不是字典，使用默认值
        if not isinstance(balance_config, dict):
            self.logger.warning(f"Player {self.id} - Invalid initial_balance format, using default 1000.0")
            return 1000.0
        
        # 获取平均值（必须字段）
        avg = balance_config.get("avg")
        if avg is None:
            self.logger.warning(f"Player {self.id} - initial_balance.avg not set, using default 1000.0")
            return 1000.0
        
        # 确保 avg 是数值类型
        try:
            avg = float(avg)
        except (ValueError, TypeError):
            self.logger.error(f"Player {self.id} - Invalid avg value: {avg}, using default 1000.0")
            return 1000.0
        
        # 获取其他参数并确保是数值类型
        try:
            std = float(balance_config.get("std", 0.0))
            min_balance = float(balance_config.get("min", avg * 0.1))
            max_balance = float(balance_config.get("max", avg * 10.0))
        except (ValueError, TypeError) as e:
            self.logger.error(f"Player {self.id} - Invalid balance config parameters: {e}, using avg only")
            return avg
        
        if std > 0 and self.rng:
            try:
                dynamic_balance = self.rng.normal(avg, std)
                dynamic_balance = max(min_balance, min(max_balance, dynamic_balance))
                dynamic_balance = round(dynamic_balance, 2)
                
                self.logger.debug(f"Player {self.id} - Dynamic balance generated: {dynamic_balance:.2f} "
                                f"(avg={avg}, std={std}, bounds=[{min_balance}, {max_balance}])")
                return dynamic_balance

            except Exception as e:
                self.logger.warning(f"Player {self.id} - Dynamic balance generation failed: {e}, using average value {avg:.2f}")
                return round(avg, 2)
        else:
            # std=0 或没有RNG，使用平均值
            self.logger.debug(f"Player {self.id} - Using static balance: {avg:.2f}")
            return round(avg, 2)

    def generate_first_bet(self, balance: float) -> float:
        """
        根据配置生成首次投注额（供Session使用）
        
        Args:
            balance: 当前余额（用于负担能力检查）
            
        Returns:
            生成的首次投注额
        """
        if not self.decision_engine:
            self.logger.warning(f"Player {self.id} - No decision engine available, using default first bet 1.0")
            return 1.0
            
        # 检查决策引擎是否有首次投注计算方法
        if hasattr(self.decision_engine, 'calculate_first_bet'):
            try:
                first_bet = self.decision_engine.calculate_first_bet(balance)
                self.logger.debug(f"Player {self.id} - Generated first bet: {first_bet}")
                return first_bet
            except Exception as e:
                self.logger.error(f"Player {self.id} - First bet calculation failed: {e}, using default 1.0")
                return 1.0
        else:
            # 使用默认逻辑
            default_bet = min(1.0, balance * 0.01)  # 默认为余额的1%，最小1.0
            self.logger.debug(f"Player {self.id} - Using default first bet logic: {default_bet}")
            return default_bet
            
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
        Make a play decision (无状态，通过session_data获取当前状态).
        
        Args:
            machine_id: ID of the machine being played
            session_data: Current session data (包含balance等状态信息)
            
        Returns:
            Tuple of (bet_amount, delay_before_next_spin)
        """
        if not self.decision_engine:
            self.logger.error("No strategy available, using default values")
            return 1.0, 1.0
            
        # Let strategy decide the bet and delay
        bet, delay = self.decision_engine.decide(machine_id, session_data)

        # # 检查投注额是否超过余额（从session_data获取）
        current_balance = session_data.get("current_balance", 0.0)
        if bet > current_balance:
            self.logger.warning(f"投注额 {bet} 超过余额 {current_balance}, 将强制结束session...")
            bet = -1
        
        self.logger.debug(f"Play decision: bet={bet}, delay={delay:.1f}s")
        return bet, delay
    
    def should_end_session(self, machine_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Determine if the player wants to end the current session (无状态).
        
        Args:
            machine_id: ID of the machine being played
            session_data: Current session information
            
        Returns:
            True if the player wants to end the session
        """
        current_balance = session_data.get("current_balance", 0.0)
        if current_balance <= 0:
            self.logger.debug("余额不足，结束会话")
            return True

        if not self.decision_engine:
            return False
            
        return self.decision_engine.should_end_session(machine_id, session_data)

    def get_info(self) -> Dict[str, Any]:
        """
        Get player information (配置信息，不包含状态).
        
        Returns:
            Dictionary containing player information
        """
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "currency": self.currency,
            "model_version": self.model_version
        }