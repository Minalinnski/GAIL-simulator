# src/domain/player/services/decision_engine.py
from typing import Dict, List, Any, Tuple, Protocol


class DecisionEngine(Protocol):
    """
    决策引擎接口，定义所有决策引擎必须实现的方法。
    不同版本的模型将通过不同的实现来提供自定义逻辑。
    """
    def decide(self, machine_id: str, session_data: Dict[str, Any]) -> Tuple[float, float]:
        """
        决策下一步的投注额和延迟时间。
        
        Args:
            machine_id: 机器ID
            session_data: 会话数据
            
        Returns:
            (投注额, 延迟时间) 元组
        """
        raise NotImplementedError("This method must be implemented")
    
    def should_end_session(self, machine_id: str, session_data: Dict[str, Any]) -> bool:
        """
        决定是否结束当前会话。
        
        Args:
            machine_id: 机器ID
            session_data: 会话数据
            
        Returns:
            如果应该结束会话则为True
        """
        raise NotImplementedError("This method must be implemented")


class BaseDecisionEngine:
    """
    决策引擎的基础实现，提供通用功能。
    各版本的具体实现可以继承此类。
    """
    def __init__(self, player, config: Dict[str, Any] = None):
        """
        初始化决策引擎。
        
        Args:
            player: 拥有此引擎的玩家实例
            config: 引擎配置
        """
        self.player = player
        self.config = config or {}
        self.logger = player.logger
        
    def decide(self, machine_id: str, session_data: Dict[str, Any]) -> Tuple[float, float]:
        """基础决策实现，子类应重写此方法。"""
        # 默认实现始终返回最小投注和中等延迟
        available_bets = session_data.get('available_bets', [1.0])
        min_bet = min(available_bets) if available_bets else 1.0
        return min_bet, 2.0
    
    def should_end_session(self, machine_id: str, session_data: Dict[str, Any]) -> bool:
        """基础会话结束判断实现，子类应重写此方法。"""
        # 只检查余额条件，其他系统级检查由SessionRunner处理
        if self.player.balance <= 0:
            return True
            
        # 子类可实现自己的决策逻辑
        return False
            