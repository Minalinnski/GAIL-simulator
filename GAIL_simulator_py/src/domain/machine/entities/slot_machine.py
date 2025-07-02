# src/domain/machine/entities/slot_machine.py
import logging
from typing import Dict, List, Any, Tuple, Optional

from .reel import Reel
from ..services.win_evaluation import WinEvaluator


class SlotMachine:
    """
    Represents a slot machine with its configuration, reels, and win evaluation logic.
    Core entity in the machine domain.
    """
    def __init__(self, machine_id: str, config: Dict[str, Any], rng_strategy=None):
        """
        Initialize the slot machine.
        
        Args:
            machine_id: Unique identifier for this machine
            config: Machine configuration dictionary
            rng_strategy: Random number generator strategy (optional)
        """
        self.id = machine_id
        self.logger = logging.getLogger(f"domain.machine.{machine_id}")
        self.logger.info(f"Initializing slot machine: {machine_id}")
        
        # Save original configuration
        self.config = config
        
        # Initialize with RNG strategy
        self.rng = rng_strategy
        
        # Extract basic parameters
        self.normal_symbols = config.get("symbols", {}).get("normal", list(range(11)))
        self.wild_symbols = config.get("symbols", {}).get("wild", [101])
        self.scatter_symbol = config.get("symbols", {}).get("scatter", 20)
        self.free_spins_count = config.get("free_spins", 10)
        self.free_spins_multiplier = config.get("free_spins_multiplier", 1)
        self.window_size = config.get("window_size", 3)
        
        # Load components
        self._load_reels(config.get("reels", {}))
        self._load_paylines(config.get("paylines", []))
        self._load_pay_table(config.get("pay_table", []))
        self._load_bet_table(config.get("bet_table", []))

        # Initialize Win Evaluator as instance
        self._evaluator = WinEvaluator(self)
        
        self.logger.info(f"Slot machine {machine_id} initialized successfully")
        
    def _load_reels(self, reels_config: Dict[str, Any]):
        """
        Load reel configurations.
        
        Args:
            reels_config: Dictionary of reel configurations
        """
        
        self.reels = {}
        
        # Process each reel set (normal mode, free spins mode, etc.)
        for reel_set_name, reel_set_data in reels_config.items():
            if not isinstance(reel_set_data, dict):
                self.logger.warning(f"Invalid reel set format {reel_set_name}: expected dict")
                continue
                
            # Skip comment entries
            if reel_set_name.startswith('_'):
                continue
                
            self.reels[reel_set_name] = {}
            
            # Process each reel in this set
            for reel_name, symbols in reel_set_data.items():
                if not isinstance(symbols, list):
                    self.logger.warning(f"Invalid reel format {reel_set_name}.{reel_name}: expected list")
                    continue
                
                self.reels[reel_set_name][reel_name] = Reel(symbols, f"{reel_set_name}_{reel_name}")
                self.logger.debug(f"Loaded reel {reel_set_name}.{reel_name} with {len(symbols)} symbols")
        
        # Verify at least one valid reel set
        if not self.reels or 'normal' not in self.reels:
            self.logger.warning("No valid reels found or missing 'normal' reel set")
            # Create minimal default reel set
            self.reels['normal'] = {
                f'reel{i}': Reel([0, 1, 2, 3, 4, 5], f'default_normal_reel{i}') 
                for i in range(1, 6) 
            }
            
    def _load_paylines(self, paylines_config: List[Dict[str, Any]]):
        """
        Load payline configurations.
        
        Args:
            paylines_config: List of payline configurations
        """
        self.paylines = []
        
        for i, entry in enumerate(paylines_config):
            if not isinstance(entry, dict) or 'indices' not in entry:
                self.logger.warning(f"Invalid payline entry at index {i}: missing 'indices'")
                continue
                
            indices = entry.get('indices', [])
            if not isinstance(indices, list) or len(indices) < 3:
                self.logger.warning(f"Invalid payline indices at index {i}: {indices}")
                continue
                
            self.paylines.append(indices)
        
        if not self.paylines:
            self.logger.warning("No valid paylines found, using defaults")
            # Create default paylines
            self.paylines = [
                [0, 1, 2, 3, 4],       # Top row
                [5, 6, 7, 8, 9],       # Middle row
                [10, 11, 12, 13, 14],  # Bottom row
            ]
            
    def _load_pay_table(self, pay_table_config: List[Dict[str, Any]]):
        """
        Load pay table configuration.
        
        Args:
            pay_table_config: List of pay table entries
        """
        self.pay_table = {}
        
        for entry in pay_table_config:
            if not isinstance(entry, dict) or 'symbol' not in entry or 'payouts' not in entry:
                self.logger.warning(f"Invalid pay table entry: {entry}")
                continue
                
            symbol = entry.get('symbol')
            payouts = entry.get('payouts', [])
            
            if not isinstance(payouts, list) or len(payouts) < 3:
                self.logger.warning(f"Invalid payouts for symbol {symbol}: {payouts}")
                continue
                
            self.pay_table[symbol] = payouts
            
        if not self.pay_table:
            self.logger.warning("No valid pay table entries, using defaults")
            # Create default pay table
            self.pay_table = {
                "0": [5, 20, 100],
                "1": [5, 20, 100],
                "2": [5, 20, 100],
                "3": [5, 20, 100],
                "4": [5, 20, 100],
                "5": [5, 20, 100],
                str(self.scatter_symbol): [5, 20, 100]
            }
            
    def _load_bet_table(self, bet_table_config: List[Dict[str, Any]]):
        """
        Load bet table configuration.
        
        Args:
            bet_table_config: List of bet table entries
        """
        self.bet_table = {}
        
        for entry in bet_table_config:
            if not isinstance(entry, dict) or 'currency' not in entry or 'bet_options' not in entry:
                self.logger.warning(f"Invalid bet table entry: {entry}")
                continue
                
            currency = entry.get('currency')
            bet_options = entry.get('bet_options', [])
            
            if not isinstance(bet_options, list) or not bet_options:
                self.logger.warning(f"Invalid bet options for currency {currency}: {bet_options}")
                continue
                
            self.bet_table[currency] = sorted(set(bet_options))  # Ensure options are unique and sorted
            
    def set_rng(self, rng_strategy):
        """
        Set or update the RNG strategy.
        
        Args:
            rng_strategy: RNG strategy instance
        """
        self.rng = rng_strategy
        self.logger.debug(f"Updated RNG strategy: {type(rng_strategy).__name__}")
        
    def spin(self, in_free: bool = False, num_free_left: int = 0) -> Tuple[List[int], bool, int]:
        """
        Execute a spin and return the result.
        
        Args:
            in_free: Whether in free spins mode
            num_free_left: Number of free spins remaining
            
        Returns:
            Tuple of (result_grid, trigger_free, num_free_left)
            - result_grid: Flattened array of symbols (row-major order)
            - trigger_free: Whether free spins were triggered
            - num_free_left: Number of free spins remaining
        """
        if self.rng is None:
            self.logger.error("No RNG strategy set, cannot spin")
            raise ValueError("No RNG strategy set for slot machine")
            
        # Determine which reel set to use
        reel_set_name = "bonus" if in_free else "normal"
        
        if reel_set_name not in self.reels:
            self.logger.warning(f"Reel set '{reel_set_name}' not found, using 'normal'")
            reel_set_name = "normal"
            
        current_reels = self.reels[reel_set_name]
        reel_names = sorted(current_reels.keys())
        num_reels = len(reel_names)
        
        # Initialize result grid
        result = [0] * (num_reels * self.window_size)  # 3 rows x num_reels
        
        # Spin each reel and get visible symbols
        for i, name in enumerate(reel_names):
            reel = current_reels[name]
            pos = self.rng.get_random_int(0, len(reel) - 1)
            symbols = reel.get_symbols_at_position(pos, self.window_size)
            
            # Store symbols in flattened grid
            for row in range(self.window_size):
                result[row * num_reels + i] = symbols[row]
        
        # Check for free spins trigger
        if not in_free:
            # Count columns with scatter symbol
            scatter_cols = sum(
                any(result[row * num_reels + col] == self.scatter_symbol for row in range(self.window_size))
                for col in range(num_reels)
            )
            trigger_free = scatter_cols >= 3
            num_free_left = self.free_spins_count if trigger_free else 0
        else:
            # In free spins mode, decrement counter
            num_free_left = max(0, num_free_left - 1)
            trigger_free = num_free_left > 0
            
        self.logger.debug(
            f"Spin result: {result}, trigger_free={trigger_free}, num_free_left={num_free_left}"
        )
            
        return result, trigger_free, num_free_left
        
    @property
    def evaluator(self):
        return self._evaluator

    def evaluate_win(self, grid: List[int], bet: float, in_free: bool = False, active_lines: int = None) -> Dict[str, Any]:
        return self._evaluator.evaluate_wins(grid, bet, in_free, active_lines)
    
        
    def reset_state(self):
        """
        重置机器状态以用于新会话。
        主要是重新初始化RNG以确保不同的随机序列。
        """
        # 重置RNG
        if hasattr(self, 'rng') and self.rng:
            if hasattr(self.rng, 'initialize'):
                self.rng.initialize()
            elif hasattr(self.rng, 'seed'):
                import random
                self.rng.seed(random.randint(0, 1000000))
        
        self.logger.debug(f"Machine {self.id} state reset")
        
        
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this machine.
        
        Returns:
            Dictionary with machine information
        """
        return {
            'id': self.id,
            'reel_sets': list(self.reels.keys()),
            'reel_lengths': {
                set_name: {reel_name: len(reel) for reel_name, reel in reel_set.items()}
                for set_name, reel_set in self.reels.items()
            },
            'num_paylines': len(self.paylines),
            'wild_symbols': self.wild_symbols,
            'scatter_symbol': self.scatter_symbol,
            'free_spins_award': self.free_spins_count,
            'free_spins_multiplier': self.free_spins_multiplier,
            'available_currencies': list(self.bet_table.keys())
        }