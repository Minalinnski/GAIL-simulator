# src/application/simulation/coordinator.py
import logging
import time
import gc
import threading
from typing import Dict, List, Any, Optional, Tuple
import copy
from collections import defaultdict, deque

from src.domain.events.event_dispatcher import EventDispatcher
from src.domain.session.factories.session_factory import SessionFactory
from src.application.registry.machine_registry import MachineRegistry
from src.application.registry.player_registry import PlayerRegistry
from src.application.simulation.session_runner import SessionRunner

from src.application.analysis.session_analyzer import SessionAnalyzer
from src.application.analysis.preference_analyzer import PreferenceAnalyzer
from src.application.analysis.report_generator import ReportGenerator
from src.infrastructure.output.output_manager import OutputManager


class SimulationCoordinator:
    """
    内存优化的模拟协调器：
    1. 实例复用和及时回收
    2. 批量写入优化
    3. 防止内存爆炸
    """
    def __init__(self, machine_registry: MachineRegistry, 
                player_registry: PlayerRegistry,
                event_dispatcher: Optional[EventDispatcher] = None,
                task_executor=None,
                output_config: Dict[str, Any] = None):
        """
        Initialize the simulation coordinator.
        """
        self.logger = logging.getLogger("application.simulation.coordinator")
        self.machine_registry = machine_registry
        self.player_registry = player_registry
        self.event_dispatcher = event_dispatcher
        self.task_executor = task_executor
        
        # Create session factory
        self.session_factory = SessionFactory(event_dispatcher)

        # Initialize output manager
        self.output_manager = OutputManager(output_config)

        self.session_analyzer = SessionAnalyzer()
        self.preference_analyzer = PreferenceAnalyzer()
        
        # Results storage - 只保存必要的汇总信息
        self.results = {}
        
        # 内存优化相关
        self.session_summaries_buffer = defaultdict(list)  # {pair_key: [summary, ...]}
        self.buffer_locks = defaultdict(threading.Lock)    # {pair_key: Lock}
        self.batch_write_size = 50  # 每50个session统计汇总后批量写入
        self.max_buffer_size = 200  # 缓冲区最大大小，防止内存爆炸
        
        # 实例池管理 - 复用实例而不是重新创建
        self.shared_instances = {}  # {(player_id, machine_id): (player, machine)}
        self.instance_locks = {}    # {(player_id, machine_id): Lock}
        
    def run_simulation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        内存优化的模拟运行
        """
        self.logger.info("Starting memory-optimized simulation")
        
        # 初始化输出管理器
        output_config = config.get("output", {})
        if output_config:
            self.output_manager = OutputManager(output_config)
            
        # 初始化输出目录结构
        sim_dir = self.output_manager.initialize()
        self.logger.info(f"Simulation output directory: {sim_dir}")
        
        # 保存配置副本用于复现
        self.output_manager.copy_config(config)
        
        # 重置结果 - 只保存必要信息
        self.results = {
            "start_time": time.time(),
            "end_time": None,
            "player_machine_pairs": [],
            "total_sessions_completed": 0,
            "simulation_dir": sim_dir,
            "sessions": []  # 这里只保存最终汇总，不保存详细数据
        }
        
        # Reset player balances if specified
        if "initial_balance" in config:
            self.player_registry.reset_all_players(config.get("initial_balance"))
        
        # Get simulation parameters
        sessions_per_pair = config.get("sessions_per_pair", 1)
        use_concurrency = config.get("use_concurrency", True)
        max_concurrent_sessions = config.get("max_concurrent_sessions", None)
        
        # 内存优化参数
        self.batch_write_size = config.get("batch_write_size", 50)
        self.max_buffer_size = config.get("max_buffer_size", 200)
        
        # 调整TaskExecutor的worker数量
        if max_concurrent_sessions and self.task_executor:
            from src.infrastructure.concurrency.task_executor import ExecutionMode
            current_mode = ExecutionMode.THREADED if use_concurrency else ExecutionMode.SEQUENTIAL
            self.task_executor.change_mode(current_mode, max_concurrent_sessions)
        
        # Generate player-machine pairs
        pairs = self._generate_pairs(config)
        self.results["player_machine_pairs"] = pairs

        total_sessions = len(pairs) * sessions_per_pair
        self.logger.info(f"Running simulation with {len(pairs)} pairs and {sessions_per_pair} sessions per pair")
        self.logger.info(f"Total sessions: {total_sessions}")
        self.logger.info(f"Memory optimization: batch_write_size={self.batch_write_size}, max_buffer_size={self.max_buffer_size}")
        
        # 预创建共享实例（每个pair一个实例，通过reset复用）
        self._prepare_shared_instances(pairs)
        
        # 执行sessions - 使用内存优化策略
        self._execute_sessions_memory_optimized(pairs, sessions_per_pair, use_concurrency, config)
        
        # 强制刷新所有剩余的缓冲区
        self._flush_all_buffers()
        
        # 设置结束时间
        self.results["end_time"] = time.time()
        self.results["duration"] = self.results["end_time"] - self.results["start_time"]
        
        # 计算性能指标
        sessions_per_second = self.results["total_sessions_completed"] / self.results["duration"] if self.results["duration"] > 0 else 0
        self.logger.info(f"Simulation completed in {self.results['duration']:.2f} seconds")
        self.logger.info(f"Performance: {sessions_per_second:.2f} sessions/second")
        self.logger.info(f"Total sessions completed: {self.results['total_sessions_completed']}")

        # 生成最终报告
        self._generate_final_reports()
        
        # 清理内存
        self._cleanup_memory()

        return self.results
    
    def _prepare_shared_instances(self, pairs: List[Tuple[str, str]]):
        """
        为每个pair创建一个共享实例（通过reset复用，而不是重新创建）
        """
        self.logger.info("Preparing shared instances for reuse")
        
        for player_id, machine_id in pairs:
            pair_key = (player_id, machine_id)
            
            # 创建锁
            self.instance_locks[pair_key] = threading.Lock()
            
            # 获取原始实例并创建一个副本
            original_player = self.player_registry.get_player(player_id)
            original_machine = self.machine_registry.get_machine(machine_id)
            
            if not original_player or not original_machine:
                self.logger.warning(f"Invalid pair: player={player_id}, machine={machine_id}")
                continue
            
            # 创建共享实例（每个pair只创建一次）
            shared_player = copy.deepcopy(original_player)
            shared_machine = copy.deepcopy(original_machine)
            
            self.shared_instances[pair_key] = (shared_player, shared_machine)
        
        self.logger.info(f"Created {len(self.shared_instances)} shared instances")
    
    def _execute_sessions_memory_optimized(self, pairs: List[Tuple[str, str]], 
                                         sessions_per_pair: int, use_concurrency: bool,
                                         config: Dict[str, Any]) -> None:
        """
        内存优化的session执行策略
        """
        session_config = {
            "max_spins": config.get("max_spins", 10000),
            "max_sim_duration": config.get("max_sim_duration", 300),
            "max_player_duration": config.get("max_player_duration", 7200),
            "output_manager": self.output_manager
        }
        
        # 创建任务工厂（延迟创建，避免提前占用内存）
        task_factories = []
        for player_id, machine_id in pairs:
            for session_num in range(sessions_per_pair):
                session_id = f"{player_id}_{machine_id}_{session_num}"
                
                # 创建任务工厂
                def create_task(pid=player_id, mid=machine_id, sid=session_id):
                    def task():
                        return self._run_memory_optimized_session(pid, mid, sid, session_config)
                    return task
                
                task_factories.append(create_task())
        
        # 使用TaskExecutor执行
        if use_concurrency and self.task_executor:
            self.logger.info(f"Running {len(task_factories)} sessions with memory optimization")
            
            # 进度回调
            def progress_callback(completed, total):
                if completed % 1000 == 0 or completed == total:
                    elapsed = time.time() - self.results["start_time"]
                    rate = completed / elapsed if elapsed > 0 else 0
                    
                    # 内存使用监控
                    import psutil
                    import os
                    process = psutil.Process(os.getpid())
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    
                    self.logger.info(f"Progress: {completed}/{total} ({completed/total*100:.1f}%) - "
                                   f"{rate:.1f} sessions/sec - Memory: {memory_mb:.0f}MB")
            
            if hasattr(self.task_executor, 'execute_with_progress'):
                self.task_executor.execute_with_progress(task_factories, progress_callback)
            else:
                self.task_executor.execute(task_factories)
        else:
            # 顺序执行
            for i, task in enumerate(task_factories):
                task()
                
                if (i + 1) % 1000 == 0 or (i + 1) == len(task_factories):
                    elapsed = time.time() - self.results["start_time"]
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Progress: {i+1}/{len(task_factories)} - {rate:.1f} sessions/sec")
    
    def _run_memory_optimized_session(self, player_id: str, machine_id: str, 
                                    session_id: str, session_config: Dict[str, Any]) -> None:
        """
        内存优化的单session执行：
        1. 复用实例（通过reset）
        2. 立即写入raw data
        3. 只保留汇总统计
        4. 及时清理内存
        """
        pair_key = (player_id, machine_id)
        
        # 获取共享实例（线程安全）
        with self.instance_locks[pair_key]:
            shared_player, shared_machine = self.shared_instances[pair_key]
            
            # 重置实例状态（而不是重新创建）
            shared_player.reset()
            shared_machine.reset_state()
        
        try:
            # 创建session
            session = self.session_factory.create_session(
                shared_player, 
                shared_machine, 
                session_id,
                output_manager=self.output_manager
            )
            
            # 创建runner并运行
            runner = SessionRunner(
                session, 
                self.event_dispatcher, 
                config=session_config
            )
            
            # 运行session
            session_result = runner.run()
            
            # 提取关键统计信息（不保存详细数据）
            session_summary = self._extract_session_summary(session_result)
            
            # 将汇总添加到缓冲区（批量写入优化）
            self._add_to_summary_buffer(pair_key, session_summary)
            
            # 更新全局计数
            self.results["total_sessions_completed"] += 1
            
            # 强制垃圾回收session对象
            del session
            del runner
            del session_result
            
        except Exception as e:
            self.logger.error(f"Session {session_id} failed: {str(e)}")
            # 记录错误但继续执行
            error_summary = {
                "session_id": session_id,
                "player_id": player_id,
                "machine_id": machine_id,
                "error": str(e),
                "total_spins": 0,
                "total_bet": 0.0,
                "total_win": 0.0,
                "duration": 0.0
            }
            self._add_to_summary_buffer(pair_key, error_summary)
    
    def _extract_session_summary(self, session_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        从完整的session结果中提取关键统计信息（丢弃详细数据）
        """
        return {
            "session_id": session_result.get("session_id"),
            "player_id": session_result.get("player_id"),
            "machine_id": session_result.get("machine_id"),
            "duration": session_result.get("duration", 0.0),
            "total_spins": session_result.get("total_spins", 0),
            "total_bet": session_result.get("total_bet", 0.0),
            "total_win": session_result.get("total_win", 0.0),
            "total_profit": session_result.get("total_profit", 0.0),
            "return_to_player": session_result.get("return_to_player", 0.0),
            "win_count": session_result.get("win_count", 0),
            "win_rate": session_result.get("win_rate", 0.0),
            "balance_change": session_result.get("balance_change", 0.0),
            "free_spins_count": session_result.get("free_spins_count", 0),
            "big_win_count": session_result.get("big_win_count", 0),
            "bonus_triggered": session_result.get("bonus_triggered", False),
        }
    
    def _add_to_summary_buffer(self, pair_key: Tuple[str, str], session_summary: Dict[str, Any]):
        """
        将session汇总添加到缓冲区，批量写入优化
        """
        with self.buffer_locks[pair_key]:
            self.session_summaries_buffer[pair_key].append(session_summary)
            
            # 检查是否需要批量写入
            if len(self.session_summaries_buffer[pair_key]) >= self.batch_write_size:
                self._flush_buffer(pair_key)
            
            # 防止内存爆炸 - 强制刷新过大的缓冲区
            elif len(self.session_summaries_buffer[pair_key]) >= self.max_buffer_size:
                self.logger.warning(f"Buffer for {pair_key} reached max size, forcing flush")
                self._flush_buffer(pair_key)
    
    def _flush_buffer(self, pair_key: Tuple[str, str]):
        """
        将指定pair的缓冲区数据批量写入文件
        """
        if not self.session_summaries_buffer[pair_key]:
            return
        
        player_id, machine_id = pair_key
        summaries = self.session_summaries_buffer[pair_key].copy()
        
        # 清空缓冲区
        self.session_summaries_buffer[pair_key].clear()
        
        # 批量写入
        for summary in summaries:
            self.output_manager.append_player_machine_session_summary(
                player_id, machine_id, summary
            )
        
        # 强制垃圾回收
        del summaries
        gc.collect()
    
    def _flush_all_buffers(self):
        """
        刷新所有剩余的缓冲区
        """
        self.logger.info("Flushing all remaining buffers")
        
        for pair_key in list(self.session_summaries_buffer.keys()):
            with self.buffer_locks[pair_key]:
                self._flush_buffer(pair_key)
        
        # 清理缓冲区字典
        self.session_summaries_buffer.clear()
        self.buffer_locks.clear()
    
    def _cleanup_memory(self):
        """
        清理内存，释放大对象
        """
        self.logger.info("Cleaning up memory")
        
        # 清理共享实例
        self.shared_instances.clear()
        self.instance_locks.clear()
        
        # 清理缓冲区
        self.session_summaries_buffer.clear()
        self.buffer_locks.clear()
        
        # 强制垃圾回收
        gc.collect()
        
        # 记录内存使用
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.logger.info(f"Memory usage after cleanup: {memory_mb:.0f}MB")
        except ImportError:
            pass
    
    def _generate_final_reports(self):
        """
        生成最终报告（基于已写入的文件，而不是内存中的数据）
        """
        if not self.output_manager.config["reports"]["generate_reports"]:
            return
            
        self.logger.info("Generating final reports")
        
        reports_dir = self.output_manager.get_reports_directory()
        report_generator = ReportGenerator(reports_dir)
        
        # 创建简化的结果集（只包含必要信息）
        simplified_results = {
            "start_time": self.results["start_time"],
            "end_time": self.results["end_time"], 
            "duration": self.results["duration"],
            "total_sessions_completed": self.results["total_sessions_completed"],
            "player_machine_pairs": self.results["player_machine_pairs"],
            "simulation_dir": self.results["simulation_dir"],
            "sessions": []  # 空列表，实际数据已写入文件
        }
        
        if self.output_manager.config["reports"]["include"].get("summary_report", True):
            summary_path = report_generator.generate_summary_report(
                simplified_results, {}
            )
            self.logger.info(f"Generated summary report: {summary_path}")
    
    # 保留其他必要方法...
    def _generate_pairs(self, config: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Generate player-machine pairs for simulation."""
        player_ids = self.player_registry.get_player_ids()
        machine_ids = self.machine_registry.get_machine_ids()
        
        if "pairings" in config:
            pairs = []
            for pair in config["pairings"]:
                player_id = pair.get("player_id")
                machine_id = pair.get("machine_id")
                
                if player_id in player_ids and machine_id in machine_ids:
                    pairs.append((player_id, machine_id))
                else:
                    self.logger.warning(f"Invalid pairing: player={player_id}, machine={machine_id}")
                    
            return pairs
            
        # Otherwise, generate all combinations
        pairs = []
        for player_id in player_ids:
            for machine_id in machine_ids:
                pairs.append((player_id, machine_id))
                
        self.logger.info(f"Generated {len(pairs)} player-machine pairs")
        return pairs
        
    def get_results(self) -> Dict[str, Any]:
        """Get the simulation results."""
        return self.results