# tests/test_default_slot_machine.py
import unittest
import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Tuple

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.config.loaders.yaml_loader import YamlConfigLoader
from src.infrastructure.config.validators.schema_validator import SchemaValidator
from src.domain.machine.factories.machine_factory import MachineFactory
from src.infrastructure.rng.rng_provider import RNGProvider
from src.infrastructure.rng.strategies.mersenne_rng import MersenneTwisterRNG


class TestDefaultSlotMachine(unittest.TestCase):
    """Test the default slot machine configuration and performance."""

    def setUp(self):
        """Set up test environment."""
        # Create config loader and validator
        self.schema_validator = SchemaValidator()
        self.config_loader = YamlConfigLoader(self.schema_validator)
        
        # Create RNG provider
        self.rng_provider = RNGProvider()
        
        # Create machine factory
        self.machine_factory = MachineFactory(self.rng_provider)
        
        # Path to default machine config
        self.config_path = "src/application/config/machines/default_machine.yaml"
        
        # Ensure config exists
        self._ensure_config_exists()
        
        # Load the default machine config
        self.config = self.config_loader.load_file(self.config_path)
        
        # Create the default machine
        self.machine = self.machine_factory.create_machine("default", self.config)
        
        # Directory for saving plots
        self.output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _ensure_config_exists(self):
        """Ensure the default machine config exists."""
        if not os.path.exists(self.config_path):
            print(f"config not found, writing config to {self.config_path}")
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                f.write(self._get_default_machine_config())
                
    def _get_default_machine_config(self) -> str:
        """Get default machine configuration."""
        return """
machine_id: "default_slot"
free_spins: 10
free_spins_multiplier: 2
wild_symbol: [101, 102, 103, 104, 105]
scatter_symbol: 20
reels:
  normal:
    reel1: [0, 10, 6, 10, 6, 9, 5, 8, 1, 7, 4, 10, 3, 20, 6, 9, 7, 4, 9, 0, 7, 10, 5, 6, 4, 10, 6, 8, 1, 7, 5, 9, 7, 10, 8, 7, 6, 5, 8, 3, 7, 9, 3, 8, 10, 6, 2, 5, 7, 9, 2, 9, 6, 9, 8, 10, 4, 9, 8, 10, 7, 6, 8, 9, 20, 8, 10]
    reel2: [2, 6, 3, 9, 7, 4, 20, 8, 9, 5, 10, 9, 4, 8, 2, 7, 9, 8, 7, 6, 10, 3, 6, 9, 8, 0, 6, 4, 101, 7, 10, 2, 5, 7, 10, 8, 1, 7, 9, 0, 10, 5, 1, 3, 8, 101, 6, 10, 2, 5, 10, 9, 1, 9, 3, 20, 6, 4, 8, 10, 7, 5, 0, 4, 10, 8, 6]
    reel3: [9, 6, 2, 7, 3, 1, 8, 5, 9, 101, 2, 7, 0, 0, 5, 8, 5, 6, 5, 101, 10, 6, 5, 9, 10, 5, 101, 8, 9, 7, 4, 10, 7, 3, 9, 10, 101, 4, 8, 0, 4, 7, 20, 6, 4, 10, 8, 101, 10, 5, 1, 7, 3, 4, 9, 3, 7, 2, 10, 9, 20]
    reel4: [101, 5, 10, 6, 101, 5, 8, 9, 1, 101, 5, 10, 4, 8, 2, 7, 101, 6, 10, 1, 10, 4, 7, 2, 6, 8, 20, 5, 8, 101, 9, 4, 0, 10, 7, 101, 3, 8, 2, 9, 6, 2, 9, 7, 2, 9, 4, 101, 8, 5, 9, 1, 5, 10, 8, 3, 7, 4, 6, 8, 5, 10, 6, 3, 101, 8, 9, 20, 10, 5, 10, 4, 8, 3, 101, 6, 10, 9, 1, 10, 4, 7, 9, 6, 3, 8, 5, 8, 101, 9, 4, 0, 10, 7, 101, 3, 8, 2, 9, 6, 2, 4, 7, 2, 9, 4, 101, 5, 9, 101, 5, 10, 2, 8, 3, 7, 20, 6]
    reel5: [10, 6, 101, 7, 8, 2, 7, 4, 9, 1, 8, 6, 8, 101, 9, 3, 6, 8, 5, 6, 4, 101, 5, 7, 8, 9, 5, 8, 1, 10, 9, 4, 101, 7, 6, 8, 0, 10, 5, 9, 101, 3, 9, 10, 6, 101, 4, 10, 2, 7, 4, 9, 3, 1, 8, 3, 7, 2, 5, 10, 6, 101, 7, 8, 2, 7, 4, 9, 101, 8, 6, 20, 9, 6, 2, 3, 8, 5, 6, 4, 101, 5, 7, 0, 9, 5, 20, 6, 10, 20, 4, 10, 7, 1, 8, 9, 10, 5, 9, 10, 3, 9, 10, 6, 101, 4, 10, 2, 7, 4, 9, 10, 5, 8, 3, 9, 7, 10]
  bonus:
    reel1: [4, 10, 8, 2, 6, 10, 5, 4, 9, 8, 4, 6, 2, 7, 9, 3, 7, 2, 6, 10, 1, 5, 10, 3, 5, 9, 10, 4, 3, 8, 9, 7, 5, 8, 6, 3, 0, 7, 5, 6, 4, 0, 9, 10, 1, 8, 7]
    reel2: [2, 8, 0, 5, 3, 2, 9, 4, 1, 7, 4, 0, 7, 2, 6, 8, 1, 7, 3, 1, 9, 8, 5, 3, 7, 3, 1, 4, 5, 1, 6, 10, 1, 9, 2, 6, 4, 0, 10, 5, 6, 8, 101, 10, 3, 9, 10]
    reel3: [101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101]
    reel4: [1, 4, 8, 0, 7, 4, 1, 9, 8, 2, 9, 10, 2, 3, 2, 7, 8, 1, 7, 9, 1, 10, 5, 3, 10, 5, 0, 4, 3, 2, 8, 5, 2, 3, 9, 4, 6, 9, 0, 6, 5, 2, 6, 4, 101, 10, 3]
    reel5: [1, 5, 7, 0, 3, 6, 2, 3, 6, 1, 10, 4, 1, 9, 8, 0, 4, 3, 4, 8, 10, 1, 7, 3, 5, 9, 10, 0, 5, 6, 6, 4, 2, 7, 5, 2, 8, 7, 7, 6, 2, 4, 5, 1, 9, 10, 101]
paylines:
  - indices: [0, 1, 2, 3, 4]
  - indices: [5, 6, 7, 8, 9]
  - indices: [10, 11, 12, 13, 14]
  - indices: [0, 6, 12, 8, 4]
  - indices: [10, 6, 2, 8, 14]
  - indices: [5, 1, 2, 3, 9]
  - indices: [5, 11, 12, 13, 9]
  - indices: [0, 1, 7, 13, 14]
  - indices: [10, 11, 7, 3, 4]
  - indices: [5, 1, 7, 13, 9]
pay_table:
  - symbol: "0"
    payouts: [100, 200, 500]
  - symbol: "1"
    payouts: [80, 150, 400]
  - symbol: "2"
    payouts: [60, 120, 300]
  - symbol: "3"
    payouts: [40, 100, 250]
  - symbol: "4"
    payouts: [30, 80, 200]
  - symbol: "5"
    payouts: [20, 60, 180]
  - symbol: "6"
    payouts: [10, 60, 150]
  - symbol: "7"
    payouts: [10, 40, 120]
  - symbol: "8"
    payouts: [10, 40, 100]
  - symbol: "9"
    payouts: [5, 30, 100]
  - symbol: "10"
    payouts: [5, 30, 100]
  - symbol: "20"
    payouts: [10, 40, 100]
bet_table:
  - currency: "USD"
    bet_options: [0.1, 0.2, 0.5, 1.0, 1.6, 3.0, 5.0, 10.0]
  - currency: "CNY"
    bet_options: [0.5, 1.0, 2.5, 5.0, 8.0, 15.0, 20.0, 25.0, 50.0]
"""
        
    def test_default_machine_construction(self):
        """Test default machine construction from config."""
        self.assertEqual(self.machine.id, "default")
        
        # Check reels
        self.assertIn("normal", self.machine.reels)
        self.assertIn("bonus", self.machine.reels)
        self.assertEqual(len(self.machine.reels["normal"]), 5)  # 5 reels
        self.assertEqual(len(self.machine.reels["bonus"]), 5)  # 5 reels
        
        # Check paylines
        self.assertGreaterEqual(len(self.machine.paylines), 25)
        
        # Check pay table
        for i in (list(range(0, 11)) + [20]): 
            self.assertIn(f"{i}", self.machine.pay_table)
        
        # Check bet table
        self.assertIn("USD", self.machine.bet_table)
        self.assertIn("CNY", self.machine.bet_table)
        
        # Print machine info
        info = self.machine.get_info()
        print("\nDefault Machine Info:")
        for key, value in info.items():
            if key != "reel_lengths":  # Too verbose
                print(f"  {key}: {value}")
        
    def test_win_evaluation(self):
        """Test win evaluation on several spins."""
        print("\nTesting win evaluation on 10 spins:")
        
        # Set seed for reproducibility
        self.machine.set_rng(MersenneTwisterRNG(seed_value=12345))
        
        # Track statistics
        total_bet = 0
        total_win = 0
        win_count = 0
        free_spins_count = 0
        line_wins = 0
        scatter_wins = 0
        
        # Do several spins
        num_spins = 10
        bet_amount = 1.0
        
        for i in range(num_spins):
            # Spin
            result, trigger_free, free_remaining = self.machine.spin()
            
            # Evaluate win
            win_data = self.machine.evaluate_win(result, bet=bet_amount)
            
            # Update statistics
            total_bet += bet_amount
            total_win += win_data["total_win"]
            if win_data["total_win"] > 0:
                win_count += 1
            if trigger_free:
                free_spins_count += 1
            if win_data["scatter_win"] > 0:
                scatter_wins += 1
            line_wins += len(win_data["line_wins"])
            
            # Print results
            print(f"  Spin {i+1}: Win={win_data['total_win']:.2f}, "
                  f"Lines={len(win_data['line_wins'])}, "
                  f"Free Spins={trigger_free}")
            
            # Print detailed line wins if any
            for line_win in win_data["line_wins"]:
                print(f"    Line {line_win['line_index']+1}: "
                      f"Symbol={line_win['symbol']}, "
                      f"Count={line_win['match_count']}, "
                      f"Win={line_win['win_amount']:.2f}")
        
        # Print summary
        print("\nWin Evaluation Summary:")
        print(f"  Total Bet: {total_bet:.2f}")
        print(f"  Total Win: {total_win:.2f}")
        print(f"  Win Rate: {win_count/num_spins:.2%}")
        print(f"  Free Spins Rate: {free_spins_count/num_spins:.2%}")
        print(f"  RTP: {total_win/total_bet:.2%}")
        print(f"  Line Wins: {line_wins}")
        print(f"  Scatter Wins: {scatter_wins}")
        
    def test_performance_10k_spins(self):
        """Test performance of 10 sets of 1000 spins."""
        print("\nTesting performance of 10 sets of 1M spins:")
        
        # Set seed for reproducibility
        self.machine.set_rng(MersenneTwisterRNG(seed_value=12345))
        
        # Track statistics
        total_times = []
        total_wins = []
        total_bets = []
        
        # Number of sets and spins per set
        num_sets = 10
        spins_per_set = 1_000_000
        
        # Fixed bet amount
        bet_amount = 1.0
        
        for set_idx in range(num_sets):
            # Track set statistics
            set_win = 0
            set_bet = 0
            free_spins_triggered = 0
            
            # Time the set
            start_time = time.time()
            
            # Run spins
            for _ in range(spins_per_set):
                # Spin
                result, trigger_free, _ = self.machine.spin()
                
                # Evaluate win
                win_data = self.machine.evaluate_win(result, bet=bet_amount)
                
                # Update statistics
                set_bet += bet_amount
                set_win += win_data["total_win"]
                
                if trigger_free:
                    free_spins_triggered += 1
            
            # Calculate time
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Store results
            total_times.append(elapsed_time)
            total_wins.append(set_win)
            total_bets.append(set_bet)
            
            # Print set summary
            print(f"  Set {set_idx+1}: Time={elapsed_time:.2f}s, "
                  f"Win={set_win:.2f}, "
                  f"Bet={set_bet:.2f}, "
                  f"RTP={set_win/set_bet:.2%}, "
                  f"Free Spins={free_spins_triggered}")
        
        # Calculate statistics
        avg_time = sum(total_times) / len(total_times)
        avg_win = sum(total_wins) / len(total_wins)
        avg_bet = sum(total_bets) / len(total_bets)
        avg_rtp = avg_win / avg_bet
        
        # Print overall summary
        print("\nPerformance Summary:")
        print(f"  Average Time per Set: {avg_time:.2f}s")
        print(f"  Spins per Second: {spins_per_set/avg_time:.2f}")
        print(f"  Total Spins: {num_sets * spins_per_set}")
        print(f"  Total Bet: {avg_bet:.2f}")
        print(f"  Total Win: {avg_win:.2f}")
        # print(f"  Win Rate: {win_count/num_spins:.2%}")
        # print(f"  Free Spins Rate: {free_spins_count/num_spins:.2%}")
        # print(f"  RTP: {total_win/total_bet:.2%}")
        # print(f"  Line Wins: {line_wins}")
        # print(f"  Scatter Wins: {scatter_wins}")
        print(f"  Average RTP: {avg_rtp:.2%}")
        
        # Plot RTP distribution
        # rtps = [win/bet for win, bet in zip(total_wins, total_bets)]
        # self._plot_rtp_distribution(rtps)
        
    def _plot_rtp_distribution(self, rtps: List[float]):
        """Plot RTP distribution."""
        plt.figure(figsize=(10, 6))
        
        # Plot RTPs
        plt.bar(range(len(rtps)), rtps, alpha=0.7)
        
        # Add average line
        avg_rtp = sum(rtps) / len(rtps)
        plt.axhline(y=avg_rtp, color='r', linestyle='-', 
                   label=f'Average RTP: {avg_rtp:.2%}')
        
        # Add theoretical RTP if known
        # theoretical_rtp = 0.95  # Example
        # plt.axhline(y=theoretical_rtp, color='g', linestyle='--', 
        #            label=f'Theoretical RTP: {theoretical_rtp:.2%}')
        
        # Set labels and title
        plt.xlabel('Test Set')
        plt.ylabel('RTP')
        plt.title('RTP Distribution Across Test Sets')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Save plot
        plot_path = os.path.join(self.output_dir, 'rtp_distribution.png')
        plt.savefig(plot_path)
        print(f"  RTP distribution plot saved to {plot_path}")
        plt.close()


if __name__ == "__main__":
    unittest.main()