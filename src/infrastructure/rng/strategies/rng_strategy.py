# src/infrastructure/rng/strategies/rng_strategy.py
from typing import List, Protocol, Optional, TypeVar, Any


class RNGStrategy(Protocol):
    """Protocol defining the interface for random number generators."""
    
    def get_random_int(self, min_val: int, max_val: int) -> int:
        """
        Get a random integer in the range [min_val, max_val].
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            
        Returns:
            Random integer in the specified range
        """
        pass
    
    def get_random_float(self, min_val: float, max_val: float) -> float:
        """
        Get a random float in the range [min_val, max_val].
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            
        Returns:
            Random float in the specified range
        """
        pass
    
    def get_batch_ints(self, min_val: int, max_val: int, count: int) -> List[int]:
        """
        Get a batch of random integers.
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            count: Number of random values to generate
            
        Returns:
            List of random integers
        """
        pass
    
    def seed(self, seed_value: int) -> None:
        """
        Set the seed for the RNG.
        
        Args:
            seed_value: Seed value to use
        """
        ...
    
    def choice(self, items: List[Any]) -> Any:
        """
        Randomly select an item from a list.
        
        Args:
            items: List of items to choose from
            
        Returns:
            Randomly selected item
        """
        pass
    
    def shuffle(self, items: List[Any]) -> List[Any]:
        """
        Randomly shuffle a list of items.
        
        Args:
            items: List of items to shuffle
            
        Returns:
            Shuffled list (may modify original list)
        """
        pass