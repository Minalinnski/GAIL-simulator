# src/domain/player/factories/player_factory.py
import logging
import os
from typing import Dict, Any, Optional

from ..entities.player import Player


class PlayerFactory:
    """
    Factory for creating Player instances.
    """
    def __init__(self):
        """Initialize the player factory."""
        self.logger = logging.getLogger("domain.player.factory")
        
    def create_player(self, player_id: str, config: Dict[str, Any], 
                     initial_balance: Optional[float] = None) -> Player:
        """
        Create a new player instance.
        
        Args:
            player_id: Unique identifier for the player
            config: Player configuration dictionary
            initial_balance: Optional starting balance (overrides config)
            
        Returns:
            Initialized Player instance
        """
        self.logger.info(f"Creating player: {player_id}")
        
        # Get initial balance from config or parameter
        if initial_balance is None:
            initial_balance = config.get("initial_balance", 1000.0)
        
        # Create player instance
        player = Player(player_id, config, initial_balance)
        
        return player
        
    def create_player_from_file(self, config_loader, file_path: str, 
                              player_id: Optional[str] = None,
                              initial_balance: Optional[float] = None) -> Player:
        """
        Create a player from a configuration file.
        
        Args:
            config_loader: Configuration loader instance
            file_path: Path to configuration file
            player_id: Optional explicit player ID (overrides ID in config)
            initial_balance: Optional starting balance (overrides config)
            
        Returns:
            Initialized Player instance
        """
        self.logger.info(f"Creating player from file: {file_path}")
        
        # Load configuration
        config = config_loader.load_file(file_path)
        
        # Use provided player_id or extract from config or filename
        if player_id is None:
            # Try to get from config
            player_id = config.get("player_id", None)
            
            # If still None, use filename without extension
            if player_id is None:
                player_id = os.path.splitext(os.path.basename(file_path))[0]
                
        # Create player
        return self.create_player(player_id, config, initial_balance)
        
    def create_multiple_players(self, config_loader, config_dir: str,
                              initial_balance: Optional[float] = None) -> Dict[str, Player]:
        """
        Create multiple players from a directory of configuration files.
        
        Args:
            config_loader: Configuration loader instance
            config_dir: Directory containing player configurations
            initial_balance: Optional starting balance for all players
            
        Returns:
            Dictionary mapping player IDs to Player instances
        """
        self.logger.info(f"Creating players from directory: {config_dir}")
        
        # Load all configurations
        configs = config_loader.load_directory(config_dir)
        
        # Create players
        players = {}
        for config_id, config in configs.items():
            # Get player_id from config or use config filename
            player_id = config.get("player_id", config_id)
            
            try:
                # Get player-specific balance if specified
                player_balance = initial_balance
                if player_balance is None:
                    player_balance = config.get("initial_balance", 1000.0)
                
                player = self.create_player(player_id, config, player_balance)
                players[player_id] = player
            except Exception as e:
                self.logger.error(f"Failed to create player {player_id}: {str(e)}")
                
        self.logger.info(f"Created {len(players)} players")
        return players