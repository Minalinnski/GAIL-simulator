# src/application/simulation/coordinator.py
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from src.domain.events.event_dispatcher import EventDispatcher
from src.domain.session.factories.session_factory import SessionFactory
from src.application.registry.registry_service import RegistryService
from src.application.simulation.session_runner import SessionRunner

from src.application.analysis.session_analyzer import SessionAnalyzer
from src.application.analysis.preference_analyzer import PreferenceAnalyzer
from src.application.analysis.report_generator import ReportGenerator
from src.infrastructure.output.output_manager import OutputManager


class SimulationCoordinator:
    """
    简化的模拟协调器，使用无状态实例池和直接任务创建。
    """
    def __init__(self, registry_service: RegistryService,
                event_dispatcher: Optional[EventDispatcher] = None,
                task_executor=None,
                output_config: Dict[str, Any] = None):
        """
        Initialize the simulation coordinator.
        
        Args:
            registry_service: 带实例池的注册服务
            event_dispatcher: 事件调度器
            task_executor: 任务执行器
            output_config: 输出配置
        """
        self.logger = logging.getLogger("application.simulation.coordinator")
        self.registry_service = registry_service
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
        
    def run_simulation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行简化的模拟
        """
        self.logger.info("Starting simplified simulation with stateless instances")
        
        # 初始化输出管理器
        output_config = config.get("output", {})
        if output_config:
            self.output_manager = OutputManager(output_config)
            
        sim_dir = self.output_manager.initialize()
        self.logger.info(f"Simulation output directory: {sim_dir}")
        self.output_manager.copy_config(config)
        
        # 重置结果
        self.results = {
            "start_time": time.time(),
            "end_time": None,
            "player_machine_pairs": [],
            "sessions": [],
            "simulation_dir": sim_dir
        }
        
        # Get simulation parameters
        sessions_per_pair = config.get("sessions_per_pair", 1)
        use_concurrency = config.get("use_concurrency", True)
        max_concurrent_sessions = config.get("max_concurrent_sessions", None)
        
        # 确保实例池已初始化
        if max_concurrent_sessions and max_concurrent_sessions > 0:
            if not hasattr(self.registry_service, '_player_instance_pools') or not self.registry_service._player_instance_pools:
                self.registry_service.initialize_instance_pools(max_concurrent_sessions)
        
        # 创建player-machine对
        pairs = self._create_player_machine_pairs(config)
        self.logger.info(f"Created {len(pairs)} player-machine pairs")
        
        # 执行sessions
        if use_concurrency and self.task_executor:
            session_results = self._execute_sessions_concurrent(pairs, sessions_per_pair, config)
        else:
            session_results = self._execute_sessions_sequential(pairs, sessions_per_pair, config)
        
        # 存储结果
        self.results["sessions"] = [r for r in session_results if r is not None]
        self.results["player_machine_pairs"] = pairs
        self.results["end_time"] = time.time()
        
        # ===== 合并所有临时summary文件 =====
        self.logger.info("Finalizing session summaries...")
        merged_summaries = self.output_manager.finalize_all_summaries()
        self.results["merged_summary_files"] = merged_summaries
        self.logger.info(f"Finalized summaries for {len(merged_summaries)} player-machine pairs")

        # 生成分析和报告
        self._generate_analysis_and_reports(config)
        
        # 输出实例池统计
        pool_stats = self.registry_service.get_pool_stats()
        self.logger.info(f"Instance pool stats: {pool_stats}")
        
        self.logger.info(f"Simulation completed with {len(self.results['sessions'])} sessions in {self.results['end_time'] - self.results['start_time']:.2f} seconds")
        
        return self.results
    
    def _create_player_machine_pairs(self, config: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        创建player-machine对
        """
        # 检查是否有特定的配对配置
        if "pairings" in config:
            pairs = []
            for pairing in config["pairings"]:
                player_id = pairing["player_id"]
                machine_id = pairing["machine_id"]
                pairs.append((player_id, machine_id))
            return pairs
        
        # 否则创建所有可能的组合
        player_ids = self.registry_service.player_registry.get_player_ids()
        machine_ids = self.registry_service.machine_registry.get_machine_ids()
        
        pairs = []
        for player_id in player_ids:
            for machine_id in machine_ids:
                pairs.append((player_id, machine_id))
        
        return pairs
    
    def _execute_sessions_concurrent(self, pairs: List[Tuple[str, str]], 
                                   sessions_per_pair: int, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        并发执行sessions，使用实例池
        """
        session_config = {
            "max_spins": config.get("max_spins", 10000),
            "max_sim_duration": config.get("max_sim_duration", 300),
            "max_player_duration": config.get("max_player_duration", 7200),
            "output_manager": self.output_manager
        }
        
        # 直接创建所有任务
        all_tasks = []
        task_id = 0
        for player_id, machine_id in pairs:
            for session_num in range(sessions_per_pair):
                session_id = f"{player_id}_{machine_id}_{session_num+1}"
                
                # 创建任务函数
                def create_task(p_id=player_id, m_id=machine_id, s_id=session_id, s_config=session_config):
                    def task():
                        return self._run_single_session(p_id, m_id, s_id, s_config)
                    return task
                
                all_tasks.append(create_task())
                task_id += 1
        
        self.logger.info(f"Created {len(all_tasks)} session tasks for concurrent execution")
        
        # 使用TaskExecutor执行
        if hasattr(self.task_executor, 'execute_with_progress'):
            def progress_callback(completed, total):
                if completed % 100 == 0 or completed == total:
                    elapsed = time.time() - self.results["start_time"]
                    rate = completed / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Progress: {completed}/{total} ({completed/total*100:.1f}%) - {rate:.1f} sessions/sec")
            
            results = self.task_executor.execute_with_progress(all_tasks, progress_callback)
        else:
            results = self.task_executor.execute(all_tasks)
        
        return [r for r in results if r is not None]
    
    def _execute_sessions_sequential(self, pairs: List[Tuple[str, str]], 
                                   sessions_per_pair: int, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        顺序执行sessions
        """
        results = []
        session_config = {
            "max_spins": config.get("max_spins", 10000),
            "max_sim_duration": config.get("max_sim_duration", 300),
            "max_player_duration": config.get("max_player_duration", 7200),
            "output_manager": self.output_manager
        }
        
        total_sessions = len(pairs) * sessions_per_pair
        completed = 0
        
        for player_id, machine_id in pairs:
            for session_num in range(sessions_per_pair):
                session_id = f"{player_id}_{machine_id}_{session_num+1}"
                
                result = self._run_single_session(player_id, machine_id, session_id, session_config)
                if result:
                    results.append(result)
                
                completed += 1
                if completed % 100 == 0 or completed == total_sessions:
                    elapsed = time.time() - self.results["start_time"]
                    rate = completed / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Progress: {completed}/{total_sessions} ({completed/total_sessions*100:.1f}%) - {rate:.1f} sessions/sec")
        
        return results
    
    def _run_single_session(self, player_id: str, machine_id: str, session_id: str, 
                          session_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        运行单个session，使用实例池
        """
        # 从实例池获取无状态实例
        player_instance = self.registry_service.get_player_instance(player_id, timeout=10.0)
        machine_instance = self.registry_service.get_machine_instance(machine_id, timeout=10.0)
        
        if not player_instance or not machine_instance:
            self.logger.error(f"Failed to get instances for session {session_id}")
            return None
        
        try:
            # 创建带状态管理的session
            session = self.session_factory.create_session(
                player=player_instance,
                machine=machine_instance,
                session_id=session_id,
                base_output_manager=self.output_manager,
                output_config=session_config.get("output", {})
            )
            
            # 创建runner并运行
            runner = SessionRunner(
                session=session,
                event_dispatcher=self.event_dispatcher,
                config=session_config
            )
            
            result = runner.run()
            return result
            
        except Exception as e:
            self.logger.error(f"Session {session_id} failed: {str(e)}")
            import traceback
            self.logger.debug(f"Session {session_id} traceback: {traceback.format_exc()}")
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
        
        finally:
            # 归还实例到池中
            if player_instance:
                self.registry_service.return_player_instance(player_id, player_instance)
            if machine_instance:
                self.registry_service.return_machine_instance(machine_id, machine_instance)
    
    def _generate_analysis_and_reports(self, config: Dict[str, Any]):
        """
        生成分析和报告
        """
        try:
            analysis_config = config.get("analysis", {})
            
            if analysis_config.get("enable", True):
                self._generate_reports(analysis_config)
            
            self.logger.info("Analysis and reports generated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to generate analysis and reports: {e}")
    
    def _generate_reports(self, analysis_config: Dict[str, Any]):
        """
        生成分析报告
        """
        try:
            # 分析所有会话
            session_analyses = []
            for session_data in self.results["sessions"]:
                analysis = self.session_analyzer.analyze_session(session_data)
                session_analyses.append(analysis)
            
            # 获取报告目录路径
            reports_dir = self.output_manager.get_reports_directory()
            
            # 创建报告生成器（传入目录路径，不是OutputManager对象）
            report_generator = ReportGenerator(reports_dir)
            
            # 生成不同类型的报告
            include_config = analysis_config.get("include", {})
            
            if include_config.get("summary_report", True):
                summary_report = self._generate_summary_report(session_analyses)
                report_generator.generate_summary_report(summary_report, {})
            
            if include_config.get("player_preference_report", False):
                pass
                # TODO
                # preference_analysis = self.preference_analyzer.analyze_player_preferences(session_analyses)
                # report_generator.generate_player_preference_report(preference_analysis)
            
            if include_config.get("machine_performance_report", False):
                pass
                # TODO 
                # machine_analysis = self._generate_machine_performance_analysis(session_analyses)
                # report_generator.generate_machine_performance_report(machine_analysis)
            
            self.logger.info("Reports generated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to generate reports: {e}")
            import traceback
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
    
    def _generate_summary_report(self, session_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成汇总报告
        """
        if not session_analyses:
            return {}
        
        total_sessions = len(session_analyses)
        total_spins = sum(a.get("performance", {}).get("total_spins", 0) for a in session_analyses)
        total_bet = sum(a.get("performance", {}).get("total_bet", 0.0) for a in session_analyses)
        total_win = sum(a.get("performance", {}).get("total_win", 0.0) for a in session_analyses)
        
        overall_rtp = total_win / total_bet if total_bet > 0 else 0.0
        
        durations = [a.get("player_behavior", {}).get("duration", 0.0) for a in session_analyses]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        return {
            "total_sessions": total_sessions,
            "total_spins": total_spins,
            "total_bet": total_bet,
            "total_win": total_win,
            "overall_rtp": overall_rtp,
            "avg_session_duration": avg_duration,
            "net_result": total_win - total_bet,
            "simulation_duration": self.results["end_time"] - self.results["start_time"]
        }
    
    def _generate_machine_performance_analysis(self, session_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成机器性能分析
        """
        machine_stats = defaultdict(lambda: {
            "total_spins": 0,
            "total_bet": 0.0,
            "total_win": 0.0,
            "session_count": 0
        })
        
        for analysis in session_analyses:
            machine_id = analysis.get("machine_id", "unknown")
            performance = analysis.get("performance", {})
            
            machine_stats[machine_id]["total_spins"] += performance.get("total_spins", 0)
            machine_stats[machine_id]["total_bet"] += performance.get("total_bet", 0.0)
            machine_stats[machine_id]["total_win"] += performance.get("total_win", 0.0)
            machine_stats[machine_id]["session_count"] += 1
        
        # 计算每台机器的RTP
        for machine_id, stats in machine_stats.items():
            stats["rtp"] = stats["total_win"] / stats["total_bet"] if stats["total_bet"] > 0 else 0.0
            stats["avg_spins_per_session"] = stats["total_spins"] / stats["session_count"]
        
        return dict(machine_stats)