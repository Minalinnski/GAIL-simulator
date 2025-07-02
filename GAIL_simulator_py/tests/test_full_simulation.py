# tests/test_full_simulation.py
import sys
import os
import time
import logging
import json
from typing import Dict, Any
from pathlib import Path

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
from src.infrastructure.concurrency.task_executor import TaskExecutor, ExecutionMode

from src.domain.events.event_dispatcher import EventDispatcher

from src.application.registry.registry_service import RegistryService
from src.application.simulation.coordinator import SimulationCoordinator


def _create_test_config() -> Dict[str, Any]:
    """创建测试配置字典"""
    return {
        "initial_balance": 1000.0,
        "file_configs": {
            "machines": {
                "dir": "src/application/config/machines",
                "selection": {
                    "mode": "all",
                    "files": []
                }
            },
            "players": {
                "dir": "src/application/config/players",
                "selection": {
                    "mode": "all",
                    "files": []
                }
            }
        },
        "sessions_per_pair": 5,
        "use_concurrency": True,
        "batch_size": 100,
        "max_spins": 1000,
        "max_sim_duration": 60,  # 1分钟
        "max_player_duration": 3600,  # 1小时
        "analysis": {
            "generate_reports": True,
            "output_dir": "tests/outputs/reports"
        }
    }


def test_basic_simulation():
    """测试基本的模拟功能，使用默认配置"""
    print("Starting basic simulation test...")
    
    # 创建配置加载器和验证器
    validator = SchemaValidator()
    config_loader = YamlConfigLoader(validator)
    
    # 创建RNG提供器
    rng_provider = RNGProvider()
    
    # 事件调度器
    event_dispatcher = EventDispatcher()
    
    # 任务执行器
    task_executor = TaskExecutor(ExecutionMode.THREADED)
    
    # 注册服务
    registry_service = RegistryService(config_loader, rng_provider)
    
    # 创建测试配置
    config = _create_test_config()
    
    # 加载实体
    loading_results = registry_service.load_from_config(config)
    
    # 检查是否加载成功
    if not loading_results["machines"] or not loading_results["players"]:
        print("Error: No machines or players loaded")
        return
        
    print(f"Loaded {len(loading_results['machines'])} machines and {len(loading_results['players'])} players")
    
    # 创建模拟协调器
    coordinator = SimulationCoordinator(
        registry_service.machine_registry,
        registry_service.player_registry,
        event_dispatcher,
        task_executor
    )
    
    # 运行模拟
    print("Running simulation...")
    start_time = time.time()
    
    results = coordinator.run_simulation(config)
    
    duration = time.time() - start_time
    print(f"Simulation completed in {duration:.2f} seconds")
    
    # 检查结果
    print("\nSimulation Results:")
    print(f"Total sessions: {len(results['sessions'])}")
    
    # 计算总计
    total_spins = sum(s.get("total_spins", 0) for s in results["sessions"])
    total_bet = sum(s.get("total_bet", 0) for s in results["sessions"])
    total_win = sum(s.get("total_win", 0) for s in results["sessions"])
    
    if total_bet > 0:
        overall_rtp = total_win / total_bet
    else:
        overall_rtp = 0.0
        
    print(f"Total spins: {total_spins}")
    print(f"Total bet: {total_bet:.2f}")
    print(f"Total win: {total_win:.2f}")
    print(f"Overall RTP: {overall_rtp:.4f} ({overall_rtp*100:.2f}%)")
    
    # 保存结果
    output_dir = Path("tests/outputs/simulation")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "basic_simulation_results.json", "w") as f:
        # 转换为可序列化对象
        serializable_results = {
            "start_time": results["start_time"],
            "end_time": results["end_time"],
            "duration": results["duration"],
            "total_sessions": len(results["sessions"]),
            "total_spins": total_spins,
            "total_bet": total_bet,
            "total_win": total_win,
            "overall_rtp": overall_rtp,
            "session_summary": [
                {
                    "session_id": s.get("session_id", "unknown"),
                    "player_id": s.get("player_id", "unknown"),
                    "machine_id": s.get("machine_id", "unknown"),
                    "total_spins": s.get("total_spins", 0),
                    "total_bet": s.get("total_bet", 0),
                    "total_win": s.get("total_win", 0),
                    "rtp": s.get("return_to_player", 0),
                    "duration": s.get("duration", 0),
                    "player_duration": s.get("player_duration", 0)
                }
                for s in results["sessions"][:10]  # 只保存前10个会话的详细信息
            ]
        }
        
        json.dump(serializable_results, f, indent=2)
    
    print(f"Results saved to {output_dir / 'basic_simulation_results.json'}")
    
    return results


