# tests/test_reel.py
import unittest
import sys
import os
from typing import List

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.domain.machine.entities.reel import Reel


class TestReel(unittest.TestCase):
    """Test cases for the Reel class."""

    def test_basic_construction(self):
        """Test basic reel construction."""
        symbols = [1, 2, 3, 4, 5]
        reel = Reel(symbols, "test_reel")
        
        self.assertEqual(reel.id, "test_reel")
        self.assertEqual(reel.symbols, symbols)
        self.assertEqual(reel.length, 5)
        self.assertEqual(len(reel), 5)
        
    def test_empty_reel(self):
        """Test construction with empty symbols list."""
        reel = Reel([], "empty_reel")
        
        self.assertEqual(reel.length, 0)
        self.assertEqual(len(reel), 0)
        
        # Getting symbols from empty reel should return empty list
        self.assertEqual(reel.get_symbols_at_position(0), [])
        
    def test_get_symbols_window(self):
        """Test getting symbols through window."""
        symbols = [10, 20, 30, 40, 50]
        reel = Reel(symbols, "window_reel")
        
        # Get default window size (3)
        result = reel.get_symbols_at_position(0)
        self.assertEqual(result, [10, 20, 30])
        
        # Get at different position
        result = reel.get_symbols_at_position(2)
        self.assertEqual(result, [30, 40, 50])
        
        # Get with wrap-around
        result = reel.get_symbols_at_position(3)
        self.assertEqual(result, [40, 50, 10])
        
        # Get with larger window size
        result = reel.get_symbols_at_position(0, window_size=5)
        self.assertEqual(result, [10, 20, 30, 40, 50])
        
        # Get with window size larger than reel
        result = reel.get_symbols_at_position(0, window_size=8)
        self.assertEqual(result, [10, 20, 30, 40, 50, 10, 20, 30])
        
    def test_wrap_around(self):
        """Test wrap-around behavior."""
        symbols = [1, 2, 3]
        reel = Reel(symbols, "wrap_reel")
        
        # Start at last position
        result = reel.get_symbols_at_position(2, window_size=5)
        self.assertEqual(result, [3, 1, 2, 3, 1])
        
        # Position larger than reel length
        result = reel.get_symbols_at_position(5, window_size=3)
        self.assertEqual(result, [3, 1, 2])  # 5 % 3 = 2
        
    def test_string_representation(self):
        """Test string representation."""
        reel = Reel([1, 2, 3], "repr_reel")
        self.assertEqual(repr(reel), "Reel(id=repr_reel, length=3)")


if __name__ == "__main__":
    unittest.main()