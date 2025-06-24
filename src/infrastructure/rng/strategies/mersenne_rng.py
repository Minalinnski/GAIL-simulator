# src/infrastructure/rng/strategies/mersenne_rng.py
import random
from typing import List, Optional, Any


class MersenneTwisterRNG:
    """
    Random number generator using the Mersenne Twister algorithm (Python's default).
    """
    def __init__(self, seed_value: Optional[int] = None):
        """
        Initialize the RNG with an optional seed.
        
        Args:
            seed_value: Optional seed value for reproducible random numbers
        """
        # Create a dedicated random instance to avoid global state issues
        self._random = random.Random()
        
        # Set seed if provided
        if seed_value is not None:
            self.seed(seed_value)
    
    def get_random_int(self, min_val: int, max_val: int) -> int:
        """
        Get a random integer in the range [min_val, max_val].
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            
        Returns:
            Random integer in the specified range
        """
        return self._random.randint(min_val, max_val)
    
    def get_random_float(self, min_val: float, max_val: float) -> float:
        """
        Get a random float in the range [min_val, max_val].
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            
        Returns:
            Random float in the specified range
        """
        return self._random.uniform(min_val, max_val)
    
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
        return [self._random.randint(min_val, max_val) for _ in range(count)]
    
    def seed(self, seed_value: int) -> None:
        """
        Set the seed for the RNG.
        
        Args:
            seed_value: Seed value to use
        """
        self._random.seed(seed_value)
        
    def choice(self, items: List[Any]) -> Any:
        """
        Randomly select an item from a list.
        
        Args:
            items: List of items to choose from
            
        Returns:
            Randomly selected item
            
        Raises:
            IndexError: If items list is empty
        """
        if not items:
            raise IndexError("Cannot choose from an empty list")
        return self._random.choice(items)
    
    def shuffle(self, items: List[Any]) -> List[Any]:
        """
        Randomly shuffle a list of items.
        
        Args:
            items: List of items to shuffle
            
        Returns:
            Shuffled list (modifies original list)
        """
        # Create a copy to avoid modifying the original
        items_copy = items.copy()
        self._random.shuffle(items_copy)
        return items_copy