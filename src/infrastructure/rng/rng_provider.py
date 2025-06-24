# src/infrastructure/rng/rng_provider.py
import logging
from typing import Optional, Dict, Any

# Import strategy implementations
from .strategies.mersenne_rng import MersenneTwisterRNG
from .strategies.numpy_rng import NumpyRNG


class RNGProvider:
    """
    Factory for creating and managing Random Number Generator strategies.
    """
    def __init__(self):
        """Initialize the RNG provider."""
        self.logger = logging.getLogger(__name__)
        self._strategies = {}  # Cache of created strategies
        
    def get_rng(self, strategy_name: str, seed: Optional[int] = None) -> 'RNGStrategy':
        """
        Get a RNG strategy instance by name.
        
        Args:
            strategy_name: Name of the RNG strategy ("mersenne", "numpy")
            seed: Optional seed value for the RNG
            
        Returns:
            An instance of the requested RNG strategy
            
        Raises:
            ValueError: If the strategy name is unknown
        """
        # Use cached instance if seed is None (for shared RNGs)
        cache_key = f"{strategy_name}_{seed}"
        if seed is None and cache_key in self._strategies:
            return self._strategies[cache_key]
        
        # Create a new strategy instance
        strategy = self._create_strategy(strategy_name, seed)
        
        # Cache if no specific seed (shared instance)
        if seed is None:
            self._strategies[cache_key] = strategy
            
        return strategy
        
    def _create_strategy(self, strategy_name: str, seed: Optional[int] = None) -> 'RNGStrategy':
        """
        Create a new RNG strategy instance.
        
        Args:
            strategy_name: Name of the RNG strategy
            seed: Optional seed value
            
        Returns:
            A new RNG strategy instance
        """
        strategy_name = strategy_name.lower()
        
        if strategy_name == "mersenne":
            self.logger.debug(f"Creating MersenneTwister RNG with seed: {seed}")
            return MersenneTwisterRNG(seed)
        elif strategy_name == "numpy":
            self.logger.debug(f"Creating NumPy RNG with seed: {seed}")
            return NumpyRNG(seed)
        else:
            self.logger.error(f"Unknown RNG strategy: {strategy_name}")
            raise ValueError(f"Unknown RNG strategy: {strategy_name}")
    
    def create_from_config(self, config: Dict[str, Any]) -> 'RNGStrategy':
        """
        Create an RNG strategy from a configuration dictionary.
        
        Args:
            config: Dictionary with 'strategy' and optional 'seed' keys
            
        Returns:
            An RNG strategy instance
            
        Example config:
            {"strategy": "numpy", "seed": 12345}
        """
        strategy_name = config.get('strategy', 'mersenne')
        seed = config.get('seed', None)
        
        return self.get_rng(strategy_name, seed)
    
    @staticmethod
    def get_available_strategies() -> Dict[str, str]:
        """
        Get a dictionary of available RNG strategies with descriptions.
        
        Returns:
            Dictionary mapping strategy names to descriptions
        """
        return {
            "mersenne": "Mersenne Twister (Python's default random generator)",
            "numpy": "NumPy-based random generator (better performance for large batches)"
        }