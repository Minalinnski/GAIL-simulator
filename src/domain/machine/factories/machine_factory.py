# src/domain/machine/factories/machine_factory.py
import logging
from typing import Dict, Any, Optional

from ..entities.slot_machine import SlotMachine


class MachineFactory:
    """
    Factory for creating SlotMachine instances.
    """
    def __init__(self, rng_provider=None):
        """
        Initialize the machine factory.
        
        Args:
            rng_provider: Optional RNG provider for creating RNG strategies
        """
        self.logger = logging.getLogger("domain.machine.factory")
        self.rng_provider = rng_provider
        
    def create_machine(self, machine_id: str, config: Dict[str, Any], 
                      rng_strategy_name: str = "mersenne") -> SlotMachine:
        """
        Create a new slot machine instance.
        
        Args:
            machine_id: Unique identifier for the machine
            config: Machine configuration dictionary
            rng_strategy_name: Name of RNG strategy to use
            
        Returns:
            Initialized SlotMachine instance
        """
        self.logger.info(f"Creating slot machine: {machine_id}")
        
        # Get RNG strategy if provider available
        rng_strategy = None
        if self.rng_provider:
            # Get RNG seed from config if specified
            rng_seed = config.get("rng_seed", None)
            
            # Create RNG strategy
            rng_strategy = self.rng_provider.get_rng(rng_strategy_name, rng_seed)
            self.logger.debug(f"Using RNG strategy: {rng_strategy_name}, seed: {rng_seed}")
        else:
            self.logger.warning("No RNG provider available, machine will need RNG set later")
        
        # Create and return the machine
        return SlotMachine(machine_id, config, rng_strategy)
        
    def create_machine_from_file(self, config_loader, file_path: str, 
                               machine_id: Optional[str] = None) -> SlotMachine:
        """
        Create a machine from a configuration file.
        
        Args:
            config_loader: Configuration loader instance
            file_path: Path to configuration file
            machine_id: Optional explicit machine ID (overrides ID in config)
            
        Returns:
            Initialized SlotMachine instance
        """
        self.logger.info(f"Creating machine from file: {file_path}")
        
        # Load configuration
        config = config_loader.load_file(file_path)
        
        # Use provided machine_id or extract from config or filename
        if machine_id is None:
            # Try to get from config
            machine_id = config.get("machine_id", None)
            
            # If still None, use filename without extension
            if machine_id is None:
                import os
                machine_id = os.path.splitext(os.path.basename(file_path))[0]
                
        # Create machine
        return self.create_machine(machine_id, config)
        
    def create_multiple_machines(self, config_loader, config_dir: str) -> Dict[str, SlotMachine]:
        """
        Create multiple machines from a directory of configuration files.
        
        Args:
            config_loader: Configuration loader instance
            config_dir: Directory containing machine configurations
            
        Returns:
            Dictionary mapping machine IDs to SlotMachine instances
        """
        self.logger.info(f"Creating machines from directory: {config_dir}")
        
        # Load all configurations
        configs = config_loader.load_directory(config_dir)
        
        # Create machines
        machines = {}
        for config_id, config in configs.items():
            # Get machine_id from config or use config filename
            machine_id = config.get("machine_id", config_id)
            
            try:
                machine = self.create_machine(machine_id, config)
                machines[machine_id] = machine
            except Exception as e:
                self.logger.error(f"Failed to create machine {machine_id}: {str(e)}")
                
        self.logger.info(f"Created {len(machines)} machines")
        return machines