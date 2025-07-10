# src/application/registry/registry_service.py
import logging
import os
import threading
from queue import Queue, Empty
from typing import Dict, List, Any, Optional

from src.application.registry.machine_registry import MachineRegistry
from src.application.registry.player_registry import PlayerRegistry


class RegistryService:
    """
    Coordinates all entity registries with instance pool management.
    Provides stateless instance pools for concurrent sessions.
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
        self.rng_provider = rng_provider
        
        # Create registries
        self.machine_registry = MachineRegistry(config_loader, rng_provider=rng_provider)
        self.player_registry = PlayerRegistry(config_loader, rng_provider=rng_provider)
        
        # === 实例池管理 ===
        self._player_instance_pools = {}  # player_id -> Queue[Player instances]
        self._machine_instance_pools = {}  # machine_id -> Queue[Machine instances]
        self._pool_lock = threading.Lock()
        self._pool_stats = {
            "players": {"created": 0, "borrowed": 0, "returned": 0},
            "machines": {"created": 0, "borrowed": 0, "returned": 0}
        }
        
        self.logger.info("Registry service initialized")
        
    def initialize_instance_pools(self, max_concurrent_sessions: int):
        """
        初始化实例池，预创建无状态实例
        
        Args:
            max_concurrent_sessions: 最大并发会话数（实例池大小）
        """
        self.logger.info(f"Initializing instance pools for {max_concurrent_sessions} concurrent sessions")
        
        with self._pool_lock:
            # 为每个Player创建实例池
            for player_id in self.player_registry.get_player_ids():
                self._player_instance_pools[player_id] = Queue()
                
                # 预创建实例
                for _ in range(max_concurrent_sessions):
                    instance = self.player_registry.create_instance(player_id)
                    if instance:
                        self._player_instance_pools[player_id].put(instance)
                        self._pool_stats["players"]["created"] += 1
                
                self.logger.debug(f"Created {max_concurrent_sessions} instances for player {player_id}")
            
            # 为每个Machine创建实例池
            for machine_id in self.machine_registry.get_machine_ids():
                self._machine_instance_pools[machine_id] = Queue()
                
                # 预创建实例
                for _ in range(max_concurrent_sessions):
                    instance = self.machine_registry.create_instance(machine_id)
                    if instance:
                        self._machine_instance_pools[machine_id].put(instance)
                        self._pool_stats["machines"]["created"] += 1
                
                self.logger.debug(f"Created {max_concurrent_sessions} instances for machine {machine_id}")
                
        self.logger.info(f"Instance pools initialized - Players: {self._pool_stats['players']['created']}, Machines: {self._pool_stats['machines']['created']}")
    
    def get_player_instance(self, player_id: str, timeout: float = 5.0):
        """
        从实例池获取Player实例
        
        Args:
            player_id: Player ID
            timeout: 获取超时时间（秒）
            
        Returns:
            Player实例或None
        """
        if player_id not in self._player_instance_pools:
            self.logger.error(f"No instance pool for player {player_id}")
            return None
            
        try:
            instance = self._player_instance_pools[player_id].get(timeout=timeout)
            self._pool_stats["players"]["borrowed"] += 1
            self.logger.debug(f"Borrowed player instance {player_id}")
            return instance
        except Empty:
            self.logger.warning(f"No available instances for player {player_id} (timeout {timeout}s)")
            return None
    
    def return_player_instance(self, player_id: str, instance):
        """
        归还Player实例到实例池
        
        Args:
            player_id: Player ID
            instance: Player实例
        """
        if player_id not in self._player_instance_pools:
            self.logger.error(f"No instance pool for player {player_id}")
            return
            
        # 无状态实例不需要重置，直接归还
        self._player_instance_pools[player_id].put(instance)
        self._pool_stats["players"]["returned"] += 1
        self.logger.debug(f"Returned player instance {player_id}")
    
    def get_machine_instance(self, machine_id: str, timeout: float = 5.0):
        """
        从实例池获取Machine实例
        
        Args:
            machine_id: Machine ID
            timeout: 获取超时时间（秒）
            
        Returns:
            Machine实例或None
        """
        if machine_id not in self._machine_instance_pools:
            self.logger.error(f"No instance pool for machine {machine_id}")
            return None
            
        try:
            instance = self._machine_instance_pools[machine_id].get(timeout=timeout)
            self._pool_stats["machines"]["borrowed"] += 1
            self.logger.debug(f"Borrowed machine instance {machine_id}")
            return instance
        except Empty:
            self.logger.warning(f"No available instances for machine {machine_id} (timeout {timeout}s)")
            return None
    
    def return_machine_instance(self, machine_id: str, instance):
        """
        归还Machine实例到实例池
        
        Args:
            machine_id: Machine ID
            instance: Machine实例
        """
        if machine_id not in self._machine_instance_pools:
            self.logger.error(f"No instance pool for machine {machine_id}")
            return
            
        # 无状态实例不需要重置，直接归还
        self._machine_instance_pools[machine_id].put(instance)
        self._pool_stats["machines"]["returned"] += 1
        self.logger.debug(f"Returned machine instance {machine_id}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """
        获取实例池统计信息
        
        Returns:
            实例池统计字典
        """
        with self._pool_lock:
            stats = self._pool_stats.copy()
            
            # 添加当前可用实例数
            stats["players"]["available"] = sum(
                pool.qsize() for pool in self._player_instance_pools.values()
            )
            stats["machines"]["available"] = sum(
                pool.qsize() for pool in self._machine_instance_pools.values()
            )
            
            return stats
    
    def load_all_machines(self, machines_dir: str, selection: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Load machine configurations from a directory with optional file selection.
        
        Args:
            machines_dir: Directory containing machine configuration files
            selection: Optional selection criteria for machine files
            
        Returns:
            List of loaded machine IDs
        """
        self.logger.info(f"Loading machines from {machines_dir}")
        
        if not os.path.exists(machines_dir):
            self.logger.error(f"Machines directory not found: {machines_dir}")
            return []
        
        # Get all machine files
        machine_files = [f for f in os.listdir(machines_dir) 
                       if f.endswith('.yaml') or f.endswith('.yml')]
        
        # Apply selection if provided
        if selection:
            selected_files = []
            include_patterns = selection.get("include", [])
            exclude_patterns = selection.get("exclude", [])
            
            self.logger.debug(f"Original machine files: {machine_files}")
            self.logger.debug(f"Include patterns: {include_patterns}")
            self.logger.debug(f"Exclude patterns: {exclude_patterns}")
            
            for file in machine_files:
                file_selected = True
                
                # Check include patterns (if specified, file must match at least one)
                if include_patterns:
                    file_selected = any(pattern in file for pattern in include_patterns)
                    self.logger.debug(f"File '{file}' include check: {file_selected}")
                
                # Check exclude patterns (if any match, exclude the file)
                if file_selected and exclude_patterns:
                    file_excluded = any(pattern in file for pattern in exclude_patterns)
                    if file_excluded:
                        file_selected = False
                        self.logger.debug(f"File '{file}' excluded by pattern")
                
                if file_selected:
                    selected_files.append(file)
                    self.logger.debug(f"File '{file}' selected")
            
            machine_files = selected_files
            self.logger.info(f"After selection: {len(machine_files)} machine files selected")
        
        # Load selected machines
        machine_ids = []
        for file in machine_files:
            file_path = os.path.join(machines_dir, file)
            try:
                machine_id = self.machine_registry.load_machine(file_path)
                machine_ids.append(machine_id)
            except Exception as e:
                self.logger.error(f"Failed to load machine from {file_path}: {e}")
        
        self.logger.info(f"Loaded {len(machine_ids)} machines")
        return machine_ids
        
    def load_all_players(self, players_dir: str, initial_balance: Optional[float] = None, 
                        selection: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Load player configurations from a directory with optional file selection.
        
        Args:
            players_dir: Directory containing player configuration files
            initial_balance: Optional starting balance for all players
            selection: Optional selection criteria for player files
            
        Returns:
            List of loaded player IDs
        """
        self.logger.info(f"Loading players from {players_dir}")
        
        if not os.path.exists(players_dir):
            self.logger.error(f"Players directory not found: {players_dir}")
            return []
        
        # Get all player files
        player_files = [f for f in os.listdir(players_dir) 
                      if f.endswith('.yaml') or f.endswith('.yml')]
        
        # Apply selection if provided
        if selection:
            selected_files = []
            include_patterns = selection.get("include", [])
            exclude_patterns = selection.get("exclude", [])
            
            self.logger.debug(f"Original player files: {player_files}")
            self.logger.debug(f"Include patterns: {include_patterns}")
            self.logger.debug(f"Exclude patterns: {exclude_patterns}")
            
            for file in player_files:
                file_selected = True
                
                # Check include patterns (if specified, file must match at least one)
                if include_patterns:
                    file_selected = any(pattern in file for pattern in include_patterns)
                    self.logger.debug(f"File '{file}' include check: {file_selected}")
                
                # Check exclude patterns (if any match, exclude the file)
                if file_selected and exclude_patterns:
                    file_excluded = any(pattern in file for pattern in exclude_patterns)
                    if file_excluded:
                        file_selected = False
                        self.logger.debug(f"File '{file}' excluded by pattern")
                
                if file_selected:
                    selected_files.append(file)
                    self.logger.debug(f"File '{file}' selected")
            
            player_files = selected_files
            self.logger.info(f"After selection: {len(player_files)} player files selected from {len(player_files)} total")
        
        # Load selected players
        player_ids = []
        for file in player_files:
            file_path = os.path.join(players_dir, file)
            try:
                player_id = self.player_registry.load_player(file_path, initial_balance=initial_balance)
                player_ids.append(player_id)
            except Exception as e:
                self.logger.error(f"Failed to load player from {file_path}: {e}")
        
        self.logger.info(f"Loaded {len(player_ids)} players")
        return player_ids
        
    def _list_yaml_files(self, directory: str) -> List[str]:
        """
        List all YAML files in a directory.
        
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
        
        # 初始化实例池（如果配置中指定了max_concurrent_sessions）
        max_concurrent_sessions = config.get("max_concurrent_sessions", 0)
        if max_concurrent_sessions > 0:
            self.initialize_instance_pools(max_concurrent_sessions)
        
        return results
        
    def get_machine(self, machine_id: str):
        """
        Get a machine by ID (兼容接口，获取配置实例).
        
        Args:
            machine_id: Machine ID
            
        Returns:
            SlotMachine instance or None if not found
        """
        return self.machine_registry.get_machine(machine_id)
        
    def get_player(self, player_id: str):
        """
        Get a player by ID (兼容接口，获取配置实例).
        
        Args:
            player_id: Player ID
            
        Returns:
            Player instance or None if not found
        """
        return self.player_registry.get_player(player_id)
        
    def reset_all(self):
        """Reset all entities to their initial state (不再需要，因为实例是无状态的)."""
        self.logger.info("Reset operation skipped - instances are stateless")
        
    def clear_all(self):
        """Clear all registries and instance pools."""
        # 清空实例池
        with self._pool_lock:
            for pool in self._player_instance_pools.values():
                while not pool.empty():
                    try:
                        pool.get_nowait()
                    except Empty:
                        break
            
            for pool in self._machine_instance_pools.values():
                while not pool.empty():
                    try:
                        pool.get_nowait()
                    except Empty:
                        break
            
            self._player_instance_pools.clear()
            self._machine_instance_pools.clear()
            
            # 重置统计
            self._pool_stats = {
                "players": {"created": 0, "borrowed": 0, "returned": 0},
                "machines": {"created": 0, "borrowed": 0, "returned": 0}
            }
        
        # 清空注册表
        self.machine_registry.clear()
        self.player_registry.clear()
        self.logger.info("All registries and instance pools cleared")