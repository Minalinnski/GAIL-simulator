# src/application/registry/player_registry.py
import logging
import os
from typing import Dict, List, Any, Optional

from src.domain.player.entities.player import Player
from src.domain.player.factories.player_factory import PlayerFactory


class PlayerRegistry:
    """
    Registry for player instances.
    Combines aspects of repository and factory to manage player lifecycle.
    """
    def __init__(self, config_loader, player_factory: Optional[PlayerFactory] = None):
        """
        Initialize the player registry.
        
        Args:
            config_loader: Configuration loader for player configs
            player_factory: Optional player factory (created if not provided)
        """
        self.logger = logging.getLogger("application.registry.player")
        self.config_loader = config_loader
        
        # Create factory if not provided
        if player_factory is None:
            self.player_factory = PlayerFactory()
        else:
            self.player_factory = player_factory
            
        # Player storage
        self.players = {}  # player_id -> Player
        
    def load_players(self, config_dir: str, initial_balance: Optional[float] = None) -> List[str]:
        """
        Load all player configurations from a directory.
        
        Args:
            config_dir: Directory containing player configuration files
            initial_balance: Optional starting balance for all players
            
        Returns:
            List of loaded player IDs
        """
        self.logger.info(f"Loading players from {config_dir}")
        
        # Create players using factory
        players = self.player_factory.create_multiple_players(
            self.config_loader, config_dir, initial_balance
        )
        
        # Store in registry
        self.players.update(players)
        
        self.logger.info(f"Loaded {len(players)} players")
        return list(players.keys())
        
    def load_player(self, config_path: str, player_id: Optional[str] = None,
                  initial_balance: Optional[float] = None) -> str:
        """
        Load a single player from a configuration file.
        
        Args:
            config_path: Path to player configuration file
            player_id: Optional explicit player ID
            initial_balance: Optional starting balance
            
        Returns:
            ID of the loaded player
        """
        self.logger.info(f"Loading player from {config_path}")
        
        # Create player using factory
        player = self.player_factory.create_player_from_file(
            self.config_loader, config_path, player_id, initial_balance
        )
        
        # Store in registry
        self.players[player.id] = player
        
        self.logger.info(f"Loaded player {player.id}")
        return player.id
        
    def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get a player by ID.
        
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
            self.logger.debug(f"Removed player {player_id} from registry")
            return True
        return False
        
    def clear(self) -> None:
        """Clear all players from the registry."""
        self.players.clear()
        self.logger.debug("Cleared all players from registry")
        
    def reset_all_players(self, initial_balance: Optional[float] = None) -> None:
        """
        Reset all players to their initial state.
        
        Args:
            initial_balance: Optional new balance for all players
        """
        for player in self.players.values():
            player.reset(initial_balance)
            
        self.logger.info(f"Reset {len(self.players)} players")