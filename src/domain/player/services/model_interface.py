# src/domain/player/services/model_interface.py
from typing import Dict, List, Any, Tuple, Protocol


class PlayerModel(Protocol):
    """
    玩家模型接口，定义所有模型必须实现的方法。
    """
    def process_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将会话数据处理为模型输入格式。
        每个模型可以自定义如何提取和转换特征。
        
        Args:
            session_data: 原始会话数据
            
        Returns:
            模型可用的处理后数据
        """
        raise NotImplementedError("This method must be implemented")
    
    def predict(self, model_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用模型生成预测结果。
        
        Args:
            model_input: 模型输入数据
            
        Returns:
            模型输出数据
        """
        raise NotImplementedError("This method must be implemented")
    
    def process_prediction(self, prediction: Dict[str, Any], 
                         constraints: Dict[str, Any]) -> Tuple[float, float]:
        """
        将模型预测结果处理为决策引擎所需格式。
        
        Args:
            prediction: 模型预测结果
            constraints: 约束条件，如可用投注额
            
        Returns:
            (投注额, 延迟时间) 元组
        """
        raise NotImplementedError("This method must be implemented")


class BasePlayerModel:
    """
    基础玩家模型实现，提供通用功能。
    """
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化模型。
        
        Args:
            config: 模型配置
        """
        self.config = config or {}
    
    def process_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        默认实现，只提取基本会话数据。
        子类应根据需要重写此方法。
        
        Args:
            session_data: 原始会话数据
            
        Returns:
            处理后的模型输入数据
        """
        # 基本抽取，子类可以扩展
        return {
            "available_bets": session_data.get("available_bets", [1.0]),
            "current_balance": session_data.get("current_balance", 0.0),
            "total_spins": session_data.get("total_spins", 0),
            "total_bet": session_data.get("total_bet", 0.0),
            "total_win": session_data.get("total_win", 0.0),
            "results": session_data.get("results", [])
        }
    
    def predict(self, model_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        基础预测实现，返回默认值。
        子类应重写此方法提供实际模型逻辑。
        
        Args:
            model_input: 模型输入数据
            
        Returns:
            预测结果
        """
        # 默认实现返回最小投注和中等延迟
        available_bets = model_input.get("available_bets", [1.0])
        min_bet = min(available_bets) if available_bets else 1.0
        
        return {
            "bet_amount": min_bet,
            "delay_time": 1.0,
            "end_session": False
        }
    
    def process_prediction(self, prediction: Dict[str, Any], 
                         constraints: Dict[str, Any]) -> Tuple[float, float]:
        """
        处理预测结果，应用约束条件。
        
        Args:
            prediction: 模型预测结果
            constraints: 约束条件
            
        Returns:
            (投注额, 延迟时间) 元组
        """
        # 提取预测值
        bet_amount = prediction.get("bet_amount", 1.0)
        delay_time = prediction.get("delay_time", 1.0)
        end_session = prediction.get("end_session", False)
        
        # 如果决定结束会话，返回0投注
        if end_session:
            return 0.0, 0.0
        
        # 应用约束：调整投注额到可用选项
        available_bets = constraints.get("available_bets", [1.0])
        if available_bets and bet_amount > 0 and bet_amount not in available_bets:
            bet_amount = min(available_bets, key=lambda x: abs(x - bet_amount))
        
        # 应用延迟约束
        min_delay = constraints.get("min_delay", 0.0)
        max_delay = constraints.get("max_delay", 10.0)
        delay_time = max(min_delay, min(max_delay, delay_time))
        
        return bet_amount, delay_time