def test_file_selection():
    """测试文件选择功能"""
    print("\nTesting file selection functionality...")
    
    # 创建配置加载器和验证器
    validator = SchemaValidator()
    config_loader = YamlConfigLoader(validator)
    
    # 创建RNG提供器
    rng_provider = RNGProvider()
    
    # 事件调度器
    event_dispatcher = EventDispatcher()
    
    # 任务执行器
    task_executor = TaskExecutor(ExecutionMode.THREADED)
    
    # 创建基础测试配置
    base_config = _create_test_config()
    
    # 获取所有可用的机器和玩家文件
    machine_dir = base_config["file_configs"]["machines"]["dir"]
    player_dir = base_config["file_configs"]["players"]["dir"]
    
    machine_files = [f for f in os.listdir(machine_dir) if f.endswith('.yaml') or f.endswith('.yml')]
    player_files = [f for f in os.listdir(player_dir) if f.endswith('.yaml') or f.endswith('.yml')]
    
    print(f"Available machine files: {machine_files}")
    print(f"Available player files: {player_files}")
    
    # 测试各种选择模式
    test_cases = [
        {
            "name": "all_files",
            "config": {
                "machines": {"mode": "all", "files": []},
                "players": {"mode": "all", "files": []}
            }
        },
        {
            "name": "include_first_machine",
            "config": {
                "machines": {"mode": "include", "files": [machine_files[0]]},
                "players": {"mode": "all", "files": []}
            }
        },
        {
            "name": "exclude_first_machine",
            "config": {
                "machines": {"mode": "exclude", "files": [machine_files[0]]},
                "players": {"mode": "all", "files": []}
            }
        },
        {
            "name": "include_first_player",
            "config": {
                "machines": {"mode": "all", "files": []},
                "players": {"mode": "include", "files": [player_files[0]]}
            }
        },
        {
            "name": "exclude_first_player",
            "config": {
                "machines": {"mode": "all", "files": []},
                "players": {"mode": "exclude", "files": [player_files[0]]}
            }
        },
        {
            "name": "include_first_of_each",
            "config": {
                "machines": {"mode": "include", "files": [machine_files[0]]},
                "players": {"mode": "include", "files": [player_files[0]]}
            }
        }
    ]
    
    results = {}
    
    for test_case in test_cases:
        case_name = test_case["name"]
        selection_config = test_case["config"]
        
        print(f"\nRunning test case: {case_name}")
        
        # 创建注册服务
        registry_service = RegistryService(config_loader, rng_provider)
        
        # 创建测试配置副本
        config = base_config.copy()
        config["file_configs"]["machines"]["selection"] = selection_config["machines"]
        config["file_configs"]["players"]["selection"] = selection_config["players"]
        
        # 加载实体
        loading_results = registry_service.load_from_config(config)
        
        # 检查是否加载成功
        if not loading_results["machines"] or not loading_results["players"]:
            print(f"Error in test case {case_name}: No machines or players loaded")
            continue
            
        machine_count = len(loading_results["machines"])
        player_count = len(loading_results["players"])
        
        print(f"  Loaded {machine_count} machines and {player_count} players")
        
        # 创建模拟协调器
        coordinator = SimulationCoordinator(
            registry_service.machine_registry,
            registry_service.player_registry,
            event_dispatcher,
            task_executor
        )
        
        # 运行短时间的模拟
        config["max_spins"] = 100  # 减少旋转次数以加快测试
        config["sessions_per_pair"] = 1  # 减少会话数
        
        # 运行模拟
        start_time = time.time()
        sim_results = coordinator.run_simulation(config)
        duration = time.time() - start_time
        
        # 添加到结果
        results[case_name] = {
            "machine_count": machine_count,
            "player_count": player_count,
            "session_count": len(sim_results["sessions"]),
            "duration": duration
        }
        
        print(f"  Simulation completed in {duration:.2f} seconds with {len(sim_results['sessions'])} sessions")
        
    # 输出总结
    print("\nFile Selection Test Summary:")
    print(f"{'Test Case':<25} {'Machines':<10} {'Players':<10} {'Sessions':<10} {'Duration (s)':<12}")
    print("-" * 67)
    
    for case_name, case_results in results.items():
        print(f"{case_name:<25} {case_results['machine_count']:<10} {case_results['player_count']:<10} "
              f"{case_results['session_count']:<10} {case_results['duration']:>11.2f}")
    
    return results


