# src/application/simulation/coordinator.py
# 最小修改版本 - 基于你现有的coordinator添加任务分发优化

import logging
import time
import threading
import queue
from typing import Dict, List, Any, Optional, Tuple
import copy
from collections import defaultdict, deque
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor

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
    任务分发优化的模拟协调器：
    1. 每个CPU核心准备一组pair实例
    2. 智能任务分发减少阻塞
    3. 最小化代码修改
    """
    def __init__(self, machine_registry: MachineRegistry, 
                player_registry: PlayerRegistry,
                event_dispatcher: Optional[EventDispatcher] = None,
                task_executor=None,
                output_config: Dict[str, Any] = None):
        """Initialize the simulation coordinator."""
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
        
        # Results storage
        self.results = {}
        
        # 新增：任务分发优化相关（简化版本）
        self.worker_instance_pools = {}  # {worker_id: {pair_key: (player, machine)}}
        self.num_workers = None
        
        # 内存优化 - 批量写入缓冲
        self.session_summaries_buffer = defaultdict(list)
        self.buffer_locks = defaultdict(threading.Lock)
        self.batch_write_size = 50
        
    def run_simulation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行模拟 - 增加任务分发优化
        """
        self.logger.info("Starting simulation with optimized task distribution")
        
        # 初始化输出管理器（保持原有逻辑）
        output_config = config.get("output", {})
        if output_config:
            self.output_manager = OutputManager(output_config)
            
        sim_dir = self.output_manager.initialize()
        self.logger.info(f"Simulation output directory: {sim_dir}")
        self.output_manager.copy_config(config)
        
        # 重置结果（保持原有结构）
        self.results = {
            "start_time": time.time(),
            "end_time": None,
            "player_machine_pairs": [],
            "sessions": [],
            "simulation_dir": sim_dir
        }
        
        # Reset player balances if specified（保持原有逻辑）
        if "initial_balance" in config:
            self.player_registry.reset_all_players(config.get("initial_balance"))
        
        # Get simulation parameters
        sessions_per_pair = config.get("sessions_per_pair", 1)
        use_concurrency = config.get("use_concurrency", True)
        max_concurrent_sessions = config.get("max_concurrent_sessions", None)
        
        # 新增：任务分发参数（简化，只保留必要的）
        self.batch_write_size = config.get("batch_write_size", 50)
        
        # 调整TaskExecutor的worker数量
        if max_concurrent_sessions and self.task_executor:
            from src.infrastructure.concurrency.task_executor import ExecutionMode
            current_mode = ExecutionMode.MULTITHREAD if use_concurrency else ExecutionMode.SEQUENTIAL
            self.task_executor.change_mode(current_mode, max_concurrent_sessions)
            self.num_workers = max_concurrent_sessions
        else:
            self.num_workers = self.task_executor.max_workers if self.task_executor else 8
        
        # Generate player-machine pairs
        pairs = self._generate_pairs(config)
        self.results["player_machine_pairs"] = pairs

        total_sessions = len(pairs) * sessions_per_pair
        self.logger.info(f"Running simulation: {len(pairs)} pairs × {sessions_per_pair} sessions = {total_sessions} total")
        self.logger.info(f"Task distribution: {self.num_workers} workers, pair grouping strategy")
        
        # 新增：为每个worker准备实例池
        if use_concurrency:
            self._prepare_worker_instance_pools(pairs)
            session_results = self._execute_sessions_with_task_distribution(
                pairs, sessions_per_pair, config
            )
        else:
            # 顺序执行时使用原有逻辑
            session_results = self._execute_sessions_sequential(pairs, sessions_per_pair, config)
        
        self.results["sessions"] = session_results
    
        # 设置结束时间（保持原有逻辑）
        self.results["end_time"] = time.time()
        self.results["duration"] = self.results["end_time"] - self.results["start_time"]
        
        sessions_per_second = len(session_results) / self.results["duration"] if self.results["duration"] > 0 else 0
        self.logger.info(f"Simulation completed in {self.results['duration']:.2f} seconds")
        self.logger.info(f"Performance: {sessions_per_second:.2f} sessions/second")

        # 分析模拟结果（保持原有逻辑）
        self._analyze_results()
        self._generate_reports()
        self._generate_player_machine_summaries()
        
        # 新增：合并临时summary文件
        self._merge_temp_summary_files()

        return self.results
    
    def _merge_temp_summary_files(self):
        """
        合并所有临时summary文件到对应的cluster/table目录
        """
        if not self.output_manager:
            return
            
        self.logger.info("Merging temporary summary files")
        
        # 获取所有unique的pair组合
        unique_pairs = set()
        for session in self.results["sessions"]:
            session_id = session.get("session_id", "")
            if session_id:
                # 使用统一的解析逻辑
                player_id, machine_id = self._parse_session_id_for_pair(session_id)
                unique_pairs.add((player_id, machine_id))
        
        # 为每个pair合并summary文件
        for player_id, machine_id in unique_pairs:
            try:
                merged_file = self.output_manager.merge_temp_summaries_to_csv(player_id, machine_id)
                if merged_file:
                    self.logger.debug(f"Merged summaries for {player_id}_{machine_id}: {merged_file}")
                else:
                    self.logger.warning(f"No summary files to merge for {player_id}_{machine_id}")
            except Exception as e:
                self.logger.error(f"Error merging summaries for {player_id}_{machine_id}: {str(e)}")
        
        self.logger.info("Temporary summary file merging completed")
    
    def _parse_session_id_for_pair(self, session_id: str) -> Tuple[str, str]:
        """
        从session_id解析player_id和machine_id
        与output_manager保持一致的解析逻辑
        
        Args:
            session_id: 格式为 "player_id_machine_id_session_num"
            
        Returns:
            (player_id, machine_id)
        """
        parts = session_id.split('_')
        if len(parts) < 3:
            return "unknown_player", "unknown_machine"
        
        # 最后一个部分是session_num，倒数第二个是machine_id（单个单词）
        machine_id = parts[-2]
        # 其余部分组成player_id
        player_id = '_'.join(parts[:-2])
        
        return player_id, machine_id
    
    def _prepare_worker_instance_pools(self, pairs: List[Tuple[str, str]]):
        """
        为每个worker准备一组完整的pair实例
        每个worker都有所有pair的副本，避免竞争
        """
        self.logger.info(f"Preparing instance pools for {self.num_workers} workers")
        
        for worker_id in range(self.num_workers):
            self.worker_instance_pools[worker_id] = {}
            
            for player_id, machine_id in pairs:
                pair_key = (player_id, machine_id)
                
                # 为每个worker创建独立的pair实例
                original_player = self.player_registry.get_player(player_id)
                original_machine = self.machine_registry.get_machine(machine_id)
                
                if not original_player or not original_machine:
                    self.logger.warning(f"Invalid pair: player={player_id}, machine={machine_id}")
                    continue
                
                # 每个worker都有自己的实例副本
                worker_player = copy.deepcopy(original_player)
                worker_machine = copy.deepcopy(original_machine)
                
                self.worker_instance_pools[worker_id][pair_key] = (worker_player, worker_machine)
        
        total_instances = sum(len(pool) for pool in self.worker_instance_pools.values())
        self.logger.info(f"Created {total_instances} instances across {self.num_workers} workers")
    
    def _execute_sessions_with_task_distribution(self, pairs: List[Tuple[str, str]], 
                                               sessions_per_pair: int, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        使用优化任务分发的session执行
        """
        session_config = {
            "max_spins": config.get("max_spins", 10000),
            "max_sim_duration": config.get("max_sim_duration", 300),
            "max_player_duration": config.get("max_player_duration", 7200),
            "output_manager": self.output_manager
        }
        
        # 创建任务列表
        all_tasks = []
        for player_id, machine_id in pairs:
            for session_num in range(sessions_per_pair):
                task_info = {
                    "player_id": player_id,
                    "machine_id": machine_id,
                    "session_id": f"{player_id}_{machine_id}_{session_num}",
                    "session_num": session_num
                }
                all_tasks.append(task_info)
        
        # 智能任务分发
        distributed_tasks = self._distribute_tasks_optimally(all_tasks)
        
        # 创建任务函数
        task_functions = []
        for worker_id, task_info in distributed_tasks:
            def create_task(wid=worker_id, tinfo=task_info):
                def task():
                    return self._run_session_with_worker_instance(wid, tinfo, session_config)
                return task
            task_functions.append(create_task())
        
        # 使用TaskExecutor执行
        self.logger.info(f"Running {len(task_functions)} sessions with optimized distribution")
        
        if hasattr(self.task_executor, 'execute_with_progress'):
            def progress_callback(completed, total):
                if completed % 1000 == 0 or completed == total:
                    elapsed = time.time() - self.results["start_time"]
                    rate = completed / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Progress: {completed}/{total} ({completed/total*100:.1f}%) - {rate:.1f} sessions/sec")
            
            results = self.task_executor.execute_with_progress(task_functions, progress_callback)
        else:
            results = self.task_executor.execute(task_functions)
        
        # 刷新所有剩余的缓冲区
        self._flush_all_buffers()
        
        return results
    
    def _distribute_tasks_optimally(self, all_tasks: List[Dict[str, Any]]) -> List[Tuple[int, Dict[str, Any]]]:
        """
        优化的任务分发策略 - 专注于pair grouping
        同一个pair的大量sessions智能分配到多个worker上
        """
        distributed = []
        
        # 按pair分组任务
        pair_tasks = defaultdict(list)
        for task_info in all_tasks:
            pair_key = (task_info["player_id"], task_info["machine_id"])
            pair_tasks[pair_key].append(task_info)
        
        # 为每个pair计算需要的worker数量
        worker_assignments = []  # [(worker_id, pair_key, start_idx, end_idx), ...]
        
        for pair_key, tasks in pair_tasks.items():
            num_tasks = len(tasks)
            
            if num_tasks <= self.num_workers:
                # 任务数少于worker数，每个worker分配1个任务
                for i, task_info in enumerate(tasks):
                    worker_id = i % self.num_workers
                    distributed.append((worker_id, task_info))
            else:
                # 任务数多于worker数，将任务分块分配给不同worker
                tasks_per_worker = num_tasks // self.num_workers
                remainder = num_tasks % self.num_workers
                
                start_idx = 0
                for worker_id in range(self.num_workers):
                    # 前remainder个worker多分配1个任务
                    end_idx = start_idx + tasks_per_worker + (1 if worker_id < remainder else 0)
                    
                    # 将这个范围的任务分配给当前worker
                    for task_info in tasks[start_idx:end_idx]:
                        distributed.append((worker_id, task_info))
                    
                    start_idx = end_idx
        
        # 统计分发结果
        worker_counts = defaultdict(int)
        pair_worker_distribution = defaultdict(lambda: defaultdict(int))
        
        for worker_id, task_info in distributed:
            worker_counts[worker_id] += 1
            pair_key = (task_info["player_id"], task_info["machine_id"])
            pair_worker_distribution[pair_key][worker_id] += 1
        
        self.logger.info(f"Task distribution summary: {dict(worker_counts)}")
        
        # 显示每个pair在各worker上的分布
        for pair_key, worker_dist in pair_worker_distribution.items():
            self.logger.debug(f"Pair {pair_key}: {dict(worker_dist)}")
        
        return distributed
    
    def _run_session_with_worker_instance(self, worker_id: int, task_info: Dict[str, Any], 
                                        session_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用指定worker的实例运行session
        """
        player_id = task_info["player_id"]
        machine_id = task_info["machine_id"]
        session_id = task_info["session_id"]
        pair_key = (player_id, machine_id)
        
        # 获取worker的实例（无需锁，每个worker有自己的实例）
        if worker_id not in self.worker_instance_pools or pair_key not in self.worker_instance_pools[worker_id]:
            raise ValueError(f"No instance available for worker {worker_id}, pair {pair_key}")
        
        worker_player, worker_machine = self.worker_instance_pools[worker_id][pair_key]
        
        try:
            # 重置实例状态（每个worker的实例是独立的）
            worker_player.reset()
            worker_machine.reset_state()
            
            # 创建session（每次都是独立的session对象）
            session = self.session_factory.create_session(
                worker_player, 
                worker_machine, 
                session_id,
                output_manager=self.output_manager
            )
            
            # 创建runner并运行
            runner = SessionRunner(
                session, 
                self.event_dispatcher, 
                config=session_config
            )
            
            result = runner.run()
            
            # 批量写入优化（可选）
            if self.batch_write_size > 1:
                self._add_session_to_buffer(pair_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Session {session_id} on worker {worker_id} failed: {str(e)}")
            return {
                "session_id": session_id,
                "player_id": player_id,
                "machine_id": machine_id,
                "error": str(e),
                "total_spins": 0,
                "total_bet": 0.0,
                "total_win": 0.0,
                "duration": 0.0
            }
    
    def _execute_sessions_sequential(self, pairs: List[Tuple[str, str]], 
                                   sessions_per_pair: int, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        顺序执行sessions（保持原有逻辑）
        """
        results = []
        session_config = {
            "max_spins": config.get("max_spins", 10000),
            "max_sim_duration": config.get("max_sim_duration", 300),
            "max_player_duration": config.get("max_player_duration", 7200),
            "output_manager": self.output_manager
        }
        
        for player_id, machine_id in pairs:
            _player = self.player_registry.get_player(player_id)
            _machine = self.machine_registry.get_machine(machine_id)
            
            if not _player or not _machine:
                self.logger.warning(f"Invalid pair: player={player_id}, machine={machine_id}")
                continue
            
            for session_num in range(sessions_per_pair):
                session_id = f"{player_id}_{machine_id}_{session_num}"
                
                # 为每个会话创建独立副本（保持原有逻辑）
                player_copy = self._clone_player(_player)
                machine_copy = self._clone_machine(_machine)
                
                session = self.session_factory.create_session(
                    player_copy, 
                    machine_copy, 
                    session_id,
                    output_manager=self.output_manager
                )
                runner = SessionRunner(
                    session, 
                    self.event_dispatcher, 
                    config=session_config
                )
                
                result = runner.run()
                results.append(result)
        
        return results
    
    def _add_session_to_buffer(self, pair_key: Tuple[str, str], session_result: Dict[str, Any]):
        """批量写入缓冲（可选优化）"""
        with self.buffer_locks[pair_key]:
            self.session_summaries_buffer[pair_key].append(session_result)
            
            if len(self.session_summaries_buffer[pair_key]) >= self.batch_write_size:
                self._flush_buffer(pair_key)
    
    def _flush_buffer(self, pair_key: Tuple[str, str]):
        """刷新缓冲区（批量写入优化）"""
        if not self.session_summaries_buffer[pair_key]:
            return
        
        # 这里可以添加批量写入逻辑
        # 目前简化处理
        self.session_summaries_buffer[pair_key].clear()
    
    def _flush_all_buffers(self):
        """刷新所有缓冲区"""
        for pair_key in list(self.session_summaries_buffer.keys()):
            with self.buffer_locks[pair_key]:
                self._flush_buffer(pair_key)
    
    # 保持所有原有方法不变
    def _clone_player(self, player):
        player_copy = copy.deepcopy(player)
        player_copy.reset()
        return player_copy

    def _clone_machine(self, machine):
        machine_copy = copy.deepcopy(machine)
        machine_copy.reset_state()
        return machine_copy
    
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
            
        pairs = []
        for player_id in player_ids:
            for machine_id in machine_ids:
                pairs.append((player_id, machine_id))
                
        self.logger.info(f"Generated {len(pairs)} player-machine pairs")
        return pairs
    
    # 保持所有其他原有方法...
    def _analyze_results(self):
        """分析模拟结果并保存到结果字典中。"""
        self.logger.info("Analyzing simulation results")
        session_analysis = self.session_analyzer.analyze_sessions(self.results["sessions"])
        self.results["session_analysis"] = session_analysis
        
        preference_analysis = self.preference_analyzer.analyze_preferences(self.results)
        self.results["preference_analysis"] = preference_analysis
        
        self.logger.info("Analysis completed")

    def _generate_reports(self):
        """生成模拟报告。"""
        if not self.output_manager.config["reports"]["generate_reports"]:
            return
            
        self.logger.info("Generating reports")
        
        reports_dir = self.output_manager.get_reports_directory()
        report_generator = ReportGenerator(reports_dir)
        
        if self.output_manager.config["reports"]["include"].get("summary_report", True):
            summary_path = report_generator.generate_summary_report(
                self.results, 
                self.results.get("preference_analysis", {})
            )
            self.logger.info(f"Generated summary report: {summary_path}")
        
        if self.output_manager.config["reports"]["include"].get("detailed_session_report", False):
            detailed_path = report_generator.generate_detailed_report(
                self.results, 
                self.results.get("preference_analysis", {})
            )
            self.logger.info(f"Generated detailed report: {detailed_path}")

    def _generate_player_machine_summaries(self):
        """为每个玩家-机器对生成汇总统计。"""
        if not self.output_manager:
            return
            
        self.logger.info("Generating player-machine summaries")
        
        player_machine_sessions = {}
        
        for session in self.results["sessions"]:
            player_id = session.get("player_id", "unknown")
            machine_id = session.get("machine_id", "unknown")
            key = f"{player_id}_{machine_id}"
            
            if key not in player_machine_sessions:
                player_machine_sessions[key] = []
            player_machine_sessions[key].append(session)
        
        for key, sessions in player_machine_sessions.items():
            if not sessions:
                continue
                
            parts = key.split('_', 1)
            if len(parts) == 2:
                player_id, machine_id = parts
            else:
                continue
            
            summary = self._calculate_player_machine_summary(player_id, machine_id, sessions)
            self.output_manager.append_player_machine_session_summary(
                player_id, machine_id, summary
            )
        
        self.logger.info(f"Generated summaries for {len(player_machine_sessions)} player-machine pairs")

    def _calculate_player_machine_summary(self, player_id: str, machine_id: str, 
                                        sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算玩家-机器对的汇总统计。"""
        if not sessions:
            return {}
        
        total_sessions = len(sessions)
        total_spins = sum(s.get("total_spins", 0) for s in sessions)
        total_bet = sum(s.get("total_bet", 0.0) for s in sessions)
        total_win = sum(s.get("total_win", 0.0) for s in sessions)
        total_duration = sum(s.get("duration", 0.0) for s in sessions)
        
        avg_session_duration = total_duration / total_sessions
        avg_spins_per_session = total_spins / total_sessions
        avg_bet_per_spin = total_bet / total_spins if total_spins > 0 else 0.0
        
        overall_rtp = total_win / total_bet if total_bet > 0 else 0.0
        
        total_wins = sum(s.get("win_count", 0) for s in sessions)
        overall_win_rate = total_wins / total_spins if total_spins > 0 else 0.0
        
        total_free_spins = sum(s.get("free_spins_count", 0) for s in sessions)
        total_big_wins = sum(s.get("big_win_count", 0) for s in sessions)
        
        balance_changes = [s.get("balance_change", 0.0) for s in sessions if "balance_change" in s]
        avg_balance_change = sum(balance_changes) / len(balance_changes) if balance_changes else 0.0
        
        return {
            "player_id": player_id,
            "machine_id": machine_id,
            "summary_generated_at": time.time(),
            "session_count": total_sessions,
            "total_spins": total_spins,
            "total_bet": total_bet,
            "total_win": total_win,
            "total_profit": total_win - total_bet,
            "overall_rtp": overall_rtp,
            "overall_win_rate": overall_win_rate,
            "total_duration": total_duration,
            "avg_session_duration": avg_session_duration,
            "avg_spins_per_session": avg_spins_per_session,
            "avg_bet_per_spin": avg_bet_per_spin,
            "avg_balance_change": avg_balance_change,
            "total_free_spins_awarded": total_free_spins,
            "total_big_wins": total_big_wins,
            "free_spins_frequency": total_free_spins / total_spins if total_spins > 0 else 0.0,
            "big_win_frequency": total_big_wins / total_spins if total_spins > 0 else 0.0,
            "sessions": [
                {
                    "session_id": s.get("session_id"),
                    "duration": s.get("duration", 0.0),
                    "total_spins": s.get("total_spins", 0),
                    "total_bet": s.get("total_bet", 0.0),
                    "total_win": s.get("total_win", 0.0),
                    "rtp": s.get("return_to_player", 0.0),
                    "balance_change": s.get("balance_change", 0.0)
                } for s in sessions
            ]
        }
        
    def get_results(self) -> Dict[str, Any]:
        """Get the simulation results."""
        return self.results