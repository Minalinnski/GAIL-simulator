# src/domain/player/factories/decision_engine_factory.py
import logging
import importlib
from typing import Dict, Any, Optional

from ..entities.decision_engine import BaseDecisionEngine


def create_decision_engine(player, version: str, config: Dict[str, Any] = None) -> BaseDecisionEngine:
    """
    创建指定版本的决策引擎。
    
    Args:
        player: 拥有此引擎的玩家实例
        version: 引擎版本标识
        config: 引擎配置
        
    Returns:
        决策引擎实例
    """
    logger = logging.getLogger("domain.player.engine_factory")
    
    # 初始化配置
    if config is None:
        config = {}
        
    # 尝试动态导入对应版本的决策引擎
    try:
        if version == "test":
            # 使用默认的引擎
            logger.info(f"Creating Base Decision Engine for player {player.id}.")
            return BaseDecisionEngine(player, config)
        else:
            # 尝试动态导入对应版本的引擎
            module_path = f"src.domain.player.models.{version}.entities.{version}_decision_engine"
            class_name = f"{version.capitalize()}DecisionEngine"
            
            try:
                # 动态导入模块
                module = importlib.import_module(module_path)
                engine_class = getattr(module, class_name)
                
                logger.info(f"Generated {version} model for player {player.id}.")
                return engine_class(player, config)
            except (ImportError, AttributeError) as e:
                logger.warning(f"Cannot import {version} decision engine: {str(e)}")
                logger.warning(f"Using Base model instead.")
                return BaseDecisionEngine(player, config)
    except Exception as e:
        logger.error(f"Error when creating decision engine {version}: {str(e)}")
        # 出现错误时，使用随机引擎作为备选
        return BaseDecisionEngine(player, config)