def test_concurrent_vs_sequential():
    """测试并行与顺序执行的性能比较"""
    print("\nComparing concurrent vs sequential execution...")
    
    # 创建配置加载器和验证器
    validator = SchemaValidator()
    config_loader = YamlConfigLoader(validator)
    
    # 创建RNG提供器
    rng_provider = RNGProvider()
    
    # 事件调度器
    event_dispatcher = EventDispatcher()
    
    # 创建测试配置
    config = _create_test_config()
    config["sessions_per_pair"] = 10  # 增加会话数以便更好地测试并发性能
    
    # 创建注册服务
    registry_service = RegistryService(config_loader, rng_provider)
    
    # 加载实体
    loading_results = registry_service.load_from_config(config)
    
    # 测试顺序执行
    print("Testing sequential execution...")
    config["use_concurrency"] = False
    
    # 创建顺序执行器
    sequential_executor = TaskExecutor(ExecutionMode.SEQUENTIAL)
    
    # 创建协调器
    sequential_coordinator = SimulationCoordinator(
        registry_service.machine_registry,
        registry_service.player_registry,
        event_dispatcher,
        sequential_executor
    )
    
    # 运行模拟
    sequential_start = time.time()
    sequential_results = sequential_coordinator.run_simulation(config)
    sequential_duration = time.time() - sequential_start
    
    # 重置注册表
    registry_service.reset_all()
    
    # 测试并行执行
    print("Testing concurrent execution...")
    config["use_concurrency"] = True
    
    # 创建并行执行器
    concurrent_executor = TaskExecutor(ExecutionMode.THREADED)
    
    # 创建协调器
    concurrent_coordinator = SimulationCoordinator(
        registry_service.machine_registry,
        registry_service.player_registry,
        event_dispatcher,
        concurrent_executor
    )
    
    # 运行模拟
    concurrent_start = time.time()
    concurrent_results = concurrent_coordinator.run_simulation(config)
    concurrent_duration = time.time() - concurrent_start
    
    # 比较结果
    sequential_sessions = len(sequential_results["sessions"])
    concurrent_sessions = len(concurrent_results["sessions"])
    
    print("\nPerformance Comparison:")
    print(f"Sequential: {sequential_sessions} sessions in {sequential_duration:.2f} seconds ({sequential_sessions/sequential_duration:.2f} sessions/s)")
    print(f"Concurrent: {concurrent_sessions} sessions in {concurrent_duration:.2f} seconds ({concurrent_sessions/concurrent_duration:.2f} sessions/s)")
    print(f"Speedup: {sequential_duration/concurrent_duration:.2f}x")
    
    return {
        "sequential": {
            "duration": sequential_duration,
            "sessions": sequential_sessions,
            "sessions_per_second": sequential_sessions/sequential_duration
        },
        "concurrent": {
            "duration": concurrent_duration,
            "sessions": concurrent_sessions,
            "sessions_per_second": concurrent_sessions/concurrent_duration
        },
        "speedup": sequential_duration/concurrent_duration
    }


def test_batch_processing():
    """测试不同批处理大小的性能"""
    print("\nTesting different batch sizes...")
    
    # 创建配置加载器和验证器
    validator = SchemaValidator()
    config_loader = YamlConfigLoader(validator)
    
    # 创建RNG提供器
    rng_provider = RNGProvider()
    
    # 事件调度器
    event_dispatcher = EventDispatcher()
    
    # 创建基础测试配置
    base_config = _create_test_config()
    base_config["use_concurrency"] = True
    base_config["sessions_per_pair"] = 5
    
    # 不同的批处理大小
    batch_sizes = [10, 50, 100]
    results = {}
    
    for batch_size in batch_sizes:
        print(f"Testing batch size {batch_size}...")
        
        # 创建注册服务
        registry_service = RegistryService(config_loader, rng_provider)
        
        # 加载实体
        registry_service.load_from_config(base_config)
        
        # 更新批处理大小
        config = base_config.copy()
        config["batch_size"] = batch_size
        
        # 创建执行器
        task_executor = TaskExecutor(ExecutionMode.THREADED)
        
        # 创建协调器
        coordinator = SimulationCoordinator(
            registry_service.machine_registry,
            registry_service.player_registry,
            event_dispatcher,
            task_executor
        )
        
        # 运行模拟
        start_time = time.time()
        batch_results = coordinator.run_simulation(config)
        duration = time.time() - start_time
        
        # 保存结果
        sessions_count = len(batch_results["sessions"])
        results[batch_size] = {
            "duration": duration,
            "sessions": sessions_count,
            "sessions_per_second": sessions_count/duration
        }
        
        print(f"Batch size {batch_size}: {sessions_count} sessions in {duration:.2f} seconds ({sessions_count/duration:.2f} sessions/s)")
        
        # 重置注册表
        registry_service.reset_all()
    
    # 打印比较结果
    print("\nBatch Size Comparison:")
    print(f"{'Batch Size':<10} {'Duration (s)':<12} {'Sessions/s':<10} {'Relative':<10}")
    print("-" * 42)
    
    baseline = results[batch_sizes[0]]["sessions_per_second"]
    
    for batch_size in batch_sizes:
        relative = results[batch_size]["sessions_per_second"] / baseline
        print(f"{batch_size:<10} {results[batch_size]['duration']:>11.2f} {results[batch_size]['sessions_per_second']:>9.2f} {relative:>9.2f}x")
    
    return results


