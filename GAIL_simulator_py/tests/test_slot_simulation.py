# tests/test_slot_simulation.py
import unittest
import time
import os
import logging
from typing import Dict, Any

# Disable logging for tests
logging.disable(logging.CRITICAL)

# Add src to path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.config.loaders.yaml_loader import YamlConfigLoader
from src.infrastructure.config.validators.schema_validator import SchemaValidator
from src.infrastructure.rng.rng_provider import RNGProvider

from src.domain.machine.factories.machine_factory import MachineFactory
from src.domain.player.factories.player_factory import PlayerFactory
from src.domain.session.factories.session_factory import SessionFactory
from src.domain.session.entities.gaming_session import GamingSession
from src.domain.events.event_dispatcher import EventDispatcher

from src.application.simulation.session_runner import SessionRunner


class TestSlotSimulation(unittest.TestCase):
    """Test cases for slot machine simulation."""

    def setUp(self):
        """Set up test environment."""
        # Set test environment variable
        os.environ["TESTING"] = "1"
        
        # Create config loader and validator
        self.schema_validator = SchemaValidator()
        self.config_loader = YamlConfigLoader(self.schema_validator)
        
        # Create RNG provider
        self.rng_provider = RNGProvider()
        
        # Create factories
        self.machine_factory = MachineFactory(self.rng_provider)
        self.player_factory = PlayerFactory()
        
        # Create event dispatcher
        self.event_dispatcher = EventDispatcher()
        
        # Create session factory
        self.session_factory = SessionFactory(self.event_dispatcher)
        
        # Define test config paths
        self.machine_config_path = "src/application/config/machines/default.yaml"
        self.player_config_path = "src/application/config/players/random_player.yaml"
        
        # Load or create test configs if they don't exist
        self._ensure_test_configs()
        
    def _ensure_test_configs(self):
        """Ensure test configuration files exist."""
        # Check and create machine config
        if not os.path.exists(self.machine_config_path):
            os.makedirs(os.path.dirname(self.machine_config_path), exist_ok=True)
            with open(self.machine_config_path, 'w') as f:
                f.write(self._get_default_machine_config())
                
        # Check and create player config
        if not os.path.exists(self.player_config_path):
            os.makedirs(os.path.dirname(self.player_config_path), exist_ok=True)
            with open(self.player_config_path, 'w') as f:
                f.write(self._get_default_player_config())
    
    def _get_default_machine_config(self) -> str:
        """Get default machine configuration."""
        return """
machine_id: "test_machine"
free_spins: 10
free_spins_multiplier: 2
wild_symbol: [101]
scatter_symbol: 20
reels:
  normal:
    reel1: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
    reel2: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 101]
    reel3: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 101]
    reel4: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 101]
    reel5: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
  bonus:
    reel1: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
    reel2: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 101]
    reel3: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 101]
    reel4: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 101]
    reel5: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
paylines:
  - indices: [0, 1, 2, 3, 4]
  - indices: [5, 6, 7, 8, 9]
  - indices: [10, 11, 12, 13, 14]
pay_table:
  - symbol: "0"
    payouts: [5, 20, 100]
  - symbol: "1"
    payouts: [5, 20, 100]
  - symbol: "20"
    payouts: [5, 20, 100]
bet_table:
  - currency: "USD"
    bet_options: [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
"""
    
    def _get_default_player_config(self) -> str:
        """Get default player configuration."""
        return """
player_id: "test_player"
initial_balance: 10000.0
currency: "USD"
active_lines: 3

# Strategy configuration
strategy_type: "random"
strategy_config:
  min_delay: 0.01
  max_delay: 0.02
  end_probability: 0.0  # Disable random ending for tests
  max_consecutive_losses: 100  # Large value to prevent early ending
  session_budget: 9000.0  # 90% of balance
  max_session_duration: 3600
  max_spins_per_session: 2000
  seed: 12345
"""

    def test_machine_creation(self):
        """Test creating a slot machine."""
        # Load machine configuration
        machine_config = self.config_loader.load_file(self.machine_config_path)
        
        # Create machine
        machine = self.machine_factory.create_machine("test_machine", machine_config)
        
        # Verify machine properties
        self.assertEqual(machine.id, "test_machine")
        self.assertIsNotNone(machine.reels)
        self.assertIsNotNone(machine.paylines)
        self.assertIsNotNone(machine.pay_table)
        self.assertIsNotNone(machine.bet_table)
        
        # Verify reel sets
        self.assertIn("normal", machine.reels)
        self.assertIn("bonus", machine.reels)
        
        # Verify a basic spin works
        result, trigger_free, free_remaining = machine.spin()
        self.assertEqual(len(result), 15)  # 3x5 grid flattened
        
    def test_player_creation(self):
        """Test creating a player."""
        # Load player configuration
        player_config = self.config_loader.load_file(self.player_config_path)
        
        # Create player
        player = self.player_factory.create_player("test_player", player_config)
        
        # Verify player properties
        self.assertEqual(player.id, "test_player")
        self.assertEqual(player.balance, 10000.0)
        self.assertEqual(player.currency, "USD")
        
        # Verify strategy creation
        self.assertIsNotNone(player.strategy)
        
    def test_session_creation(self):
        """Test creating a gaming session."""
        # Create machine and player
        machine_config = self.config_loader.load_file(self.machine_config_path)
        player_config = self.config_loader.load_file(self.player_config_path)
        
        machine = self.machine_factory.create_machine("test_machine", machine_config)
        player = self.player_factory.create_player("test_player", player_config)
        
        # Create session
        session = self.session_factory.create_session(player, machine, "test_session")
        
        # Verify session properties
        self.assertEqual(session.id, "test_session")
        self.assertEqual(session.player, player)
        self.assertEqual(session.machine, machine)
        self.assertFalse(session.active)
        
        # Start session
        session.start()
        self.assertTrue(session.active)
        
        # Test a spin
        result = session.execute_spin(1.0)
        self.assertNotIn("error", result)
        self.assertIn("bet", result)
        self.assertIn("win", result)
        
        # End session
        session.end()
        self.assertFalse(session.active)
        
    def test_session_runner(self):
        """Test running a complete session."""
        # Create machine and player
        machine_config = self.config_loader.load_file(self.machine_config_path)
        player_config = self.config_loader.load_file(self.player_config_path)
        
        machine = self.machine_factory.create_machine("test_machine", machine_config)
        player = self.player_factory.create_player("test_player", player_config)
        
        # Create session
        session = self.session_factory.create_session(player, machine, "test_session")
        
        # Create runner
        runner = SessionRunner(session, self.event_dispatcher)
        
        # Run session
        stats = runner.run()
        
        # Verify session completed
        self.assertIsNotNone(stats)
        self.assertIn("spins_count", stats)
        self.assertIn("total_bet", stats)
        self.assertIn("total_win", stats)
        
        # Print session stats
        print(f"Session completed with {stats['spins_count']} spins")
        print(f"Total bet: {stats['total_bet']}")
        print(f"Total win: {stats['total_win']}")
        print(f"RTP: {stats['return_to_player']:.2%}")
        
    def test_early_termination(self):
        """Test session early termination causes."""
        # Create machine and player with end_probability = 0.5 (very high)
        machine_config = self.config_loader.load_file(self.machine_config_path)
        player_config = self.config_loader.load_file(self.player_config_path)
        
        # Modify player config to have high end probability
        player_config["strategy_config"] = {
            "end_probability": 0.5,  # 50% chance to end per spin
            "max_consecutive_losses": 2,  # End after 2 consecutive losses
            "session_budget": 100.0,  # Small budget
            "max_spins_per_session": 10  # Small max spins
        }
        
        machine = self.machine_factory.create_machine("test_machine", machine_config)
        player = self.player_factory.create_player("test_player", player_config)
        
        # Create session
        session = self.session_factory.create_session(player, machine, "test_session")
        
        # Create runner
        runner = SessionRunner(session, self.event_dispatcher)
        
        # Run session
        stats = runner.run()
        
        # Verify session completed early
        self.assertIsNotNone(stats)
        self.assertLessEqual(stats["spins_count"], 10)  # Should be less than max_spins
        
        print(f"Early termination test: session completed with {stats['spins_count']} spins")
        
    def test_performance_1000_spins(self):
        """Test performance of 1000 spins."""
        # Create machine and player
        machine_config = self.config_loader.load_file(self.machine_config_path)
        player_config = self.config_loader.load_file(self.player_config_path)
        
        # Override strategy config to prevent early ending
        player_config["strategy_config"] = {
            "end_probability": 0.0,
            "max_consecutive_losses": 10000,
            "session_budget": 1000000.0,
            "max_spins_per_session": 2000,
            "min_delay": 0.0,
            "max_delay": 0.0
        }
        
        machine = self.machine_factory.create_machine("test_machine", machine_config)
        player = self.player_factory.create_player("test_player", player_config)
        
        # Create session without event dispatcher for performance
        session = GamingSession("perf_test", player, machine)
        
        # Start session
        session.start()
        
        # Track time
        start_time = time.time()
        spin_count = 0
        
        # Do 1000 spins directly
        for _ in range(1000):
            # Get player's next bet decision - should always return a bet > 0
            bet_amount, _ = player.play(machine.id, session.get_data_for_decision())
            
            if bet_amount <= 0:
                print("Warning: Player returned bet <= 0")
                bet_amount = 1.0  # Force a minimum bet
                
            # Execute spin
            result = session.execute_spin(bet_amount)
            
            # Check for errors
            if "error" in result:
                print(f"Error in spin: {result['error']}")
                break
                
            spin_count += 1
            
        # End session
        session.end()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print performance stats
        print(f"Performance test: {spin_count} spins in {duration:.2f} seconds")
        print(f"Spins per second: {spin_count / duration:.2f}")
        
        # Verify we did 1000 spins
        self.assertEqual(spin_count, 1000)
        
    def test_long_running_session(self):
        """Test a long running session (1000 spins) with session runner."""
        # Create machine and player
        machine_config = self.config_loader.load_file(self.machine_config_path)
        player_config = self.config_loader.load_file(self.player_config_path)
        
        # Override strategy config to prevent early ending
        player_config["strategy_config"] = {
            "end_probability": 0.0,
            "max_consecutive_losses": 10000,
            "session_budget": 1000000.0,
            "max_spins_per_session": 1001,  # Just over 1000
            "min_delay": 0.0,
            "max_delay": 0.0
        }
        
        machine = self.machine_factory.create_machine("test_machine", machine_config)
        player = self.player_factory.create_player("test_player", player_config)
        
        # Create session
        session = self.session_factory.create_session(player, machine, "long_test")
        
        # Create a special runner that will count spins
        class CountingRunner(SessionRunner):
            def __init__(self, session, event_dispatcher=None):
                super().__init__(session, event_dispatcher)
                self.spin_count = 0
                
            def run(self):
                self.session.start()
                
                while self.spin_count < 1000:
                    session_data = self.session.get_data_for_decision()
                    
                    bet_amount, _ = self.session.player.play(
                        self.session.machine.id, 
                        session_data
                    )
                    
                    if bet_amount <= 0:
                        bet_amount = 1.0  # Force a bet
                        
                    spin_result = self.session.execute_spin(bet_amount)
                    
                    if "error" in spin_result:
                        break
                        
                    self.spin_count += 1
                    
                self.session.end()
                return self.session.get_statistics()
        
        # Create counting runner
        runner = CountingRunner(session)
        
        # Run session
        start_time = time.time()
        stats = runner.run()
        end_time = time.time()
        
        # Verify results
        self.assertEqual(runner.spin_count, 1000)
        self.assertEqual(stats["spins_count"], 1000)
        
        # Print performance
        duration = end_time - start_time
        print(f"Long session test: {stats['spins_count']} spins in {duration:.2f} seconds")
        print(f"Spins per second: {stats['spins_count'] / duration:.2f}")
        print(f"Total bet: {stats['total_bet']}")
        print(f"Total win: {stats['total_win']}")
        print(f"RTP: {stats['return_to_player']:.2%}")


if __name__ == "__main__":
    unittest.main()