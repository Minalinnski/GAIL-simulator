# src/application/simulation/coordinator.py
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
import copy

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
    Coordinates the simulation process, matching players with machines
    and orchestrating session execution.
    """
    def __init__(self, machine_registry: MachineRegistry, 
                player_registry: PlayerRegistry,
                event_dispatcher: Optional[EventDispatcher] = None,
                task_executor=None,
                output_config: Dict[str, Any] = None):
        """
        Initialize the simulation coordinator.
        
        Args:
            machine_registry: Registry of slot machines
            player_registry: Registry of players
            event_dispatcher: Optional event dispatcher
            task_executor: Optional executor for concurrent tasks
        """
        self.logger = logging.getLogger("application.simulation.coordinator")
        self.machine_registry = machine_registry
        self.player_registry = player_registry
        self.event_dispatcher = event_dispatcher
        self.task_executor = task_executor
        
        # Create session factory
        self.session_factory = SessionFactory(event_dispatcher)

        # Initilize output manager
        self.output_manager = OutputManager(output_config)

        self.session_analyzer = SessionAnalyzer()
        self.preference_analyzer = PreferenceAnalyzer()
        
        # Results storage
        self.results = {}
        
    def run_simulation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a simulation based on configuration.
        
        Args:
            config: Simulation configuration
            
        Returns:
            Dictionary of simulation results
        """
        self.logger.info("Starting simulation")
        
        # 初始化输出管理器
        output_config = config.get("output", {})
        if output_config:
            self.output_manager = OutputManager(output_config)
            
        # 初始化输出目录结构
        sim_dir = self.output_manager.initialize()
        self.logger.info(f"Simulation output directory: {sim_dir}")
        
        # 保存配置副本用于复现
        self.output_manager.copy_config(config)
        
        # 重置结果
        self.results = {
            "start_time": time.time(),
            "end_time": None,
            "player_machine_pairs": [],
            "sessions": [],
            "simulation_dir": sim_dir
        }
        
        # Reset player balances if specified
        if "initial_balance" in config:
            self.player_registry.reset_all_players(config.get("initial_balance"))
        
        # Get simulation parameters
        sessions_per_pair = config.get("sessions_per_pair", 1)
        use_concurrency = config.get("use_concurrency", True)

        # Get batching parameters
        batch_size = config.get("batch_size", 100)  # Default to 100 sessions per batch
        
        # Generate player-machine pairs
        pairs = self._generate_pairs(config)
        self.results["player_machine_pairs"] = pairs

        total_pairs = len(pairs)    
        self.logger.info(f"Running simulation with {total_pairs} pairs and {sessions_per_pair} sessions per pair, batch_size = {batch_size}")
        
        pairs_processed = 0
        batch_num = 0
        
        while pairs_processed < total_pairs:
            batch_num += 1

            remaining_pairs = total_pairs - pairs_processed
            pairs_in_batch = min(batch_size, remaining_pairs)
            
            batch_pairs = pairs[pairs_processed:pairs_processed + pairs_in_batch]
            
            batch_results = self._process_batch(batch_pairs, sessions_per_pair, use_concurrency, config)
            self.results["sessions"].extend(batch_results)

            pairs_processed += pairs_in_batch
            self.logger.info(f"Completed batch {batch_num}: {pairs_in_batch} pairs processed, {len(batch_results)} sessions completed")
    
        # 设置结束时间
        self.results["end_time"] = time.time()
        self.results["duration"] = self.results["end_time"] - self.results["start_time"]
        self.logger.info(f"Simulation completed in {self.results['duration']:.2f} seconds")

        # 分析模拟结果
        self._analyze_results()
        # 生成报告
        self._generate_reports()

        self._generate_player_machine_summaries()

        return self.results
    
    
    def _process_batch(self, batch_pairs: List[Tuple[str, str]], sessions_per_pair: int, 
                 use_concurrency: bool, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        batch_tasks = []
        
        session_config = {
            "max_spins": config.get("max_spins", 10000),
            "max_sim_duration": config.get("max_sim_duration", 300),
            "max_player_duration": config.get("max_player_duration", 7200),
            "output_manager": self.output_manager  # 传递输出管理器给会话
        }

        for player_id, machine_id in batch_pairs:
            # 从注册表获取原始实例
            _player = self.player_registry.get_player(player_id)
            _machine = self.machine_registry.get_machine(machine_id)
            
            if not _player or not _machine:
                self.logger.warning(f"Invalid pair: player={player_id}, machine={machine_id}")
                continue
            
            for session_num in range(sessions_per_pair):
                # 创建唯一会话ID
                session_id = f"{player_id}_{machine_id}_{session_num}"
                
                # 为每个会话创建玩家和机器的独立副本
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
                
                batch_tasks.append(runner.run)
        
        # 执行批次任务
        batch_results = []
        if batch_tasks:
            if use_concurrency and self.task_executor:
                self.logger.info(f"Running {len(batch_tasks)} sessions concurrently")
                batch_results = self.task_executor.execute(batch_tasks)
            else:
                # 顺序运行
                self.logger.info(f"Running {len(batch_tasks)} sessions sequentially")
                for task in batch_tasks:
                    result = task()
                    batch_results.append(result)
        
        return batch_results
    
    
    def _clone_player(self, player):
        player_copy = copy.deepcopy(player)
        player_copy.reset() # TODO player.balance)
        return player_copy

    def _clone_machine(self, machine):
        machine_copy = copy.deepcopy(machine)
        machine_copy.reset_state()
        return machine_copy
    
    
    def _generate_pairs(self, config: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        Generate player-machine pairs for simulation.
        
        Args:
            config: Simulation configuration
            
        Returns:
            List of (player_id, machine_id) tuples
        """
        # Get player and machine IDs
        player_ids = self.player_registry.get_player_ids()
        machine_ids = self.machine_registry.get_machine_ids()
        
        # Check for explicit pairings
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
    
    # 添加分析方法
    def _analyze_results(self):
        """分析模拟结果并保存到结果字典中。"""
        self.logger.info("Analyzing simulation results")
        session_analysis = self.session_analyzer.analyze_sessions(self.results["sessions"])
        self.results["session_analysis"] = session_analysis
        
        preference_analysis = self.preference_analyzer.analyze_preferences(self.results)
        self.results["preference_analysis"] = preference_analysis
        
        self.logger.info("Analysis completed")

    # 添加报告生成方法
    def _generate_reports(self):
        """
        生成模拟报告。
        使用ReportGenerator生成各种报告。
        """
        if not self.output_manager.config["reports"]["generate_reports"]:
            return
            
        self.logger.info("Generating reports")
        
        reports_dir = self.output_manager.get_reports_directory()
        report_generator = ReportGenerator(reports_dir)
        
        # 生成摘要报告
        if self.output_manager.config["reports"]["include"].get("summary_report", True):
            summary_path = report_generator.generate_summary_report(
                self.results, 
                self.results.get("preference_analysis", {})
            )
            self.logger.info(f"Generated summary report: {summary_path}")
        
        # 生成玩家偏好报告
        if self.output_manager.config["reports"]["include"].get("player_preference_report", True):
            # TODO 这里可以添加专门的玩家偏好报告生成逻辑
            pass
        
        # 生成机器性能报告
        if self.output_manager.config["reports"]["include"].get("machine_performance_report", True):
            # TODO 这里可以添加专门的机器性能报告生成逻辑
            pass
        
        # 生成详细会话报告
        if self.output_manager.config["reports"]["include"].get("detailed_session_report", False):
            detailed_path = report_generator.generate_detailed_report(
                self.results, 
                self.results.get("preference_analysis", {})
            )
            self.logger.info(f"Generated detailed report: {detailed_path}")

    def _generate_player_machine_summaries(self):
        """
        为每个玩家-机器对生成汇总统计。
        利用现有的 output_manager 而不是重新初始化。
        """
        if not self.output_manager:
            return
            
        self.logger.info("Generating player-machine summaries")
        
        # 按玩家-机器对分组会话
        player_machine_sessions = {}
        
        for session in self.results["sessions"]:
            player_id = session.get("player_id", "unknown")
            machine_id = session.get("machine_id", "unknown")
            key = f"{player_id}_{machine_id}"
            
            if key not in player_machine_sessions:
                player_machine_sessions[key] = []
            player_machine_sessions[key].append(session)
        
        # 为每个玩家-机器对生成汇总
        for key, sessions in player_machine_sessions.items():
            if not sessions:
                continue
                
            parts = key.split('_', 1)
            if len(parts) == 2:
                player_id, machine_id = parts
            else:
                continue
            
            # 计算汇总统计
            summary = self._calculate_player_machine_summary(player_id, machine_id, sessions)
            
            # 写入汇总文件（使用现有的output_manager）
            self.output_manager.append_player_machine_session_summary(
                player_id, machine_id, summary
            )
        
        self.logger.info(f"Generated summaries for {len(player_machine_sessions)} player-machine pairs")

    def _calculate_player_machine_summary(self, player_id: str, machine_id: str, 
                                        sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算玩家-机器对的汇总统计。
        
        Args:
            player_id: 玩家ID
            machine_id: 机器ID
            sessions: 该玩家-机器对的所有会话
            
        Returns:
            汇总统计字典
        """
        if not sessions:
            return {}
        
        # 聚合统计
        total_sessions = len(sessions)
        total_spins = sum(s.get("total_spins", 0) for s in sessions)
        total_bet = sum(s.get("total_bet", 0.0) for s in sessions)
        total_win = sum(s.get("total_win", 0.0) for s in sessions)
        total_duration = sum(s.get("duration", 0.0) for s in sessions)
        
        # 计算平均值
        avg_session_duration = total_duration / total_sessions
        avg_spins_per_session = total_spins / total_sessions
        avg_bet_per_spin = total_bet / total_spins if total_spins > 0 else 0.0
        
        # RTP计算
        overall_rtp = total_win / total_bet if total_bet > 0 else 0.0
        
        # 胜率计算
        total_wins = sum(s.get("win_count", 0) for s in sessions)
        overall_win_rate = total_wins / total_spins if total_spins > 0 else 0.0
        
        # 免费旋转统计
        total_free_spins = sum(s.get("free_spins_count", 0) for s in sessions)
        total_big_wins = sum(s.get("big_win_count", 0) for s in sessions)
        
        # 余额变化
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
        """
        Get the simulation results.
        
        Returns:
            Dictionary of simulation results
        """
        return self.results