# src/application/simulation/session_runner.py
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from src.domain.events.event_dispatcher import EventDispatcher
from src.domain.events.session_events import SessionEventType, SessionEvent


class SessionRunner:
    """
    运行单个游戏会话从开始到结束。
    处理会话逻辑，包括旋转循环和终止检查。
    """
    def __init__(self, session, event_dispatcher: Optional[EventDispatcher] = None, config: Dict[str, Any] = None):
        """
        初始化会话运行器。
        
        Args:
            session: GamingSession 实例
            event_dispatcher: 可选的事件调度器
            config: 可选的配置参数
        """
        self.logger = logging.getLogger(f"application.simulation.runner.{session.id}")
        self.session = session
        self.event_dispatcher = event_dispatcher
        
        # 初始化配置（默认值或从传入配置获取）
        self.config = config or {}
        self.max_spins = self.config.get("max_spins", 100000)
        self.max_sim_duration = self.config.get("max_sim_duration", 3600)  # 默认1小时
        self.max_player_duration = self.config.get("max_player_duration", 7200)  # 默认2小时
        
        # 获取输出管理器（如果有）
        self.output_manager = self.config.get("output_manager", None)



        
    def run(self) -> Dict[str, Any]:
        """
        执行会话从开始到结束。
        
        Returns:
            包含会话统计信息的字典
        """
        self.logger.info(f"Starting session {self.session.id} for player {self.session.player.id} on machine {self.session.machine.id}")
        
        # 开始会话
        self.session.start()
        sim_start_time = time.time()
        
        # 跟踪统计
        spin_count = 0
        player_time = 0.0  # 累积玩家逻辑时间
        
        # 会话运行主循环
        while True:
            # 检查会话是否应该终止
            terminate_reason = self._check_termination_conditions(
                spin_count, 
                player_time, 
                sim_start_time
            )
            
            if terminate_reason:
                self.logger.debug(f"Session terminated: {terminate_reason}")
                break
            
            # 检查是否处于免费旋转状态
            if self.session.in_free_spins:
                # 处理免费旋转序列
                free_results, free_spins_count, error = self._run_free_spins_sequence()
                spin_count += free_spins_count
                
                if error:
                    # 发生错误，终止会话
                    self._dispatch_event(SessionEventType.SESSION_ENDED, {
                        "reason": "error_in_free_spins",
                        "error": error
                    })
                    break
                
                # 免费旋转不增加玩家时间，因为是自动进行的
                continue
            
            # 获取会话数据用于玩家决策
            session_data = self.session.get_data_for_decision()
            
            # 检查玩家是否想结束会话
            if self.session.player.should_end_session(self.session.machine.id, session_data):
                self._dispatch_event(SessionEventType.SESSION_ENDED, {
                    "reason": "player_decision",
                    "total_spins": spin_count,
                    "player_time": player_time
                })
                self.logger.debug(f"Player {self.session.player.id} decided to end session after {spin_count} spins")
                break
                
            # 获取玩家的下一个下注决策
            bet_amount, delay = self.session.player.play(
                self.session.machine.id, 
                session_data
            )
            
            # 如果玩家不想下注，结束会话
            if bet_amount <= 0:
                self._dispatch_event(SessionEventType.SESSION_ENDED, {
                    "reason": "player_zero_bet",
                    "total_spins": spin_count,
                    "player_time": player_time
                })
                self.logger.debug(f"Player {self.session.player.id} signaled end of session (bet=0)")
                break
                
            # 执行旋转
            spin_result = self.session.execute_spin(bet_amount)
            
            # 检查错误
            if "error" in spin_result:
                error_msg = spin_result.get("error", "Unknown error")
                
                # 检查是否是余额不足错误
                if "Insufficient balance" in error_msg:
                    self._dispatch_event(SessionEventType.SESSION_ENDED, {
                        "reason": "insufficient_balance",
                        "total_spins": spin_count,
                        "player_time": player_time
                    })
                else:
                    self._dispatch_event(SessionEventType.SESSION_ENDED, {
                        "reason": "error",
                        "error": error_msg,
                        "total_spins": spin_count,
                        "player_time": player_time
                    })
                
                self.logger.warning(f"Error in spin: {error_msg}")
                break
                
            # 增加旋转计数，累加玩家决策时间
            spin_count += 1
            player_time += delay
            self.session.duration = player_time
        
        # 结束会话
        self.session.end()
        
        statistics = self.session.get_statistics()
        sim_duration = time.time() - sim_start_time
        
        self.logger.info(
            f"Session completed: sim time: {sim_duration:.2f}s, " +
            f"{spin_count} spins, " +
            f"player time: {player_time:.2f}s, " +
            f"bet: {statistics['total_bet']:.2f}, " +
            f"win: {statistics['total_win']:.2f}, " +
            f"net: {statistics['total_profit']:.2f}, " +
            f"RTP: {statistics['return_to_player']:.2%}"
        )
        
        return statistics
    
    def _check_termination_conditions(self, spin_count: int, player_time: float, 
                                    sim_start_time: float) -> Optional[str]:
        """
        检查会话是否应该终止的条件。
        
        Args:
            spin_count: 当前旋转次数
            player_time: 累积玩家时间
            sim_start_time: 模拟开始时间
            
        Returns:
            终止原因，如果应该终止；否则为None
        """
        # 1. 检查旋转次数限制
        if spin_count >= self.max_spins:
            self._dispatch_event(SessionEventType.SESSION_ENDED, {
                "reason": "max_spins_reached",
                "total_spins": spin_count,
                "player_time": player_time
            })
            return "max_spins_reached"
            
        # 2. 检查模拟时长限制
        current_time = time.time()
        sim_duration = current_time - sim_start_time
        if sim_duration >= self.max_sim_duration:
            self._dispatch_event(SessionEventType.SESSION_ENDED, {
                "reason": "max_sim_duration_reached",
                "total_spins": spin_count,
                "player_time": player_time,
                "sim_duration": sim_duration
            })
            return "max_sim_duration_reached"
            
        # 3. 检查玩家时间限制
        if player_time >= self.max_player_duration:
            self._dispatch_event(SessionEventType.SESSION_ENDED, {
                "reason": "max_player_duration_reached",
                "total_spins": spin_count,
                "player_time": player_time
            })
            return "max_player_duration_reached"
            
        # 没有满足终止条件
        return None
    
    def _run_free_spins_sequence(self) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        """
        运行一个完整的免费旋转序列直到结束。
        
        Returns:
            (免费旋转结果列表, 免费旋转次数, 错误信息[如有])
        """
        free_spin_results = []
        free_spins_count = 0
        error = None
        
        self.logger.debug(f"Starting free spins sequence with {self.session.free_spins_remaining} free spins")
        
        # 连续执行所有免费旋转
        while self.session.in_free_spins and self.session.free_spins_remaining > 0:
            # # 检查玩家是否想结束会话 - 新增：在free spin中也允许退出决策
            # session_data = self.session.get_data_for_decision()
            
            # if self.session.player.should_end_session(self.session.machine.id, session_data):
            #     self._dispatch_event(SessionEventType.SESSION_ENDED, {
            #         "reason": "player_decision_during_free_spins",
            #         "free_spins_remaining": self.session.free_spins_remaining,
            #         "free_spins_completed": free_spins_count
            #     })
            #     self.logger.debug(f"Player {self.session.player.id} decided to end session during free spins")
            #     break
            
            # 执行免费旋转
            result = self.session.execute_spin(0.0)  # 传入0因为免费旋转会使用记录的base_bet
            
            # 检查错误
            if "error" in result:
                error_msg = result.get("error", "Unknown error")
                self.logger.warning(f"Error in free spin: {error_msg}")
                error = error_msg
                break
                
            free_spin_results.append(result)
            free_spins_count += 1
            
            self.logger.debug(f"Free spin {free_spins_count} completed, remaining: {self.session.free_spins_remaining}")
            
        self.logger.debug(f"Free spins sequence completed: {free_spins_count} free spins executed")
        return free_spin_results, free_spins_count, error
    
    def _dispatch_event(self, event_type: SessionEventType, data: Dict[str, Any] = None):
        """
        便捷方法用于派发会话事件。
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if not self.event_dispatcher:
            return
            
        if data is None:
            data = {}
            
        self.event_dispatcher.dispatch(SessionEvent(
            type=event_type,
            session_id=self.session.id,
            player_id=self.session.player.id,
            machine_id=self.session.machine.id,
            data=data
        ))
    
    def _is_test_environment(self) -> bool:
        """
        Check if this is running in a test environment.
        
        Returns:
            True if in a test environment
        """
        import os
        return os.environ.get("TESTING", "0") == "1"