# src/domain/player/factories/decision_engine_factory.py
import logging
import importlib
from typing import Dict, Any, Optional

from ..entities.decision_engine import BaseDecisionEngine


def create_decision_engine(player, version: str, config: Dict[str, Any] = None, rng_strategy=None) -> BaseDecisionEngine:
    """
    创建指定版本的决策引擎。
    
    Args:
        player: 拥有此引擎的玩家实例
        version: 引擎版本标识 (random, v1, etc.)
        config: 引擎配置
        rng_strategy: RNG strategy instance # TODO
        
    Returns:
        决策引擎实例
    """
    logger = logging.getLogger("domain.player.engine_factory")
    
    # 初始化配置
    if config is None:
        config = {}
    
    try:
        if version == "test":
            # 使用默认的引擎
            logger.info(f"Creating Base Decision Engine for player {player.id}")
            return BaseDecisionEngine(player, config)
        
        elif version == "random":
            # 使用随机引擎
            try:
                from ..models.random.entities.random_decision_engine import RandomDecisionEngine
                logger.info(f"Creating Random Decision Engine for player {player.id}")
                return RandomDecisionEngine(player, config)
            except ImportError as e:
                logger.warning(f"Cannot import random decision engine: {e}")
                logger.warning(f"Using Base model instead")
                return BaseDecisionEngine(player, config)
        
        elif version == "v1":
            # 使用V1模型引擎
            try:
                from ..models.v1.entities.v1_decision_engine import V1DecisionEngine
                logger.info(f"Creating V1 Decision Engine for player {player.id}")
                return V1DecisionEngine(player, config)
            except ImportError as e:
                logger.warning(f"Cannot import v1 decision engine: {e}")
                logger.warning(f"Using Base model instead")
                return BaseDecisionEngine(player, config)
        
        else:
            # 尝试动态导入其他版本的引擎
            module_path = f"src.domain.player.models.{version}.entities.{version}_decision_engine"
            class_name = f"{version.capitalize()}DecisionEngine"
            
            try:
                # 动态导入模块
                module = importlib.import_module(module_path)
                engine_class = getattr(module, class_name)
                
                logger.info(f"Created {version} model for player {player.id}")
                return engine_class(player, config)
            except (ImportError, AttributeError) as e:
                logger.warning(f"Cannot import {version} decision engine: {str(e)}")
                logger.warning(f"Using Base model instead")
                return BaseDecisionEngine(player, config)
                
    except Exception as e:
        logger.error(f"Error when creating decision engine {version}: {str(e)}")
        # 出现错误时，使用基础引擎作为备选
        logger.warning(f"Falling back to Base Decision Engine")
        return BaseDecisionEngine(player, config)