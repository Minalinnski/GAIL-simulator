# src/domain/player/models/random/services/random_player_model.py
import random
from typing import Dict, List, Any, Tuple

from ....services.model_interface import BasePlayerModel


class RandomPlayerModel(BasePlayerModel):
    """
    随机玩家模型，生成随机决策。
    此模型主要用于测试或作为基线比较。
    """
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化随机模型。
        
        Args:
            config: 模型配置
        """
        super().__init__(config)
        
        # 读取配置参数
        self.min_bet_factor = self.config.get("min_bet_factor", 0.2)  # 最小投注比例
        self.max_bet_factor = self.config.get("max_bet_factor", 1.0)  # 最大投注比例
        self.min_delay = self.config.get("min_delay", 0.5)  # 最小延迟时间
        self.max_delay = self.config.get("max_delay", 3.0)  # 最大延迟时间
        self.end_probability = self.config.get("end_probability", 0.01)  # 结束概率
        
        # 创建随机数生成器
        self.rng = random.Random()
        
        # 如果配置了种子，设置随机种子
        if "seed" in self.config:
            self.rng.seed(self.config["seed"])
    
    def process_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理会话数据，随机模型只需要提取少量信息。
        
        Args:
            session_data: 原始会话数据
            
        Returns:
            处理后的模型输入数据
        """
        # 提取关键数据
        model_input = {
            "available_bets": session_data.get("available_bets", [1.0]),
            "current_balance": session_data.get("current_balance", 0.0),
            "in_free_spins": session_data.get("in_free_spins", False),
            "free_spins_remaining": session_data.get("free_spins_remaining", 0)
        }
        
        # 获取最近的结果（最多5个）
        results = session_data.get("results", [])
        recent_results = results[-5:] if results else []
        
        # 提取最近结果的关键信息
        recent_bets = []
        recent_wins = []
        for result in recent_results:
            recent_bets.append(result.get("bet", 0))
            recent_wins.append(result.get("win", 0))
        
        model_input["recent_bets"] = recent_bets
        model_input["recent_wins"] = recent_wins
        
        return model_input
    
    def predict(self, model_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成随机预测结果。
        
        Args:
            model_input: 模型输入数据
            
        Returns:
            预测结果字典
        """
        # 获取可用投注额
        available_bets = model_input.get("available_bets", [1.0])
        current_balance = model_input.get("current_balance", 0.0)
        
        # 随机决定是否结束会话
        end_session = self.rng.random() < self.end_probability
        
        # 如果余额不足，强制结束会话
        if current_balance <= 0:
            end_session = True
        
        # 随机选择投注额
        if available_bets and not end_session:
            # TODO 直接从可用投注中随机选择
            bet_amount = self.rng.choice(available_bets)
            bet_amount = 1.0
        else:
            bet_amount = 0.0
        
        # 随机选择延迟时间
        delay_time = self.rng.uniform(self.min_delay, self.max_delay)
        
        return {
            "bet_amount": bet_amount,
            "delay_time": delay_time,
            "end_session": end_session
        }
    
    def process_prediction(self, prediction: Dict[str, Any], 
                         constraints: Dict[str, Any]) -> Tuple[float, float]:
        """
        处理预测结果，应用约束条件。
        随机模型只需要简单的验证。
        
        Args:
            prediction: 模型预测结果
            constraints: 约束条件
            
        Returns:
            (投注额, 延迟时间) 元组
        """
        # 使用基类实现
        return super().process_prediction(prediction, constraints)