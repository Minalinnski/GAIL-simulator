# src/application/registry/registry_service.py
import logging
import os
from typing import Dict, List, Any, Optional

from src.application.registry.machine_registry import MachineRegistry
from src.application.registry.player_registry import PlayerRegistry


class RegistryService:
    """
    Coordinates all entity registries in the application.
    Provides a single access point for entity management.
    """
    def __init__(self, config_loader, rng_provider=None):
        """
        Initialize the registry service.
        
        Args:
            config_loader: Configuration loader for entity configs
            rng_provider: Optional RNG provider for machine instances
        """
        self.logger = logging.getLogger("application.registry.service")
        self.config_loader = config_loader
        
        # Create registries
        self.machine_registry = MachineRegistry(config_loader, rng_provider=rng_provider)
        self.player_registry = PlayerRegistry(config_loader, rng_provider=rng_provider)
        
        self.logger.info("Registry service initialized")
        
    def load_all_machines(self, machines_dir: str, selection: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Load machine configurations from a directory with optional file selection.
        
        Args:
            machines_dir: Directory containing machine configurations
            selection: Optional selection criteria for files
                {
                    "mode": "all", "include", or "exclude",
                    "files": List of filenames to include or exclude
                }
            
        Returns:
            List of loaded machine IDs
        """
        if not selection:
            # Default behavior - load all
            return self.machine_registry.load_machines(machines_dir)
            
        # Get file selection parameters
        mode = selection.get("mode", "all")
        file_list = selection.get("files", [])
        
        if mode == "all" or not file_list:
            # Load all files
            return self.machine_registry.load_machines(machines_dir)
            
        # Generate a list of full file paths based on selection
        all_files = self._get_yaml_files(machines_dir)
        
        if mode == "include":
            # Only include specified files
            files_to_load = [
                os.path.join(machines_dir, f) for f in file_list 
                if f in all_files
            ]
            self.logger.info(f"Loading {len(files_to_load)} of {len(all_files)} machine files (include mode)")
        elif mode == "exclude":
            # Exclude specified files
            files_to_load = [
                os.path.join(machines_dir, f) for f in all_files 
                if f not in file_list
            ]
            self.logger.info(f"Loading {len(files_to_load)} of {len(all_files)} machine files (exclude mode)")
        else:
            self.logger.warning(f"Unknown file selection mode: {mode}, loading all files")
            files_to_load = [os.path.join(machines_dir, f) for f in all_files]
            
        # Load each file individually
        machine_ids = []
        for file_path in files_to_load:
            try:
                machine_id = self.machine_registry.load_machine(file_path)
                machine_ids.append(machine_id)
            except Exception as e:
                self.logger.error(f"Failed to load machine from {file_path}: {str(e)}")
                
        return machine_ids
        
    def load_all_players(self, players_dir: str, initial_balance: Optional[float] = None,
                        selection: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Load player configurations from a directory with optional file selection.
        
        Args:
            players_dir: Directory containing player configurations
            initial_balance: Optional starting balance for all players
            selection: Optional selection criteria for files
                {
                    "mode": "all", "include", or "exclude",
                    "files": List of filenames to include or exclude
                }
            
        Returns:
            List of loaded player IDs
        """
        if not selection:
            # Default behavior - load all
            return self.player_registry.load_players(players_dir, initial_balance)
            
        # Get file selection parameters
        mode = selection.get("mode", "all")
        file_list = selection.get("files", [])
        
        if mode == "all" or not file_list:
            # Load all files
            return self.player_registry.load_players(players_dir, initial_balance)
            
        # Generate a list of full file paths based on selection
        all_files = self._get_yaml_files(players_dir)
        
        if mode == "include":
            # Only include specified files
            files_to_load = [
                os.path.join(players_dir, f) for f in file_list 
                if f in all_files
            ]
            self.logger.info(f"Loading {len(files_to_load)} of {len(all_files)} player files (include mode)")
        elif mode == "exclude":
            # Exclude specified files
            files_to_load = [
                os.path.join(players_dir, f) for f in all_files 
                if f not in file_list
            ]
            self.logger.info(f"Loading {len(files_to_load)} of {len(all_files)} player files (exclude mode)")
        else:
            self.logger.warning(f"Unknown file selection mode: {mode}, loading all files")
            files_to_load = [os.path.join(players_dir, f) for f in all_files]
            
        # Load each file individually
        player_ids = []
        for file_path in files_to_load:
            try:
                player_id = self.player_registry.load_player(file_path, initial_balance=initial_balance)
                player_ids.append(player_id)
            except Exception as e:
                self.logger.error(f"Failed to load player from {file_path}: {str(e)}")
                
        return player_ids
        
    def _get_yaml_files(self, directory: str) -> List[str]:
        """
        Get list of YAML file names in a directory.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of file names with .yaml or .yml extension
        """
        if not os.path.exists(directory):
            return []
            
        return [f for f in os.listdir(directory) 
                if f.endswith('.yaml') or f.endswith('.yml')]
        
    def load_from_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load entities based on a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dictionary with loading results
        """
        self.logger.info("Loading entities from configuration")
        
        results = {
            "machines": [],
            "players": []
        }
        
        # Get file configurations
        file_configs = config.get("file_configs", {})
        
        # Load machines
        machine_config = file_configs.get("machines", {})
        if "dir" in machine_config:
            machines_dir = machine_config["dir"]
            self.logger.info(f"Loading machines from {machines_dir}")
            
            if os.path.exists(machines_dir):
                # Get machine file selection if present
                machine_selection = machine_config.get("selection")
                    
                machine_ids = self.load_all_machines(machines_dir, machine_selection)
                results["machines"] = machine_ids
            else:
                self.logger.error(f"Machines directory not found: {machines_dir}")
        
        # Load players
        player_config = file_configs.get("players", {})
        if "dir" in player_config:
            players_dir = player_config["dir"]
            self.logger.info(f"Loading players from {players_dir}")
            
            # Get initial balance if specified
            initial_balance = config.get("initial_balance", None)
            
            # Get player file selection if present
            player_selection = player_config.get("selection")
                
            if os.path.exists(players_dir):
                player_ids = self.load_all_players(players_dir, initial_balance, player_selection)
                results["players"] = player_ids
            else:
                self.logger.error(f"Players directory not found: {players_dir}")
                
        # Log summary
        self.logger.info(f"Loaded {len(results['machines'])} machines and {len(results['players'])} players")
        return results
        
    def get_machine(self, machine_id: str):
        """
        Get a machine by ID.
        
        Args:
            machine_id: Machine ID
            
        Returns:
            SlotMachine instance or None if not found
        """
        return self.machine_registry.get_machine(machine_id)
        
    def get_player(self, player_id: str):
        """
        Get a player by ID.
        
        Args:
            player_id: Player ID
            
        Returns:
            Player instance or None if not found
        """
        return self.player_registry.get_player(player_id)
        
    def reset_all(self):
        """Reset all entities to their initial state."""
        # Reset players
        self.player_registry.reset_all_players()
        
        # Nothing to reset for machines currently
        
        self.logger.info("All entities reset")
        
    def clear_all(self):
        """Clear all registries."""
        self.machine_registry.clear()
        self.player_registry.clear()
        self.logger.info("All registries cleared")