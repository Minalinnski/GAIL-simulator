# src/domain/player/models/v1/services/data_processor_service.py
import logging
import numpy as np
from typing import Dict, Any, List


class DataProcessorService:
    """
    数据预处理服务，将会话数据转换为模型输入格式
    基于您的SpinResult和GamingSession数据结构
    """
    
    def __init__(self):
        """初始化数据处理器"""
        self.logger = logging.getLogger(f"domain.player.models.v1.data_processor")
    
    def prepare_betting_input(self, session_data: Dict[str, Any]) -> np.ndarray:
        """
        准备投注模型输入数据 (12维)
        
        根据您的inference代码，投注模型需要12维输入：
        [balance, profit, streak, slot_type, base_point, 
         delta_t, delta_profit, delta_payout, prev_bet, 
         prev_basepoint, prev_profit, currency_flag]
        
        Args:
            session_data: 来自gaming_session.get_data_for_decision()的会话数据
            
        Returns:
            12维numpy数组
        """
        try:
            # 从session_data提取基本信息
            current_balance = session_data.get('current_balance', 1000.0)
            spins = session_data.get('spins', [])  # SpinResult列表
            machine_info = session_data.get('machine', {})
            
            # 计算profit相关数据
            current_profit = 0
            total_profit = 0
            prev_bet = 0
            prev_profit = 0
            prev_basepoint = current_balance
            streak = 0
            
            if spins:
                # 获取最后一次spin的结果
                last_spin = spins[-1]
                current_profit = last_spin.get('profit', 0)
                
                # 计算总利润（所有spin的profit总和）
                total_profit = sum(spin.get('profit', 0) for spin in spins)
                
                # 获取连胜/连败streak
                streak = last_spin.get('streak', 0)
                
                # 获取前一次的投注和利润
                if len(spins) >= 2:
                    prev_spin = spins[-2]
                    prev_bet = prev_spin.get('bet', 0)
                    prev_profit = prev_spin.get('profit', 0)
                    prev_basepoint = prev_spin.get('balance_after', current_balance)
                else:
                    prev_bet = 0
                    prev_profit = 0
                    prev_basepoint = current_balance
            
            # slot_type相关（从machine信息或者spin信息获取）
            slot_type = 1  # 默认normal spin
            if spins:
                last_spin = spins[-1]
                if last_spin.get('in_free_spins', False):
                    slot_type = 2  # free spin
            
            # base_point就是当前余额
            base_point = current_balance
            
            # delta时间相关（简化处理）
            delta_t = session_data.get('delta_t', 2.0)  # 默认值，您可以根据实际需要调整
            
            # delta_profit和delta_payout
            delta_profit = current_profit if spins else 0
            delta_payout = 0
            if spins:
                last_spin = spins[-1]
                delta_payout = last_spin.get('payout', 0) - last_spin.get('bet', 0)
            
            # currency_flag（根据您的bet_dictionary）
            currency = session_data.get('currency', 'CNY')
            currency_flag = self._get_currency_flag(currency)
            
            # 构建12维向量
            betting_input = np.array([
                current_balance,    # balance
                current_profit,     # profit  
                streak,            # streak
                slot_type,         # slot_type
                base_point,        # base_point
                delta_t,           # delta_t
                delta_profit,      # delta_profit
                delta_payout,      # delta_payout
                prev_bet,          # prev_bet
                prev_basepoint,    # prev_basepoint
                prev_profit,       # prev_profit
                currency_flag      # currency_flag
            ], dtype=np.float32)
            
            return betting_input
            
        except Exception as e:
            # 如果出错，返回默认值
            return np.array([
                1000.0, 0.0, 0.0, 1.0, 1000.0, 
                1.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 1.0
            ], dtype=np.float32)
    
    def prepare_termination_input(self, session_data: Dict[str, Any], expected_dim: int = 8) -> np.ndarray:
        """
        准备终止模型输入数据 (默认8维，但可以根据模型结构调整)
        
        根据您的inference代码，终止模型需要8维输入：
        [current_balance, total_profit, current_bet, streak,
        win_streak, prev_bet, prev_balance, prev_profit]
        
        Args:
            session_data: 来自gaming_session.get_data_for_decision()的会话数据
            expected_dim: 期望的输入维度，默认8
            
        Returns:
            expected_dim维numpy数组
        """
        try:
            # 从session_data提取基本信息
            self.logger.debug(f"Session Data: {session_data}")
            current_balance = session_data.get('current_balance', 1000.0)
            prev_balance = session_data.get('initial_balance', 1000.0)
            total_profit = session_data.get('total_profit', 0.0)

            results = session_data.get('results', [])
            
            # 计算各种指标
            current_bet = 1.0  # 默认投注额
            streak = 0
            win_streak = 0
            prev_bet = 0
            prev_profit = 0

            if results:
                curr_result = results[-1]
                current_bet = curr_result.get('bet', 1.0)
                streak = curr_result.get('streak', 0)
                win_streak = max(streak, 0)
            
            if len(results) >= 2:
                prev_result = results[-2]
                prev_bet = prev_result.get('bet', 1.0) 
                prev_profit = prev_result.get('profit', 0) 
                prev_balance = prev_result.get('balance_before', prev_balance)

            # 构建8维基础特征向量
            base_features = [
                current_balance,   # current_balance
                total_profit,      # total_profit
                current_bet,       # current_bet
                streak,            # streak
                win_streak,        # win_streak
                prev_bet,          # prev_bet
                prev_balance,      # prev_balance
                prev_profit        # prev_profit
            ]
            
            # 根据expected_dim处理
            if expected_dim > 8:
                raise ValueError(f"expected_dim ({expected_dim}) cannot be greater than 8. "
                            f"Only 8 features are supported.")
            
            # 截断到前expected_dim个特征（包括expected_dim=8的情况）
            termination_input = np.array(base_features[:expected_dim], dtype=np.float32)
            
            with np.printoptions(suppress=True, precision=2):
                self.logger.debug(f"Termination input prepared: {termination_input}")
            return termination_input
            
        except Exception as e:
            self.logger.error(f"Error preparing termination input: {e}")
            # 返回默认值
            default_values = [1000.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1000.0, 0.0]
            
            if expected_dim > 8:
                # 如果期望维度大于8，仍然报错，不返回默认值
                raise ValueError(f"expected_dim ({expected_dim}) cannot be greater than 8. "
                            f"Only 8 features are supported.")
            elif expected_dim < 8:
                default_values = default_values[:expected_dim]
            
            return np.array(default_values, dtype=np.float32)
    
    def _get_currency_flag(self, currency: str) -> float:
        """
        根据货币类型返回标志位
        基于您的bet_dictionary中的货币类型
        """
        currency_mapping = {
            'AUD': 0.0,
            'BRL': 1.0,
            'CNY': 2.0,
            'EUR': 3.0,
            'IDR': 4.0,
            'INR': 5.0,
            'JPY': 6.0,
            'KER': 7.0,
            'MMK': 8.0,
            'MYR': 9.0,
            'THB': 10.0,
            'USD': 11.0,
            'VND': 12.0
        }
        return currency_mapping.get(currency, 2.0)  # 默认CNY