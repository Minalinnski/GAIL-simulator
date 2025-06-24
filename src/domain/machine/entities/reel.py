# src/domain/machine/entities/reel.py
from typing import List, Optional


class Reel:
    """
    Represents a single reel in a slot machine.
    Contains the symbols on the reel and their ordering.
    """
    def __init__(self, symbols: List[int], reel_id: str = ""):
        """
        Initialize a reel with symbols.
        
        Args:
            symbols: List of symbol IDs in order
            reel_id: Optional identifier for the reel
        """
        self.id = reel_id
        self.symbols = symbols
        self.length = len(symbols)
        
    def get_symbols_at_position(self, position: int, window_size: int = 3) -> List[int]:
        """
        Get the symbols visible in the window at the given position.
        Handles wrapping around the reel.
        
        Args:
            position: Starting position on the reel
            window_size: Number of symbols to return (default: 3)
            
        Returns:
            List of visible symbols
        """
        result = []
        if self.length == 0:
            return result
        
        for i in range(window_size):
            index = (position + i) % self.length
            result.append(self.symbols[index])
        return result
    
    def __len__(self) -> int:
        """Return the length of the reel."""
        return self.length
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Reel(id={self.id}, length={self.length})"