def test_memory_usage():
    """测试模拟过程中的内存使用情况"""
    # 注意：此函数需要安装psutil库
    try:
        import psutil
    except ImportError:
        print("psutil library not found. Install with: pip install psutil")
        return None
    
    print("\nTesting memory usage...")
    
    # 获取当前进程
    process = psutil.Process(os.getpid())
    
    # 创建配置加载器和验证器
    validator = SchemaValidator()
    config_loader = YamlConfigLoader(validator)
    
    # 创建RNG提供器
    rng_provider = RNGProvider()
    
    # 事件调度器
    event_dispatcher = EventDispatcher()
    
    # 创建测试配置
    config = _create_test_config()
    config["sessions_per_pair"] = 20  # 增加会话数以更明显地观察内存使用
    config["batch_size"] = 5  # 小批次以测试批处理内存使用
    
    # 创建注册服务
    registry_service = RegistryService(config_loader, rng_provider)
    
    # 加载实体
    registry_service.load_from_config(config)
    
    # 创建执行器
    task_executor = TaskExecutor(ExecutionMode.THREADED)
    
    # 创建协调器
    coordinator = SimulationCoordinator(
        registry_service.machine_registry,
        registry_service.player_registry,
        event_dispatcher,
        task_executor
    )
    
    # 记录内存使用
    memory_samples = []
    
    # 初始内存
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_samples.append(("initial", initial_memory))
    
    print(f"Initial memory usage: {initial_memory:.2f} MB")
    
    # 运行模拟
    start_time = time.time()
    
    # 注册内存监控回调
    def progress_callback(batch_num, total_batches):
        memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_samples.append((f"batch_{batch_num}", memory))
        print(f"After batch {batch_num}/{total_batches}: {memory:.2f} MB")
    
    # 修改协调器的run_simulation方法以支持进度回调
    original_process_batch = coordinator._process_batch
    
    batch_num = 0
    total_batches = 0
    
    def wrapped_process_batch(*args, **kwargs):
        nonlocal batch_num
        batch_num += 1
        result = original_process_batch(*args, **kwargs)
        progress_callback(batch_num, total_batches)
        return result
    
    # 替换方法
    coordinator._process_batch = wrapped_process_batch
    
    # 计算总批次数
    player_count = len(registry_service.player_registry.get_player_ids())
    machine_count = len(registry_service.machine_registry.get_machine_ids())
    pair_count = player_count * machine_count
    
    total_batches = (pair_count + config["batch_size"] - 1) // config["batch_size"]
    
    # 运行模拟
    results = coordinator.run_simulation(config)
    
    # 结束内存
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_samples.append(("final", final_memory))
    
    duration = time.time() - start_time
    
    print(f"\nSimulation completed in {duration:.2f} seconds")
    print(f"Final memory usage: {final_memory:.2f} MB")
    print(f"Memory increase: {final_memory - initial_memory:.2f} MB")
    
    # 恢复原始方法
    coordinator._process_batch = original_process_batch
    
    # 打印内存使用统计
    print("\nMemory Usage Summary:")
    for sample_name, memory in memory_samples:
        print(f"{sample_name}: {memory:.2f} MB")
    
    return {
        "initial_memory_mb": initial_memory,
        "final_memory_mb": final_memory,
        "memory_increase_mb": final_memory - initial_memory,
        "samples": memory_samples
    }


if __name__ == "__main__":
    # 运行基本模拟测试
    print("=" * 80)
    print("RUNNING BASIC SIMULATION TEST")
    print("=" * 80)
    test_basic_simulation()
    
    # # 测试文件选择功能
    # print("=" * 80)
    # print("RUNNING FILE SELECTION TEST")
    # print("=" * 80)
    # test_file_selection()
    
    # # 运行并行与顺序比较测试
    # print("=" * 80)
    # print("RUNNING CONCURRENT VS SEQUENTIAL TEST")
    # print("=" * 80)
    # test_concurrent_vs_sequential()

