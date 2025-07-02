import unittest
from src.domain.machine.services.win_evaluation import WinEvaluator  # 根据你本地路径调整

class TestWinEvaluatorExtended(unittest.TestCase):
    def setUp(self):
        self.pay_table = {
            "0": [10, 20, 30],
            "1": [15, 25, 35],
            "2": [20, 30, 40],
            "20": [5, 10, 20]  # scatter
        }
        self.paylines_3x5 = [
            [0, 1, 2, 3, 4],
            [5, 6, 7, 8, 9],
            [10, 11, 12, 13, 14],
            [0, 6, 12, 8, 4],
            [10, 6, 2, 8, 14]
        ]
        self.wild_symbols = [101, 102, 202]  # 101: x1, 102: x2, 202: x2
        self.scatter_symbol = 20

    def run_eval_and_assert(self, grid, expected_total, expected_lines, bet=1.0, multiplier=1.0):
        result = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines_3x5,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=bet,
            active_lines=len(self.paylines_3x5),
            free_multiplier=multiplier
        )
        self.assertAlmostEqual(result["total_win"], expected_total)
        self.assertEqual(len(result["line_wins"]), expected_lines)

    def test_five_of_a_kind_direct(self):
        self.run_eval_and_assert(
            grid=[0, 0, 0, 0, 0, 1, 2, 3, 4, 1, 2, 1, 0, 1, 2],
            expected_total=30,
            expected_lines=1
        )

    def test_wild_substitution_middle(self):
        self.run_eval_and_assert(
            grid=[0, 101, 0, 0, 0, 1, 2, 3, 4, 1, 2, 1, 0, 1, 2],
            expected_total=30,
            expected_lines=1
        )

    def test_wild_multiplier_applied(self):
        self.run_eval_and_assert(
            grid=[0, 202, 0, 0, 0, 1, 2, 3, 4, 1, 2, 1, 0, 1, 2],
            expected_total=60,
            expected_lines=1
        )

    def test_scatter_only(self):
        self.run_eval_and_assert(
            grid=[20, 20, 0, 0, 0, 1, 20, 3, 4, 1, 2, 1, 0, 1, 2],
            expected_total=5,
            expected_lines=0
        )

    def test_wild_cannot_start_line(self):
        self.run_eval_and_assert(
            grid=[101, 0, 0, 0, 0, 1, 2, 3, 4, 1, 2, 1, 0, 1, 2],
            expected_total=0,
            expected_lines=0
        )

    def test_nonexistent_symbol_in_paytable(self):
        self.run_eval_and_assert(
            grid=[99, 99, 99, 99, 99, 1, 2, 3, 4, 1, 2, 1, 0, 1, 2],
            expected_total=0,
            expected_lines=0
        )

    def test_multiple_line_hits(self):
        self.run_eval_and_assert(
            grid=[0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 1, 0, 1, 2],
            expected_total=30 + 35,
            expected_lines=2
        )

    def test_bet_scaling(self):
        grid = [0, 0, 0, 0, 0, 1, 2, 3, 4, 1, 2, 1, 0, 1, 2]
        base_result = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines_3x5,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=1.0,
            active_lines=5
        )
        scaled_result = WinEvaluator.evaluate_wins(
            grid=grid,
            paylines=self.paylines_3x5,
            wild_symbols=self.wild_symbols,
            scatter_symbol=self.scatter_symbol,
            pay_table=self.pay_table,
            bet=2.0,
            active_lines=5
        )
        self.assertAlmostEqual(scaled_result["total_win"], base_result["total_win"] * 2)

    def test_free_spin_multiplier(self):
        self.run_eval_and_assert(
            grid=[0, 0, 0, 0, 0, 1, 2, 3, 4, 1, 2, 1, 0, 1, 2],
            expected_total=60,
            expected_lines=1,
            multiplier=2.0
        )


if __name__ == "__main__":
    unittest.main()
