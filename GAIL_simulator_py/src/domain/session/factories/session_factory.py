# src/domain/session/factories/session_factory.py
import logging
import uuid
from typing import Dict, Any, Optional, List

from ..entities.gaming_session import GamingSession
from src.infrastructure.output.session_output_manager import SessionOutputManager


class SessionFactory:
    """
    Factory for creating GamingSession instances with state management.
    """
    def __init__(self, event_dispatcher=None):
        """
        Initialize the session factory.
        
        Args:
            event_dispatcher: Optional event dispatcher for session events
        """
        self.logger = logging.getLogger("domain.session.factory")
        self.event_dispatcher = event_dispatcher
        
    def create_session(self, player, machine, session_id: Optional[str] = None, 
                      base_output_manager=None, output_config: Optional[Dict[str, Any]] = None) -> GamingSession:
        """
        Create a new gaming session with state management.
        
        Args:
            player: Stateless Player entity instance
            machine: SlotMachine entity instance  
            session_id: Optional session ID (generated if not provided)
            base_output_manager: 基础输出管理器
            output_config: Session级输出配置
            
        Returns:
            Initialized GamingSession instance with state management
        """
        # 生成唯一session ID
        if not session_id:
            session_id = f"{player.id}_{machine.id}_{uuid.uuid4().hex[:8]}"
        
        self.logger.info(f"Creating stateful session {session_id} for player {player.id} on machine {machine.id}")
        
        # 创建Session级输出管理器
        session_output_manager = None
        if base_output_manager:
            session_output_manager = SessionOutputManager(
                session_id=session_id,
                base_output_manager=base_output_manager,
                config=output_config
            )
        
        # 创建GamingSession（会自动生成initial_balance和first_bet）
        session = GamingSession(
            session_id=session_id,
            player=player,
            machine=machine,
            event_dispatcher=self.event_dispatcher,
            output_manager=session_output_manager
        )
        
        self.logger.debug(f"Created session {session_id} with initial balance: {session.get_initial_balance():.2f}, first bet: {session.get_first_bet():.2f}")
        
        return session
    
    def create_session_from_config(self, player, machine, config: Dict[str, Any], 
                                 base_output_manager=None) -> GamingSession:
        """
        从配置字典创建会话。
        
        Args:
            player: 无状态玩家实体
            machine: 老虎机实体
            config: 会话配置
            base_output_manager: 基础输出管理器
            
        Returns:
            新的GamingSession实例
        """
        # 从配置中提取会话ID
        session_id = config.get("session_id")
        
        # 如果未提供ID，生成一个唯一ID
        if not session_id:
            session_id = f"{player.id}_{machine.id}_{uuid.uuid4().hex[:8]}"
        
        # 提取输出配置
        output_config = config.get("output", {})
        
        # 创建带状态管理的会话
        session = self.create_session(
            player=player, 
            machine=machine, 
            session_id=session_id,
            base_output_manager=base_output_manager,
            output_config=output_config
        )
        
        # 如果配置中有其他参数，可以在这里设置
        # 例如，可以配置记录选项等
        if "record_spins" in config:
            if session.output_manager:
                session.output_manager.should_record_spins = config["record_spins"]
            session.should_record_spins = config["record_spins"]
        
        return session
    
    def create_multiple_sessions(self, player, machine, count: int, 
                               base_output_manager=None, output_config: Optional[Dict[str, Any]] = None) -> List[GamingSession]:
        """
        为同一player-machine对创建多个会话
        
        Args:
            player: 无状态Player实体
            machine: SlotMachine实体
            count: 要创建的会话数量
            base_output_manager: 基础输出管理器
            output_config: Session级输出配置
            
        Returns:
            GamingSession实例列表
        """
        sessions = []
        
        for i in range(count):
            session_id = f"{player.id}_{machine.id}_{i+1}_{uuid.uuid4().hex[:6]}"
            
            session = self.create_session(
                player=player,
                machine=machine,
                session_id=session_id,
                base_output_manager=base_output_manager,
                output_config=output_config
            )
            
            sessions.append(session)
        
        self.logger.info(f"Created {count} sessions for player {player.id} on machine {machine.id}")
        return sessions