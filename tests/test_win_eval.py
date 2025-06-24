# tests/test_win_evaluator.py
import unittest
import sys
import os
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.domain.machine.services.win_evaluation import WinEvaluator


class TestWinEvaluator(unittest.TestCase):
    """Test cases for the WinEvaluator service."""

    def setUp(self):
        """Set up test fixtures."""
        # Simple pay table for testing
        self.pay_table = {
            "0": [10, 20, 30],  # 3, 4, 5 of a kind
            "1": [15, 25, 35],
            "2": [20, 30, 40],
            "20": [5, 10, 20]   # Scatter
        }
        
        # Simple paylines for testing (3x3 grid)
        self.paylines = [
            [0, 1, 2],  # Top row
            [3, 4, 5],  # Middle row
            [6, 7, 8],  # Bottom row
            [0, 4, 8],  # Diagonal top-left to bottom-right
            [2, 4, 6]   # Diagonal top-right to bottom-left
        ]
        
        # Wild symbols
        self.wild_symbols = [101, 102]
        
        # Scatter symbol
        self.scatter_symbol = 20
        
    def test_is_wild(self):
        """Test wild symbol identification."""
        # Wild symbols
        self.assertTrue(WinEvaluator.is_wild(101, self.wild_symbols))
        self.assertTrue(WinEvaluator.is_wild(102, self.wild_symbols))
        
        # Non-wild symbols
        self.assertFalse(WinEvaluator.is_wild(0, self.wild_symbols))
        self.assertFalse(WinEvaluator.is_wild(20, self.wild_symbols))
        
    def test_is_scatter(self):
        """Test scatter symbol identification."""
        # Scatter symbol
        self.assertTrue(WinEvaluator.is_scatter(20, self.scatter_symbol))
        
        # Non-scatter symbols
        self.assertFalse(WinEvaluator.is_scatter(0, self.scatter_symbol))
        self.assertFalse(WinEvaluator.is_scatter(101, self.scatter_symbol))
        
    def test_get_wild_multiplier(self):
        """Test wild multiplier calculation."""
        # Standard wild (101 = wild with 1x multiplier)
        self.assertEqual(WinEvaluator.get_wild_multiplier(101), 1)
        self.assertEqual(WinEvaluator.get_wild_multiplier(105), 5)
        
        # Wild with multiplier (202 = wild with 2x multiplier)
        self.assertEqual(WinEvaluator.get_wild_multiplier(202), 2)
        
        # Non-wild symbol
        self.assertEqual(WinEvaluator.get_wild_multiplier(5), 1)
        
    def test_evaluate_wins_empty_grid(self):
        """Test win evaluation with invalid empty grid."""
        with self.assertRaises(ValueError):
            WinEvaluator.evaluate_wins(
                grid=[],
                paylines=self.paylines,
                wild_symbols=self.wild_symbols,
                scatter_symbol=self.scatter_symbol,
                pay_table=self.pay_table,
                bet=1.0,
                active_lines=5
            )
            
    def test_evaluate_wins_no_win(self):
        """Test win evaluation with no winning combinations."""
        # 3x3 grid with no winning combinations
        grid = [
            0, 1, 2,
            2, 0, 1,
            1, 2, 1
        ]
        
        result = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        
        self.assertEqual(result["total_win"], 0)
        self.assertEqual(len(result["line_wins"]), 0)
        self.assertEqual(result["scatter_count"], 0)
        self.assertEqual(result["scatter_win"], 0)
        
    def test_evaluate_wins_line_win(self):
        """Test win evaluation with line wins."""
        # 3x3 grid with winning line (top row: 0, 0, 0)
        grid = [
            0, 0, 0,
            1, 2, 1,
            2, 1, 2
        ]
        
        result = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        
        # Should have one line win (first payline)
        self.assertEqual(result["total_win"], 10)  # 3 of symbol 0 = 10
        self.assertEqual(len(result["line_wins"]), 1)
        self.assertEqual(result["line_wins"][0]["line_index"], 0)
        self.assertEqual(result["line_wins"][0]["symbol"], 0)
        self.assertEqual(result["line_wins"][0]["match_count"], 3)
        self.assertEqual(result["line_wins"][0]["win_amount"], 10)
        
    def test_evaluate_wins_wild_substitution(self):
        """Test win evaluation with wild symbol substitution."""
        # 3x3 grid with wild substitution (top row: 0, wild, 0)
        grid = [
            0, 101, 0,
            1, 2, 1,
            2, 1, 2
        ]
        
        result = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        
        # Should have one line win (first payline)
        self.assertEqual(result["total_win"], 10)  # 3 of symbol 0 = 10
        self.assertEqual(len(result["line_wins"]), 1)
        self.assertEqual(result["line_wins"][0]["line_index"], 0)
        self.assertEqual(result["line_wins"][0]["symbol"], 0)
        self.assertEqual(result["line_wins"][0]["match_count"], 3)
        
    def test_evaluate_wins_wild_multiplier(self):
        """Test win evaluation with wild multiplier."""
        # 3x3 grid with wild multiplier (top row: 0, wild(2x), 0)
        grid = [
            0, 202, 0,
            1, 2, 1,
            2, 1, 2
        ]
        
        result = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=[202],  # Wild with 2x multiplier
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        
        # Should have one line win with 2x multiplier
        self.assertEqual(result["total_win"], 20)  # 3 of symbol 0 = 10 * 2x = 20
        self.assertEqual(len(result["line_wins"]), 1)
        self.assertEqual(result["line_wins"][0]["multiplier"], 2)
        
    def test_evaluate_wins_scatter(self):
        """Test win evaluation with scatter symbols."""
        # 3x3 grid with 3 scatter symbols
        grid = [
            0, 20, 1,
            20, 2, 1,
            2, 20, 0
        ]
        
        result = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        
        # Should have scatter win
        self.assertEqual(result["scatter_count"], 3)
        self.assertEqual(result["scatter_win"], 5)  # 3 scatters = 5
        self.assertEqual(result["total_win"], 5)
        
    def test_evaluate_wins_multiple_lines(self):
        """Test win evaluation with multiple winning lines."""
        # 3x3 grid with 2 winning lines (top row and middle row)
        grid = [
            0, 0, 0,
            1, 1, 1,
            2, 2, 0
        ]
        
        result = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        
        # Should have two line wins
        self.assertEqual(len(result["line_wins"]), 2)
        self.assertEqual(result["total_win"], 25)  # 10 (symbol 0) + 15 (symbol 1) = 25
        
        # Verify each line
        symbols = [win["symbol"] for win in result["line_wins"]]
        self.assertIn(0, symbols)  # Symbol 0 win
        self.assertIn(1, symbols)  # Symbol 1 win
        
    def test_evaluate_wins_bet_multiplier(self):
        """Test win evaluation with different bet amounts."""
        # 3x3 grid with winning line
        grid = [
            0, 0, 0,
            1, 2, 1,
            2, 1, 2
        ]
        
        # With bet = 1.0
        result1 = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        
        # With bet = 2.0
        result2 = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=2.0,
            active_lines=5
        )
        
        # Win should scale with bet
        self.assertEqual(result2["total_win"], result1["total_win"] * 2)
        
    def test_evaluate_wins_free_multiplier(self):
        """Test win evaluation with free spins multiplier."""
        # 3x3 grid with winning line
        grid = [
            0, 0, 0,
            1, 2, 1,
            2, 1, 2
        ]
        
        # Normal evaluation
        result1 = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        
        # With free spins multiplier
        result2 = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5,
            free_multiplier=2.0
        )
        
        # Win should be multiplied
        self.assertEqual(result2["total_win"], result1["total_win"] * 2)
        
    def test_evaluate_wins_active_lines(self):
        """Test win evaluation with limited active lines."""
        # 3x3 grid with 2 winning lines (top row and middle row)
        grid = [
            0, 0, 0,
            1, 1, 1,
            2, 2, 0
        ]
        
        # With all lines active
        result1 = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        
        # With only first line active
        result2 = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=1
        )
        
        # Should only have win from first line
        self.assertEqual(len(result2["line_wins"]), 1)
        self.assertEqual(result2["line_wins"][0]["line_index"], 0)
        self.assertEqual(result2["total_win"], 10)  # Just the symbol 0 win
        
    def test_evaluate_line(self):
        """Test evaluation of a single payline."""
        # Grid with first row all 0s
        grid = [
            0, 0, 0,
            1, 2, 1,
            2, 1, 2
        ]
        
        # First payline (top row)
        payline = [0, 1, 2]
        
        result = WinEvaluator._evaluate_line(
            grid=grid,
            payline=payline,
            wild_symbols=self.wild_symbols,
            pay_table=self.pay_table,
            bet=1.0,
            line_idx=0
        )
        
        # Check result
        self.assertEqual(result["line_index"], 0)
        self.assertEqual(result["win_amount"], 10)
        self.assertEqual(result["match_count"], 3)
        self.assertEqual(result["symbol"], 0)
        self.assertEqual(result["multiplier"], 1)
        
    def test_evaluate_line_no_win(self):
        """Test evaluation of a payline with no win."""
        # Grid with mixed symbols
        grid = [
            0, 1, 2,
            1, 2, 0,
            2, 0, 1
        ]
        
        # First payline (top row)
        payline = [0, 1, 2]
        
        result = WinEvaluator._evaluate_line(
            grid=grid,
            payline=payline,
            wild_symbols=self.wild_symbols,
            pay_table=self.pay_table,
            bet=1.0,
            line_idx=0
        )
        
        # No win
        self.assertEqual(result["win_amount"], 0)
        
    def test_evaluate_line_wild_first(self):
        """Test evaluation of a payline with wild in first position."""
        # Grid with wild in first position
        grid = [
            101, 0, 0,
            1, 2, 1,
            2, 1, 2
        ]
        
        # First payline (top row)
        payline = [0, 1, 2]
        
        result = WinEvaluator._evaluate_line(
            grid=grid,
            payline=payline,
            wild_symbols=self.wild_symbols,
            pay_table=self.pay_table,
            bet=1.0,
            line_idx=0
        )
        
        # Wild in first position doesn't count
        self.assertEqual(result["win_amount"], 0)
        
    def test_evaluate_line_invalid_payline(self):
        """Test evaluation with invalid payline."""
        # Empty payline
        result = WinEvaluator._evaluate_line(
            grid=[0, 0, 0],
            payline=[],
            wild_symbols=self.wild_symbols,
            pay_table=self.pay_table,
            bet=1.0,
            line_idx=0
        )
        
        # No win
        self.assertEqual(result["win_amount"], 0)
        
        # Payline with index out of range
        result = WinEvaluator._evaluate_line(
            grid=[0, 0, 0],
            payline=[10, 11, 12],  # Out of range
            wild_symbols=self.wild_symbols,
            pay_table=self.pay_table,
            bet=1.0,
            line_idx=0
        )
        
        # No win
        self.assertEqual(result["win_amount"], 0)


if __name__ == "__main__":
    unittest.main()