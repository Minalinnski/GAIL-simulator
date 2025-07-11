# src/domain/player/models/random/entities/random_decision_engine.py
import logging
from typing import Dict, List, Any, Tuple

from ....entities.decision_engine import BaseDecisionEngine
from ..services.random_player_model import RandomPlayerModel


class RandomDecisionEngine(BaseDecisionEngine):
    """
    随机决策引擎实现，使用随机模型生成决策。
    """
    def __init__(self, player, config: Dict[str, Any] = None):
        """
        初始化随机决策引擎。
        
        Args:
            player: 拥有此引擎的玩家实例
            config: 引擎配置
        """
        super().__init__(player, config)
        
        # 创建模型实例
        self.model = RandomPlayerModel(self.config)
        
        self.logger.debug(f"随机决策引擎初始化完成")
    
    def decide(self, machine_id: str, session_data: Dict[str, Any]) -> Tuple[float, float]:
        """
        使用随机模型决策下一步的投注额和延迟时间。
        
        Args:
            machine_id: 机器ID
            session_data: 会话数据
            
        Returns:
            (投注额, 延迟时间) 元组
        """
        # 1. 处理会话数据为模型输入
        model_input = self.model.process_session_data(session_data)
        
        # 2. 使用模型生成预测
        prediction = self.model.predict(model_input)
        
        # 3. 处理预测结果，应用约束
        constraints = {
            "available_bets": session_data.get("available_bets", [1.0]),
            "min_delay": self.config.get("min_delay", 0.0),
            "max_delay": self.config.get("max_delay", 5.0)
        }
        bet_amount, delay_time = self.model.process_prediction(prediction, constraints)
        
        self.logger.debug(f"决策结果: 投注={bet_amount}, 延迟={delay_time:.1f}秒")
        return bet_amount, delay_time
    
    def should_end_session(self, machine_id: str, session_data: Dict[str, Any]) -> bool:
        """
        决定是否结束当前会话。
        
        Args:
            machine_id: 机器ID
            session_data: 会话数据
            
        Returns:
            如果应该结束会话则为True
        """
        # 1. 余额不足（从session_data获取，而不是self.player.balance）
        current_balance = session_data.get("current_balance", 0.0)
        if current_balance <= 0:
            self.logger.debug("余额不足，结束会话")
            return True
        
        # 2. 会话时间过长
        start_time = session_data.get("start_time", 0)
        current_time = session_data.get("current_time", 0)
        max_duration = self.config.get("max_session_duration", 3600)  # 1小时
        if current_time - start_time > max_duration:
            self.logger.debug("会话时间过长，结束会话")
            return True
        
        # 3. 旋转次数过多
        total_spins = session_data.get("total_spins", 0)
        max_spins = self.config.get("max_spins_per_session", 500)
        if total_spins >= max_spins:
            self.logger.debug(f"旋转次数 ({total_spins}) 达到限制 ({max_spins})，结束会话")
            return True
        
        # 4. 随机结束（根据配置的概率）
        end_probability = self.config.get("end_probability", 0.01)
        if end_probability > 0 and self.model.rng.random() < end_probability:
            self.logger.debug(f"随机决定结束会话 (概率: {end_probability})")
            return True
        
        return False