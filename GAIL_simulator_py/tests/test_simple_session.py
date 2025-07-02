# tests/test_simple_session.py
import sys
import os
import time
import logging

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.infrastructure.config.loaders.yaml_loader import YamlConfigLoader
from src.infrastructure.config.validators.schema_validator import SchemaValidator
from src.infrastructure.rng.rng_provider import RNGProvider

from src.domain.machine.factories.machine_factory import MachineFactory
from src.domain.player.factories.player_factory import PlayerFactory
from src.domain.session.factories.session_factory import SessionFactory
from src.domain.events.event_dispatcher import EventDispatcher

from src.application.simulation.session_runner import SessionRunner


def run_simple_test():
    """运行一个简单的会话测试，验证系统正常工作。"""
    print("Starting simple session test...")
    
    # 创建配置加载器和验证器
    validator = SchemaValidator()
    config_loader = YamlConfigLoader(validator)
    
    # 创建RNG提供器
    rng_provider = RNGProvider()
    
    # 创建事件分发器
    event_dispatcher = EventDispatcher()
    
    # 确保配置目录存在
    os.makedirs("src/application/config/machines", exist_ok=True)
    os.makedirs("src/application/config/players", exist_ok=True)
    
    # 检查并创建默认配置文件
    machine_config_path = "src/application/config/machines/default.yaml"
    player_config_path = "src/application/config/players/random_player.yaml"
    
    if not os.path.exists(machine_config_path):
        print(f"Warning: Machine config not found at {machine_config_path}")
        print("Please create a machine configuration file before running this test.")
        return
        
    if not os.path.exists(player_config_path):
        print(f"Warning: Player config not found at {player_config_path}")
        print("Please create a player configuration file before running this test.")
        return
    
    # 加载配置
    try:
        machine_config = config_loader.load_file(machine_config_path)
        player_config = config_loader.load_file(player_config_path)
        
        print("Successfully loaded configurations")
    except Exception as e:
        print(f"Error loading configurations: {str(e)}")
        return
    
    # 创建工厂
    machine_factory = MachineFactory(rng_provider)
    player_factory = PlayerFactory()
    session_factory = SessionFactory(event_dispatcher)
    
    try:
        # 创建老虎机
        machine = machine_factory.create_machine("test_machine", machine_config)
        print(f"Created machine: {machine.id}")
        
        # 创建玩家
        player = player_factory.create_player("test_player", player_config)
        print(f"Created player: {player.id} with model version: {player.model_version}")
        
        # 创建会话
        session = session_factory.create_session(player, machine, "test_session")
        print(f"Created session: {session.id}")
        
        # 创建会话运行器
        runner = SessionRunner(session, event_dispatcher)
        
        # 运行会话
        print("Running session...")
        start_time = time.time()
        
        statistics = runner.run()
        
        duration = time.time() - start_time
        print(f"Session completed in {duration:.2f} seconds")
        
        # Print statistics
        print("\nSession Statistics:")

        print(f"Total spins: {statistics['total_spins']:.2f}")
        print(f"Total bet: {statistics['total_bet']:.2f}")
        print(f"Total win: {statistics['total_win']:.2f}")
        print(f"Return to player: {(statistics['return_to_player'] * 100):.4f}%")

        print(statistics)
        
        print("\nSimple session test completed successfully!")
        return statistics
    
    except Exception as e:
        print(f"Error during session execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    run_simple_test()