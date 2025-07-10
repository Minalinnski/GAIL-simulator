# src/domain/player/factories/player_factory.py
import logging
import os
from typing import Dict, Any, Optional

from ..entities.player import Player


class PlayerFactory:
    """
    Factory for creating stateless Player instances.
    """
    def __init__(self, rng_provider=None):
        """Initialize the player factory."""
        self.logger = logging.getLogger("domain.player.factory")
        self.rng_provider = rng_provider
        
    def create_player(self, player_id: str, config: Dict[str, Any], 
                     initial_balance: Optional[float] = None,
                     rng_strategy_name: str = "mersenne") -> Player:
        """
        Create a new stateless player instance.
        
        Args:
            player_id: Unique identifier for the player
            config: Player configuration dictionary
            initial_balance: Deprecated parameter (ignored, kept for compatibility)
            rng_strategy_name: Name of RNG strategy to use
            
        Returns:
            Initialized stateless Player instance
        """
        self.logger.info(f"Creating stateless player: {player_id}")
        
        # Note: initial_balance is ignored as Player is now stateless
        if initial_balance is not None:
            self.logger.debug(f"initial_balance parameter ({initial_balance}) ignored - Player is now stateless")

        # Get RNG strategy if provider available
        rng_strategy = None
        if self.rng_provider:
            # Get RNG seed from config if specified
            rng_seed = config.get("rng_seed", None)
            
            # Create RNG strategy
            rng_strategy = self.rng_provider.get_rng(rng_strategy_name, rng_seed)
            self.logger.debug(f"Using RNG strategy: {rng_strategy_name}, seed: {rng_seed}")
        else:
            self.logger.warning("No RNG provider available, player will need RNG set later")
        
        # Create stateless player instance (only 3 parameters)
        return Player(player_id, config, rng_strategy)
        
    def create_player_from_file(self, config_loader, file_path: str, 
                              player_id: Optional[str] = None,
                              initial_balance: Optional[float] = None) -> Player:
        """
        Create a player from a configuration file.
        
        Args:
            config_loader: Configuration loader instance
            file_path: Path to configuration file
            player_id: Optional explicit player ID (overrides ID in config)
            initial_balance: Deprecated parameter (ignored)
            
        Returns:
            Initialized stateless Player instance
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
                
        # Create player (ignore initial_balance as it's deprecated)
        return self.create_player(player_id, config, initial_balance=None)
        
    def create_multiple_players(self, config_loader, config_dir: str,
                              initial_balance: Optional[float] = None) -> Dict[str, Player]:
        """
        Create multiple players from a directory of configuration files.
        
        Args:
            config_loader: Configuration loader instance
            config_dir: Directory containing player configurations
            initial_balance: Deprecated parameter (ignored)
            
        Returns:
            Dictionary mapping player IDs to Player instances
        """
        self.logger.info(f"Creating players from directory: {config_dir}")
        
        if initial_balance is not None:
            self.logger.debug(f"initial_balance parameter ({initial_balance}) ignored - Players are now stateless")
        
        # Load all configurations
        configs = config_loader.load_directory(config_dir)
        
        # Create players
        players = {}
        for config_id, config in configs.items():
            # Get player_id from config or use config filename
            player_id = config.get("player_id", config_id)
            
            try:
                # Create stateless player (no initial_balance)
                player = self.create_player(player_id, config, initial_balance=None)
                players[player_id] = player
            except Exception as e:
                self.logger.error(f"Failed to create player {player_id}: {str(e)}")
                
        self.logger.info(f"Created {len(players)} stateless players")
        return players