# src/infrastructure/rng/strategies/numpy_rng.py
import numpy as np
from typing import List, Optional, Any


class NumpyRNG:
    """
    Random number generator using NumPy's implementation for better performance
    when generating large batches of random numbers.
    """
    def __init__(self, seed_value: Optional[int] = None):
        """
        Initialize the RNG with an optional seed.
        
        Args:
            seed_value: Optional seed value for reproducible random numbers
        """
        # Create a dedicated RandomState instance to avoid global state issues
        self.rng = np.random.RandomState(seed_value)
    
    def get_random_int(self, min_val: int, max_val: int) -> int:
        """
        Get a random integer in the range [min_val, max_val].
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            
        Returns:
            Random integer in the specified range
        """
        # NumPy's randint is [min, max) so we add 1 to max_val
        return self.rng.randint(min_val, max_val + 1)
    
    def get_random_float(self, min_val: float, max_val: float) -> float:
        """
        Get a random float in the range [min_val, max_val].
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            
        Returns:
            Random float in the specified range
        """
        return self.rng.uniform(min_val, max_val)
    
    def get_batch_ints(self, min_val: int, max_val: int, count: int) -> List[int]:
        """
        Get a batch of random integers - more efficient for large batches.
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            count: Number of random values to generate
            
        Returns:
            List of random integers
        """
        # NumPy's randint is [min, max) so we add 1 to max_val
        return self.rng.randint(min_val, max_val + 1, size=count).tolist()
    
    def seed(self, seed_value: int) -> None:
        """
        Set the seed for the RNG.
        
        Args:
            seed_value: Seed value to use
        """
        self.rng = np.random.RandomState(seed_value)
        
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
        
        # Select a random index and return the corresponding item
        idx = self.rng.randint(0, len(items))
        return items[idx]
    
    def shuffle(self, items: List[Any]) -> List[Any]:
        """
        Randomly shuffle a list of items.
        
        Args:
            items: List of items to shuffle
            
        Returns:
            Shuffled list (without modifying original)
        """
        # Create a copy to avoid modifying the original
        items_array = np.array(items, dtype=object)
        
        # Shuffle the numpy array
        self.rng.shuffle(items_array)
        
        # Convert back to list
        return items_array.tolist()

    def normal(self, mean, stddev):
        return self.rng.normal(mean, stddev)