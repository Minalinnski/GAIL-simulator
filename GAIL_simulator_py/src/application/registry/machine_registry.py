# src/application/registry/machine_registry.py
import logging
import os
from typing import Dict, List, Any, Optional

from src.domain.machine.entities.slot_machine import SlotMachine
from src.domain.machine.factories.machine_factory import MachineFactory


class MachineRegistry:
    """
    Registry for slot machine instances with support for stateless instance creation.
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
            
        # Machine storage - 存储配置模板，不是实例
        self.machine_configs = {}  # machine_id -> config dict
        self.machines = {}  # machine_id -> SlotMachine (配置模板实例)
        
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
        
        # 也存储配置以便创建新实例
        for machine_id, machine in machines.items():
            self.machine_configs[machine_id] = machine.config
        
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
        self.machine_configs[machine.id] = machine.config
        
        self.logger.info(f"Loaded machine {machine.id}")
        return machine.id
    
    def create_instance(self, machine_id: str) -> Optional[SlotMachine]:
        """
        创建一个新的无状态Machine实例（用于实例池）
        
        Args:
            machine_id: Machine ID
            
        Returns:
            新的SlotMachine实例或None
        """
        if machine_id not in self.machine_configs:
            self.logger.error(f"Machine config not found: {machine_id}")
            return None
        
        try:
            # 从存储的配置创建新实例
            config = self.machine_configs[machine_id].copy()
            
            # 创建无状态Machine实例
            instance = self.machine_factory.create_machine(
                machine_id=machine_id,
                config=config
            )
            
            self.logger.debug(f"Created new instance for machine {machine_id}")
            return instance
            
        except Exception as e:
            self.logger.error(f"Failed to create instance for machine {machine_id}: {e}")
            return None
        
    def get_machine(self, machine_id: str) -> Optional[SlotMachine]:
        """
        Get a machine by ID (配置模板实例).
        
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
        self.machine_configs[machine.id] = machine.config
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
            if machine_id in self.machine_configs:
                del self.machine_configs[machine_id]
            self.logger.debug(f"Removed machine {machine_id} from registry")
            return True
        return False
        
    def clear(self) -> None:
        """Clear all machines from the registry."""
        self.machines.clear()
        self.machine_configs.clear()
        self.logger.debug("Cleared all machines from registry")