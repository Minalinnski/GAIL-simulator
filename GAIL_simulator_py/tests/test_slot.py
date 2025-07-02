# tests/test_slot_machine.py
import unittest
import sys
import os
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.domain.machine.entities.slot_machine import SlotMachine
from src.infrastructure.rng.strategies.mersenne_rng import MersenneTwisterRNG


class TestSlotMachine(unittest.TestCase):
    """Test cases for the SlotMachine class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a fixed-seed RNG for reproducible tests
        self.rng = MersenneTwisterRNG(seed_value=12345)
        
        # Basic config for tests
        self.basic_config = {
            "wild_symbol": [101],
            "scatter_symbol": 20,
            "free_spins": 10,
            "free_spins_multiplier": 2,
            "reels": {
                "normal": {
                    "reel1": [0, 1, 2, 3, 4, 5],
                    "reel2": [0, 1, 2, 3, 4, 5],
                    "reel3": [0, 1, 2, 3, 4, 5]
                }
            },
            "paylines": [
                {"indices": [0, 1, 2]}
            ],
            "pay_table": [
                {"symbol": "0", "payouts": [10, 20, 30]},
                {"symbol": "1", "payouts": [10, 20, 30]}
            ],
            "bet_table": [
                {"currency": "USD", "bet_options": [1.0, 2.0, 5.0]}
            ]
        }
        
    def test_basic_construction(self):
        """Test basic slot machine construction."""
        machine = SlotMachine("test_machine", self.basic_config, self.rng)
        
        self.assertEqual(machine.id, "test_machine")
        self.assertEqual(machine.wild_symbols, [101])
        self.assertEqual(machine.scatter_symbol, 20)
        self.assertEqual(machine.free_spins_count, 10)
        self.assertEqual(machine.free_spins_multiplier, 2)
        
        # Check reels
        self.assertIn("normal", machine.reels)
        self.assertEqual(len(machine.reels["normal"]), 3)  # 3 reels
        
        # Check paylines
        self.assertEqual(len(machine.paylines), 1)
        
        # Check pay table
        self.assertIn("0", machine.pay_table)
        self.assertIn("1", machine.pay_table)
        
        # Check bet table
        self.assertIn("USD", machine.bet_table)
        
    def test_minimal_config(self):
        """Test construction with minimal configuration."""
        minimal_config = {
            "reels": {
                "normal": {
                    "reel1": [0, 1, 2]
                }
            },
            "paylines": [
                {"indices": [0, 1, 2]}
            ],
            "pay_table": [
                {"symbol": "0", "payouts": [10, 20, 30]}
            ]
        }
        
        machine = SlotMachine("minimal", minimal_config, self.rng)
        
        # Check defaults
        self.assertEqual(machine.wild_symbols, [101])  # Default
        self.assertEqual(machine.scatter_symbol, 20)   # Default
        
        # Basic spin should still work
        result, _, _ = machine.spin()
        self.assertEqual(len(result), 3)  # 1 reel x 3 rows
        
    def test_missing_normal_reels(self):
        """Test handling of missing normal reels."""
        bad_config = {
            "reels": {
                "bonus": {  # Only bonus reels, no normal
                    "reel1": [0, 1, 2]
                }
            },
            "paylines": [{"indices": [0, 1, 2]}],
            "pay_table": [{"symbol": "0", "payouts": [10, 20, 30]}]
        }
        
        machine = SlotMachine("missing_normal", bad_config, self.rng)
        
        # Should create default normal reels
        self.assertIn("normal", machine.reels)
        
        # Spin should still work
        result, _, _ = machine.spin()
        self.assertGreater(len(result), 0)
        
    def test_spin_basic(self):
        """Test basic spin operation."""
        machine = SlotMachine("spin_test", self.basic_config, self.rng)
        
        result, trigger_free, free_left = machine.spin()
        
        # Check result format
        self.assertEqual(len(result), 9)  # 3x3 grid flattened
        
        # First spin shouldn't trigger free spins with this RNG seed
        self.assertFalse(trigger_free)
        self.assertEqual(free_left, 0)
        
    def test_spin_free_spins(self):
        """Test free spins mode."""
        # Force scatter symbols in reels for testing
        scatter_config = dict(self.basic_config)
        scatter_config["reels"] = {
            "normal": {
                "reel1": [20, 20, 20],  # All scatters
                "reel2": [20, 20, 20],
                "reel3": [20, 20, 20]
            }
        }
        
        machine = SlotMachine("free_spins_test", scatter_config, self.rng)
        
        # Spin should trigger free spins
        result, trigger_free, free_left = machine.spin()
        
        self.assertTrue(trigger_free)
        self.assertEqual(free_left, 10)  # Default free spins count
        
        # Next spin should be in free spins mode
        result, trigger_free, free_left = machine.spin(in_free=True, num_free_left=free_left)
        
        self.assertTrue(trigger_free)  # Still in free spins
        self.assertEqual(free_left, 9)  # Counter decreased
        
    def test_evaluate_win(self):
        """Test win evaluation."""
        machine = SlotMachine("win_test", self.basic_config, self.rng)
        
        # Create a grid with a winning line
        grid = [0, 0, 0]  # Top row all 0s
        
        # Evaluate win
        win_data = machine.evaluate_win(grid, bet=1.0)
        
        # Should have a line win
        self.assertGreater(win_data["total_win"], 0)
        self.assertEqual(len(win_data["line_wins"]), 1)
        
    def test_get_info(self):
        """Test getting machine info."""
        machine = SlotMachine("info_test", self.basic_config, self.rng)
        
        info = machine.get_info()
        
        self.assertEqual(info["id"], "info_test")
        self.assertIn("reel_sets", info)
        self.assertIn("reel_lengths", info)
        self.assertIn("num_paylines", info)
        self.assertIn("wild_symbols", info)
        self.assertIn("scatter_symbol", info)
        self.assertIn("free_spins_award", info)
        self.assertIn("free_spins_multiplier", info)
        self.assertIn("available_currencies", info)


if __name__ == "__main__":
    unittest.main()