# src/domain/machine/services/win_evaluation.py
import logging
from typing import List, Dict, Any, Optional, Union, Tuple


class WinEvaluator:
    """
    Service for evaluating slot machine win combinations.
    Provides static methods for win evaluation logic.
    """

    def __init__(self, slot_machine):
        self._paylines = slot_machine.paylines
        self._normal_symbols = slot_machine.normal_symbols
        self._wild_symbols = slot_machine.wild_symbols
        self._scatter_symbol = slot_machine.scatter_symbol
        self._pay_table = slot_machine.pay_table
        self._free_multiplier = slot_machine.free_spins_multiplier

        self._wild_multipliers = {s: self._gen_wild_multiplier(s) for s in self._wild_symbols}

        self.logger = logging.getLogger("domain.machine.win_evaluator")
    

    def _is_scatter(self, symbol: int) -> bool:
        return symbol == self._scatter_symbol
    
    def _is_wild(self, symbol: int) -> bool:
        return symbol in self._wild_symbols
    
    def _gen_wild_multiplier(self, symbol: int) -> int:
        if symbol < 100:
            return 1
        
        multiplier = symbol % 100
        return multiplier if multiplier > 0 else 1
    
    def _get_wild_multiplier(self, symbol: int) -> int:
        return self._wild_multipliers.get(symbol, 1)
    

    def evaluate_wins(self, grid: List[int], bet: float, in_free: bool, active_lines: Optional[int]) -> Dict[str, Any]:
        if not grid:
            error_msg = f"Invalid input values! grid: {grid}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Set default active lines if None
        if active_lines is None:
            active_lines = len(self._paylines)
        else:
            _lines = max(1, min(active_lines, len(self._paylines)))
            if _lines != active_lines:
                self.logger.warning(f"Payline count adjusted: {active_lines} → {_lines}")
                active_lines = _lines

        base_multiplier = self._free_multiplier if in_free else 1

        total_win = 0
        line_wins = []          # Shape=(len(payline), ), amount of win amount for each payline
        line_wins_info = []     # List[Dict[str, Any]], list of winning payline's detailed info
        
        # Precompute scatter symbol information
        scatter_count = grid.count(self._scatter_symbol)
        scatter_win = 0
        
        # Process scatter wins
        if scatter_count >= 3:
            scatter_index = min(scatter_count - 3, 2)  # 0=3 symbols, 1=4 symbols, 2=5 symbols
            scatter_pays = self._pay_table.get(str(self._scatter_symbol), [])
            
            if scatter_index < len(scatter_pays):
                scatter_win = scatter_pays[scatter_index] * bet
                total_win += scatter_win
        
        # Check each active payline
        for line_idx in range(active_lines):
            if line_idx >= len(self._paylines):
                break
                
            line_result = self._evaluate_line(grid, self._paylines[line_idx], bet, line_idx, base_multiplier)
            
            line_wins.append(line_result["win_amount"])

            if line_result["win_amount"] > 0:
                line_wins_info.append(line_result)
                total_win += line_result["win_amount"]
        
        return {
            "total_win": total_win,
            "line_wins": line_wins,
            "line_wins_info": line_wins_info,
            "scatter_count": scatter_count,
            "scatter_win": scatter_win
        }
    

    def _evaluate_line(self, grid: List[int], payline: List[int], bet: float, line_idx: int, base_multiplier: float) -> Dict[str, Any]: 
        result = {
            "line_index": line_idx,
            "win_amount": 0,
            "match_count": 0,
            "symbol": -1,
            "multiplier": base_multiplier
        }
        
        if not payline or len(payline) < 3 or not grid:
            return result
        
        # Ensure first position is valid
        first_pos = payline[0]
        if first_pos >= len(grid):
            return result
        
        # Get first symbol
        first_symbol = grid[first_pos]
        
        # Can't start with a wild symbol or scatter
        if self._is_wild(first_symbol) or self._is_scatter(first_symbol):
            return result
        
        # Check if symbol exists in pay table
        symbol_str = str(first_symbol)
        if symbol_str not in self._pay_table:
            return result
        
        # Start counting consecutive matches
        result["symbol"] = first_symbol
        result["match_count"] = 1
        multiplier = base_multiplier
        
        # Check remaining positions
        for i in range(1, len(payline)):
            pos = payline[i]
            if pos >= len(grid):
                break
                
            current_symbol = grid[pos]
            
            # Wild symbol match
            if self._is_wild(current_symbol):
                result["match_count"] += 1
                wild_multiplier = self._get_wild_multiplier(current_symbol)
                multiplier *= wild_multiplier
            # Same symbol match
            elif current_symbol == first_symbol:
                result["match_count"] += 1
            # No match - stop
            else:
                break
        
        # Need at least 3 consecutive matches
        if result["match_count"] < 3:
            return result
        
        # Calculate win amount
        win_index = result["match_count"] - 3  # 0=3 matches, 1=4 matches, 2=5 matches
        symbol_pays = self._pay_table.get(symbol_str, [])
        num_lines = len(self._paylines)
        
        if win_index < len(symbol_pays):
            result["win_amount"] = symbol_pays[win_index] * bet * multiplier / num_lines
        
        result["multiplier"] = multiplier

        return result