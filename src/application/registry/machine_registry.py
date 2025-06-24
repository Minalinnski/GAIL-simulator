# src/application/registry/machine_registry.py
import logging
import os
from typing import Dict, List, Any, Optional

from src.domain.machine.entities.slot_machine import SlotMachine
from src.domain.machine.factories.machine_factory import MachineFactory


class MachineRegistry:
    """
    Registry for slot machine instances.
    Combines aspects of repository and factory to manage machine lifecycle.
    """
    def __init__(self, config_loader, machine_factory: Optional[MachineFactory] = None,
                rng_provider=None):
        """
        Initialize the machine registry.
        
        Args:
            config_loader: Configuration loader for machine configs
            machine_factory: Optional machine factory (created if not provided)
            rng_provider: Optional RNG provider for machine instances
        """
        self.logger = logging.getLogger("application.registry.machine")
        self.config_loader = config_loader
        
        # Create factory if not provided
        if machine_factory is None:
            self.machine_factory = MachineFactory(rng_provider)
        else:
            self.machine_factory = machine_factory
            
        # Machine storage
        self.machines = {}  # machine_id -> SlotMachine
        
    def load_machines(self, config_dir: str) -> List[str]:
        """
        Load all machine configurations from a directory.
        
        Args:
            config_dir: Directory containing machine configuration files
            
        Returns:
            List of loaded machine IDs
        """
        self.logger.info(f"Loading machines from {config_dir}")
        
        # Create machines using factory
        machines = self.machine_factory.create_multiple_machines(
            self.config_loader, config_dir
        )
        
        # Store in registry
        self.machines.update(machines)
        
        self.logger.info(f"Loaded {len(machines)} machines")
        return list(machines.keys())
        
    def load_machine(self, config_path: str, machine_id: Optional[str] = None) -> str:
        """
        Load a single machine from a configuration file.
        
        Args:
            config_path: Path to machine configuration file
            machine_id: Optional explicit machine ID
            
        Returns:
            ID of the loaded machine
        """
        self.logger.info(f"Loading machine from {config_path}")
        
        # Create machine using factory
        machine = self.machine_factory.create_machine_from_file(
            self.config_loader, config_path, machine_id
        )
        
        # Store in registry
        self.machines[machine.id] = machine
        
        self.logger.info(f"Loaded machine {machine.id}")
        return machine.id
        
    def get_machine(self, machine_id: str) -> Optional[SlotMachine]:
        """
        Get a machine by ID.
        
        Args:
            machine_id: Machine ID to retrieve
            
        Returns:
            SlotMachine instance or None if not found
        """
        if machine_id not in self.machines:
            self.logger.warning(f"Machine not found: {machine_id}")
            return None
            
        return self.machines[machine_id]
        
    def get_all_machines(self) -> List[SlotMachine]:
        """
        Get all registered machines.
        
        Returns:
            List of all SlotMachine instances
        """
        return list(self.machines.values())
        
    def get_machine_ids(self) -> List[str]:
        """
        Get all machine IDs.
        
        Returns:
            List of machine IDs
        """
        return list(self.machines.keys())
        
    def get_machine_count(self) -> int:
        """
        Get the number of registered machines.
        
        Returns:
            Count of machines
        """
        return len(self.machines)
        
    def add_machine(self, machine: SlotMachine) -> None:
        """
        Add a machine to the registry.
        
        Args:
            machine: SlotMachine instance to add
        """
        self.machines[machine.id] = machine
        self.logger.debug(f"Added machine {machine.id} to registry")
        
    def remove_machine(self, machine_id: str) -> bool:
        """
        Remove a machine from the registry.
        
        Args:
            machine_id: ID of machine to remove
            
        Returns:
            True if removed, False if not found
        """
        if machine_id in self.machines:
            del self.machines[machine_id]
            self.logger.debug(f"Removed machine {machine_id} from registry")
            return True
        return False
        
    def clear(self) -> None:
        """Clear all machines from the registry."""
        self.machines.clear()
        self.logger.debug("Cleared all machines from registry")