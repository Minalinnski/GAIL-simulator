# src/domain/player/models/v1/entities/v1_decision_engine.py
import logging
import numpy as np
from typing import Dict, Any, Tuple
import random

from ....entities.decision_engine import BaseDecisionEngine
from ..services.v1_model_service import V1ModelService
from ..services.data_processor_service import DataProcessorService


class V1DecisionEngine(BaseDecisionEngine):
    """
    V1决策引擎实现，使用预训练的投注和终止模型
    """
    
    def __init__(self, player, config: Dict[str, Any] = None):
        """
        初始化V1决策引擎
        
        Args:
            player: 拥有此引擎的玩家实例
            config: 引擎配置
        """
        super().__init__(player, config)
        
        # 从配置获取聚类ID
        self.cluster_id = config.get('cluster_id', 0)
        
        # 模型服务和数据处理器
        self.model_service = None
        self.data_processor = DataProcessorService()

        self.rng = random.Random()

        self._is_first_bet = True
        self._first_bet_amount = self._init_first_bet_amount()
        
        # 初始化模型服务
        self._initialize_model_service()
        
        self.logger.debug(f"V1决策引擎初始化完成 - Cluster {self.cluster_id}")

    def _init_first_bet_amount(self):
        try:
            first_bet_config = self.config.get("first_bet_mapping", {})

            if not first_bet_config:
                raise ValueError(f"V1决策引擎 - Cluster {self.cluster_id} - bet mapping not found!")
            
            items = list(first_bet_config.keys())
            weights = list(first_bet_config.values())
            first_bet = random.choices(items, weights=weights, k=1)[0]
            self.logger.info(f"首次投注预计算完成: {first_bet}")
            return first_bet
        except Exception as e:
            self.logger.warning(f"首次投注预计算失败: {e}, 使用默认值1.0")
            return 1.0

    def _initialize_model_service(self):
        """初始化模型服务"""
        try:
            # 获取模型目录（可选配置）
            base_model_dir = self.config.get('base_model_dir', None)
            
            # 创建模型服务
            self.model_service = V1ModelService(
                cluster_id=self.cluster_id,
                base_model_dir=base_model_dir
            )
            
            self.logger.info(f"模型服务初始化成功 - Cluster {self.cluster_id}")
            
        except Exception as e:
            self.logger.error(f"模型服务初始化失败: {e}")
            # 不设置fallback，让系统自然处理
            raise
    
    def decide(self, machine_id: str, session_data: Dict[str, Any]) -> Tuple[float, float]:
        """
        使用V1模型决策下一步的投注额和延迟时间
        
        Args:
            machine_id: 机器ID
            session_data: 会话数据
            
        Returns:
            (投注额, 延迟时间) 元组
        """
        try:
            # # 1. 首先检查是否应该终止
            # if self._should_terminate_session(machine_id, session_data):
            #     self.logger.debug("模型决定终止会话")
            #     return 0.0, 0.0
            if self._is_first_bet:
                self._is_first_bet = False
                bet_amount = self._first_bet_amount
            else:
            # 2. 如果继续，决定投注额
                bet_amount = self._decide_bet_amount(session_data)
            
            # 3. 决定延迟时间
            delay_time = self._decide_delay_time(session_data)
            
            self.logger.debug(f"V1决策结果: 投注={bet_amount}, 延迟={delay_time:.1f}秒")
            return bet_amount, delay_time
            
        except Exception as e:
            self.logger.error(f"V1决策失败: {e}")
            # 不使用fallback，重新抛出异常让系统处理
            raise
    
    def _should_terminate_session(self, machine_id: str, session_data: Dict[str, Any]) -> bool:
        """使用终止模型判断是否结束会话"""
        try:
            # 获取模型期望的输入维度
            expected_dim = 8  # 默认值
            if hasattr(self.model_service, 'dqn_model') and self.model_service.dqn_model:
                # 从模型获取实际的输入维度
                first_layer = self.model_service.dqn_model.network[0]
                if hasattr(first_layer, 'in_features'):
                    expected_dim = first_layer.in_features
            
            # 准备终止模型输入
            termination_state = self.data_processor.prepare_termination_input(
                session_data, expected_dim=expected_dim
            )
            
            # 使用模型预测
            should_terminate = self.model_service.predict_termination(
                termination_state, 
                use_ensemble=True
            )
            
            return should_terminate
            
        except Exception as e:
            self.logger.error(f"终止决策失败: {e}")
            # 不使用fallback，重新抛出异常
            raise
    
    def _decide_bet_amount(self, session_data: Dict[str, Any]) -> float:
        """使用投注模型决定投注额"""
        try:
            # 准备投注模型输入 (12维观察向量)
            betting_observation = self.data_processor.prepare_betting_input(session_data)
            
            # 使用模型预测
            bet_amount = self.model_service.predict_bet_amount(
                betting_observation, 
                deterministic=True
            )
            
            # # 应用约束条件
            # bet_amount = self._apply_bet_constraints(bet_amount, session_data)
            
            return bet_amount
            
        except Exception as e:
            self.logger.error(f"投注决策失败: {e}")
            # 不使用fallback，重新抛出异常
            raise
        
    def _decide_delay_time(self, session_data: Dict[str, Any]) -> float:
        """决定延迟时间"""
        min_delay = self.config.get('min_delay', 2.0)
        max_delay = self.config.get('max_delay', 3.0)
        
        recent_results = session_data.get('spins', [])
        if recent_results:
            last_result = recent_results[-1]
            profit = last_result.get('profit', 0)
            
            if profit > 0:
                # 赢了，随机偏向稍慢区间（2.5 - 3.0s）
                return random.uniform(2.5, max_delay)
            else:
                # 输了，随机偏向稍快区间（2.0 - 2.5s）
                return random.uniform(min_delay, 2.5)
        
        # 无最近结果时，随机2-3s之间
        return random.uniform(min_delay, max_delay)
    
    def _apply_bet_constraints(self, bet_amount: float, session_data: Dict[str, Any]) -> float:
        """应用投注约束条件"""
        model_bet_amount = bet_amount
        # 1. 不超过余额
        # current_balance = session_data.get('current_balance', self.player.balance)
        # bet_amount = min(bet_amount, current_balance)
        
        # 2. 符合可用投注额
        available_bets = session_data.get('available_bets', [1.0])
        if available_bets:
            bet_amount = min(available_bets, key=lambda x: abs(x - bet_amount))
        
        if model_bet_amount != bet_amount:
            self.logger.debug(f"Cluster {self.cluster_id}: 调整模型输出")
        return bet_amount
    
    def should_end_session(self, machine_id: str, session_data: Dict[str, Any]) -> bool:
        """
        决定是否结束当前会话
        
        系统已经会自动处理余额不足的情况，这里只处理玩家主动终止的逻辑
        
        Args:
            machine_id: 机器ID
            session_data: 会话数据
            
        Returns:
            如果应该结束会话则为True
        """
        if self._is_first_bet:
            return False
        return self._should_terminate_session(machine_id, session_data)