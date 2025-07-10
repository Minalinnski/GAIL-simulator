# src/application/registry/player_registry.py
import logging
import os
from typing import Dict, List, Any, Optional

from src.domain.player.entities.player import Player
from src.domain.player.factories.player_factory import PlayerFactory


class PlayerRegistry:
    """
    Registry for player instances with support for stateless instance creation.
    """
    def __init__(self, config_loader, player_factory: Optional[PlayerFactory] = None,
                rng_provider=None):
        """
        Initialize the player registry.
        
        Args:
            config_loader: Configuration loader for player configs
            player_factory: Optional player factory (created if not provided)
            rng_provider: Optional RNG provider for player instances
        """
        self.logger = logging.getLogger("application.registry.player")
        self.config_loader = config_loader
        
        # Create factory if not provided
        if player_factory is None:
            self.player_factory = PlayerFactory(rng_provider)
        else:
            self.player_factory = player_factory
            
        # Player storage - 存储配置模板，不是实例
        self.player_configs = {}  # player_id -> config dict
        self.players = {}  # player_id -> Player (配置模板实例)
        
    def load_players(self, config_dir: str, initial_balance: Optional[float] = None) -> List[str]:
        """
        Load all player configurations from a directory.
        
        Args:
            config_dir: Directory containing player configuration files
            initial_balance: Deprecated parameter (ignored for stateless players)
            
        Returns:
            List of loaded player IDs
        """
        self.logger.info(f"Loading players from {config_dir}")
        
        if initial_balance is not None:
            self.logger.debug(f"initial_balance parameter ({initial_balance}) ignored - Players are now stateless")
        
        # Create players using factory
        players = self.player_factory.create_multiple_players(
            self.config_loader, config_dir, initial_balance=None
        )
        
        # Store in registry
        self.players.update(players)
        
        # 也存储配置以便创建新实例
        for player_id, player in players.items():
            self.player_configs[player_id] = player.config
        
        self.logger.info(f"Loaded {len(players)} players")
        return list(players.keys())
        
    def load_player(self, config_path: str, player_id: Optional[str] = None,
                  initial_balance: Optional[float] = None) -> str:
        """
        Load a single player from a configuration file.
        
        Args:
            config_path: Path to player configuration file
            player_id: Optional explicit player ID
            initial_balance: Deprecated parameter (ignored for stateless players)
            
        Returns:
            ID of the loaded player
        """
        self.logger.info(f"Loading player from {config_path}")
        
        if initial_balance is not None:
            self.logger.debug(f"initial_balance parameter ({initial_balance}) ignored - Players are now stateless")
        
        # Create player using factory
        player = self.player_factory.create_player_from_file(
            self.config_loader, config_path, player_id, initial_balance=None
        )
        
        # Store in registry
        self.players[player.id] = player
        self.player_configs[player.id] = player.config
        
        self.logger.info(f"Loaded player {player.id}")
        return player.id
    
    def create_instance(self, player_id: str) -> Optional[Player]:
        """
        创建一个新的无状态Player实例（用于实例池）
        
        Args:
            player_id: Player ID
            
        Returns:
            新的Player实例或None
        """
        if player_id not in self.player_configs:
            self.logger.error(f"Player config not found: {player_id}")
            return None
        
        try:
            # 从存储的配置创建新实例
            config = self.player_configs[player_id].copy()
            
            # 创建无状态Player实例（不传入initial_balance，让Player自己生成）
            instance = self.player_factory.create_player(
                player_id=player_id,
                config=config,
                initial_balance=None,  # 移除这个参数，因为新的Player构造函数不需要它
                rng_strategy_name="mersenne"
            )
            
            self.logger.debug(f"Created new instance for player {player_id}")
            return instance
            
        except Exception as e:
            self.logger.error(f"Failed to create instance for player {player_id}: {e}")
            return None
        
    def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get a player by ID (配置模板实例).
        
        Args:
            player_id: Player ID to retrieve
            
        Returns:
            Player instance or None if not found
        """
        if player_id not in self.players:
            self.logger.warning(f"Player not found: {player_id}")
            return None
            
        return self.players[player_id]
        
    def get_all_players(self) -> List[Player]:
        """
        Get all registered players.
        
        Returns:
            List of all Player instances
        """
        return list(self.players.values())
        
    def get_player_ids(self) -> List[str]:
        """
        Get all player IDs.
        
        Returns:
            List of player IDs
        """
        return list(self.players.keys())
        
    def get_player_count(self) -> int:
        """
        Get the number of registered players.
        
        Returns:
            Count of players
        """
        return len(self.players)
        
    def add_player(self, player: Player) -> None:
        """
        Add a player to the registry.
        
        Args:
            player: Player instance to add
        """
        self.players[player.id] = player
        self.player_configs[player.id] = player.config
        self.logger.debug(f"Added player {player.id} to registry")
        
    def remove_player(self, player_id: str) -> bool:
        """
        Remove a player from the registry.
        
        Args:
            player_id: ID of player to remove
            
        Returns:
            True if removed, False if not found
        """
        if player_id in self.players:
            del self.players[player_id]
            if player_id in self.player_configs:
                del self.player_configs[player_id]
            self.logger.debug(f"Removed player {player_id} from registry")
            return True
        return False
        
    def clear(self) -> None:
        """Clear all players from the registry."""
        self.players.clear()
        self.player_configs.clear()
        self.logger.debug("Cleared all players from registry")
        
    def reset_all_players(self, initial_balance: Optional[float] = None) -> None:
        """
        Reset all players to their initial state (无状态架构下不再需要).
        
        Args:
            initial_balance: Optional new balance for all players
        """
        # 无状态架构下，实例不需要重置
        self.logger.debug("Reset operation skipped - players are now stateless")