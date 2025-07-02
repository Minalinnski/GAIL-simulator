# src/domain/session/factories/session_factory.py
import logging
import uuid
from typing import Dict, Any, Optional


from ..entities.gaming_session import GamingSession


class SessionFactory:
    """
    Factory for creating GamingSession instances.
    """
    def __init__(self, event_dispatcher=None):
        """
        Initialize the session factory.
        
        Args:
            event_dispatcher: Optional event dispatcher for session events
        """
        self.logger = logging.getLogger("domain.session.factory")
        self.event_dispatcher = event_dispatcher
        
    def create_session(self, player, machine, session_id: Optional[str] = None, output_manager=None) -> GamingSession:
        """
        Create a new gaming session.
        
        Args:
            player: Player entity instance
            machine: SlotMachine entity instance
            session_id: Optional session ID (generated if not provided)
            output_manager: 可选的输出管理器
            
        Returns:
            Initialized GamingSession instance
        """
        self.logger.info(f"Creating session {session_id} for player {player.id} on machine {machine.id}")
        
        return GamingSession(
            session_id=session_id,
            player=player,
            machine=machine,
            event_dispatcher=self.event_dispatcher,
            output_manager=output_manager
        )
    
    
    def create_session_from_config(self, player, machine, config: Dict[str, Any], output_manager=None) -> GamingSession:
        """
        从配置字典创建会话。
        
        Args:
            player: 玩家实体
            machine: 老虎机实体
            config: 会话配置
            output_manager: 可选的输出管理器
            
        Returns:
            新的GamingSession实例
        """
        # 从配置中提取会话ID
        session_id = config.get("session_id")
        
        # 如果未提供ID，生成一个唯一ID
        if not session_id:
            session_id = f"{player.id}_{machine.id}_{uuid.uuid4().hex[:8]}"
            
        # 创建基本会话
        session = self.create_session(player, machine, session_id, output_manager)
        
        # 如果配置中有其他参数，可以在这里设置
        # 例如，可以配置批处理大小、文件路径等
        
        return session
