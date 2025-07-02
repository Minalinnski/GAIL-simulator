# src/domain/player/models/v1/services/v1_model_service.py
import logging
import numpy as np
import torch
import torch.nn as nn
import pickle
import os
import json
from typing import Dict, Any, Optional, Tuple
from collections import deque
from stable_baselines3 import PPO
import gymnasium as gym
from gymnasium import spaces


class BasicDQN(nn.Module):
    """DQN网络定义"""
    def __init__(self, state_dim: int, hidden_dims: list = [512]):
        super(BasicDQN, self).__init__()
        
        layers = []
        prev_dim = state_dim
        
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.1)
            ])
            prev_dim = hidden_dim
        
        # 输出层：2个动作 [terminate=0, continue=1]
        layers.append(nn.Linear(prev_dim, 2))
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


class DummyBettingEnv(gym.Env):
    """虚拟环境用于PPO初始化"""
    def __init__(self, obs_dim=12, action_dim=16):
        super().__init__()
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(action_dim)
    
    def reset(self, seed=None, options=None):
        return np.zeros(self.observation_space.shape, dtype=np.float32), {}
    
    def step(self, action):
        return np.zeros(self.observation_space.shape, dtype=np.float32), 0.0, True, False, {}


class V1ModelService:
    """
    统一的V1模型服务，管理投注和终止决策模型
    """
    
    def __init__(self, cluster_id: int, base_model_dir: str = None):
        """
        初始化V1模型服务
        
        Args:
            cluster_id: 玩家聚类ID (0, 1, 2)
            base_model_dir: 模型基础目录，默认自动推断
        """
        self.cluster_id = cluster_id
        self.logger = logging.getLogger(f"domain.player.models.v1.cluster_{cluster_id}")
        
        # 推断模型目录
        if base_model_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_model_dir = os.path.join(os.path.dirname(current_dir), "weights")
        
        self.model_dir = os.path.join(base_model_dir, f"cluster_{cluster_id}")
        
        # 设备
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 投注模型组件
        self.ppo_model = None
        self.policy = None
        
        # 终止模型组件
        self.dqn_model = None
        self.isolation_forest = None
        self.tda_scaler = None
        self.normalization_scaler = None
        
        # 滑动窗口用于异常检测
        self.sliding_window = deque(maxlen=10)
        
        # 模型元数据
        self.metadata = {}
        
        # 投注额映射（基于您的bet_dictionary）
        self.bet_mapping = {
            0: 0.0,     # 终止
            1: 0.5,     # CNY最小值
            2: 1.0,
            3: 2.5,
            4: 5.0,
            5: 8.0,
            6: 15.0,
            7: 25.0,
            8: 50.0,
            9: 70.0,
            10: 100.0,
            11: 250.0,
            12: 500.0,
            13: 1000.0,
            14: 2000.0,
            15: 5000.0,
        }
        
        # 初始化模型
        self._initialize_models()
    
    def _initialize_models(self):
        """初始化所有模型"""
        if not os.path.exists(self.model_dir):
            raise FileNotFoundError(f"模型目录不存在: {self.model_dir}")
        
        # 加载元数据
        self._load_metadata()
        
        # 初始化投注模型
        self._initialize_betting_model()
        
        # 初始化终止模型
        self._initialize_termination_model()
        
        self.logger.info(f"Cluster {self.cluster_id} 模型初始化完成")
    
    def _load_metadata(self):
        """加载模型元数据"""
        metadata_file = None
        for file in os.listdir(self.model_dir):
            if file.endswith('_metadata.json'):
                metadata_file = os.path.join(self.model_dir, file)
                break
        
        if metadata_file and os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    self.metadata = json.load(f)
                self.logger.debug(f"加载元数据: {metadata_file}")
            except Exception as e:
                self.logger.warning(f"加载元数据失败: {e}")
                self.metadata = {}
        else:
            self.logger.warning("未找到元数据文件")
            self.metadata = {}
    
    def _initialize_betting_model(self):
        """初始化投注模型"""
        try:
            # 查找投注模型文件
            betting_model_path = os.path.join(self.model_dir, f"betting_cluster_{self.cluster_id}.pth")
            
            if not os.path.exists(betting_model_path):
                raise FileNotFoundError(f"投注模型文件不存在: {betting_model_path}")
            
            # 创建虚拟环境
            dummy_env = DummyBettingEnv()
            
            # 初始化PPO模型
            self.ppo_model = PPO("MlpPolicy", dummy_env, verbose=0, device=self.device)
            self.policy = self.ppo_model.policy
            
            # 尝试不同的加载方式
            try:
                self.ppo_model = PPO.load(betting_model_path, env=dummy_env, device=self.device)
                self.policy = self.ppo_model.policy
                self.policy.eval()
                self.logger.info(f"投注模型加载成功 (SB3格式): {betting_model_path}")
                
            except Exception as e1:
                self.logger.debug(f"SB3格式加载失败: {e1}")
            
        except Exception as e:
            self.logger.error(f"投注模型初始化失败: {e}")
            raise
    
    def _initialize_termination_model(self):
        """初始化终止模型"""
        try:
            # 查找终止模型文件
            dqn_pattern = f"termination_25_model_{self.cluster_id:02d}.pth"
            if_pattern = f"termination_25_model_{self.cluster_id:02d}_isolation_forest.pkl"
            
            dqn_path = os.path.join(self.model_dir, dqn_pattern)
            if_path = os.path.join(self.model_dir, if_pattern)
            
            # 加载DQN模型
            if os.path.exists(dqn_path):
                # 先加载checkpoint来推断网络结构
                checkpoint = torch.load(dqn_path, map_location=self.device)
                
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                else:
                    state_dict = checkpoint
                
                # 从state_dict推断网络结构
                state_dim, hidden_dims = self._infer_network_structure(state_dict)
                
                # 验证推断的输入维度
                if state_dim != 8:
                    self.logger.warning(f"推断的输入维度({state_dim})与期望的8不匹配，使用推断值")
                
                # 创建匹配的网络
                self.dqn_model = BasicDQN(state_dim=state_dim, hidden_dims=hidden_dims).to(self.device)
                self.dqn_model.load_state_dict(state_dict)
                self.dqn_model.eval()
                
                self.logger.info(f"DQN模型加载成功: {dqn_path}")
                self.logger.info(f"网络结构: 输入={state_dim}, 隐藏层={hidden_dims}")
            else:
                raise FileNotFoundError(f"DQN模型文件不存在: {dqn_path}")
            
            # 加载Isolation Forest模型（可选）
            if os.path.exists(if_path):
                with open(if_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                if isinstance(model_data, dict):
                    self.isolation_forest = model_data['isolation_forest']
                    self.tda_scaler = model_data.get('scaler') or model_data.get('tda_scaler')
                else:
                    self.isolation_forest = model_data
                
                self.logger.info(f"Isolation Forest加载成功: {if_path}")
            else:
                self.logger.warning(f"Isolation Forest文件不存在: {if_path}")
                
        except Exception as e:
            self.logger.error(f"终止模型初始化失败: {e}")
            raise
    
    def _infer_network_structure(self, state_dict: dict) -> tuple:
        """
        从state_dict推断网络的完整结构
        
        Args:
            state_dict: 模型的状态字典
            
        Returns:
            (state_dim, hidden_dims) 元组
        """
        hidden_dims = []
        state_dim = None
        layer_idx = 0
        
        # 推断输入维度（第一层的输入维度）
        if "network.0.weight" in state_dict:
            first_layer_weight = state_dict["network.0.weight"]
            state_dim = first_layer_weight.shape[1]  # 输入维度
            hidden_dims.append(first_layer_weight.shape[0])  # 第一个隐藏层维度
            layer_idx = 3  # 下一层的索引（跳过ReLU和Dropout）
        
        # 推断后续隐藏层维度
        while f"network.{layer_idx}.weight" in state_dict:
            weight_shape = state_dict[f"network.{layer_idx}.weight"].shape
            hidden_dims.append(weight_shape[0])  # 输出维度
            layer_idx += 3  # 跳过ReLU和Dropout层
        
        # 移除最后一层（输出层，应该是2维）
        if hidden_dims and len(hidden_dims) > 1:
            output_dim = hidden_dims.pop()  # 移除输出层
            self.logger.debug(f"检测到输出维度: {output_dim}")
        
        self.logger.debug(f"推断的网络结构: 输入维度={state_dim}, 隐藏层={hidden_dims}")
        return state_dim, hidden_dims

    def predict_bet_amount(self, observation: np.ndarray, deterministic: bool = True) -> float:
        """
        预测投注额
        
        Args:
            observation: 12维观察向量
            deterministic: 是否使用确定性策略
            
        Returns:
            预测的投注额
        """
        if self.ppo_model is None:
            raise RuntimeError("投注模型未初始化")
        
        # 确保输入格式正确
        if observation.shape != (12,):
            raise ValueError(f"观察向量维度错误: 期望12, 实际{observation.shape}")
        
        self.logger.debug(f"投注预测输入: {observation}")
        # 预测动作
        action, _ = self.ppo_model.predict(observation, deterministic=deterministic)
        
        # 映射为投注额
        bet_amount = self.bet_mapping.get(int(action), 1.0)
        
        self.logger.debug(f"投注预测: 动作={action}, 投注额={bet_amount}")
        return bet_amount
    
    def predict_termination(self, state_vector: np.ndarray, use_ensemble: bool = True) -> bool:
        """
        预测是否应该终止
        
        Args:
            state_vector: 8维状态向量
            use_ensemble: 是否使用集成方法
            
        Returns:
            True表示应该终止
        """
        if self.dqn_model is None:
            raise RuntimeError("终止模型未初始化")
        
        # 添加到滑动窗口
        self.sliding_window.append(state_vector.copy())
        
        self.logger.debug(f"终止模型预测数据: {state_vector}")
        # DQN预测
        dqn_action, dqn_confidence = self._predict_dqn(state_vector)
        
        # 如果有Isolation Forest且启用集成方法
        if use_ensemble and self.isolation_forest is not None and len(self.sliding_window) >= 5:
            final_action = self._ensemble_predict(dqn_action, dqn_confidence)
            self.logger.debug(f"终止模型预测结果: {final_action}")
            return final_action == 0
        else:
            self.logger.debug(f"终止模型预测结果: {dqn_action}")
            return dqn_action == 0
    
    def _predict_dqn(self, state_vector: np.ndarray) -> Tuple[int, float]:
        """DQN预测"""
        self.dqn_model.eval()
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state_vector).unsqueeze(0).to(self.device)
            q_values = self.dqn_model(state_tensor)
            
            # 获取动作和置信度
            probabilities = torch.softmax(q_values, dim=1)
            action = torch.argmax(q_values, dim=1).item()
            confidence = torch.max(probabilities, dim=1)[0].item()
            
            return action, confidence
    
    def _ensemble_predict(self, dqn_action: int, dqn_confidence: float) -> int:
        """集成预测（DQN + Isolation Forest）"""
        try:
            # 使用最近5个状态
            if len(self.sliding_window) < 5:
                return dqn_action
            
            window_obs = np.array(list(self.sliding_window)[-5:])
            
            # 计算TDA特征
            tda_features = self._compute_tda_features(window_obs)
            
            # 获取当前状态
            current_state = window_obs[-1]
            
            # 组合特征
            combined_features = np.concatenate([current_state, tda_features])
            
            # 使用TDA scaler缩放
            if self.tda_scaler is not None:
                combined_scaled = self.tda_scaler.transform(combined_features.reshape(1, -1))
            else:
                combined_scaled = combined_features.reshape(1, -1)
            
            # 获取异常分数
            isolation_score = self.isolation_forest.decision_function(combined_scaled)[0]
            
            # 集成决策逻辑
            if dqn_action == 0:  # DQN预测终止
                if dqn_confidence > 0.6 and isolation_score > -0.1:
                    return 0  # 保持终止
                else:
                    return 1  # 改为继续
            else:  # DQN预测继续
                return 1  # 保持继续
                
        except Exception as e:
            self.logger.warning(f"集成预测失败: {e}")
            return dqn_action
    
    def _compute_tda_features(self, window_obs: np.ndarray) -> np.ndarray:
        """计算TDA特征（简化版本）"""
        try:
            from sklearn.decomposition import PCA
            from gtda.homology import VietorisRipsPersistence
            from gtda.diagrams import PersistenceEntropy
            
            window_size, n_features = window_obs.shape
            
            # 如果特征太多，使用PCA降维
            if n_features > 4:
                pca = PCA(n_components=4)
                window_obs = pca.fit_transform(window_obs)
            
            # 重塑为点云格式
            point_cloud = window_obs.reshape(1, window_size, -1)
            
            # 计算Vietoris-Rips持久性
            VR = VietorisRipsPersistence(homology_dimensions=[0, 1], collapse_edges=True, n_jobs=1)
            barcodes = VR.fit_transform(point_cloud)
            
            # 计算持久性熵
            PE = PersistenceEntropy()
            entropy = PE.fit_transform(barcodes)[0]  # Shape: (2,) for H0 and H1
            
            return entropy
            
        except Exception as e:
            self.logger.warning(f"TDA特征计算失败: {e}")
            return np.zeros(2)
    
    def reset_session(self):
        """重置会话状态"""
        self.sliding_window.clear()
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'cluster_id': self.cluster_id,
            'device': str(self.device),
            'betting_model_loaded': self.ppo_model is not None,
            'termination_dqn_loaded': self.dqn_model is not None,
            'isolation_forest_loaded': self.isolation_forest is not None,
            'tda_scaler_loaded': self.tda_scaler is not None,
            'metadata': self.metadata
        }