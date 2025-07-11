# src/application/simulation/session_runner.py
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from src.domain.events.event_dispatcher import EventDispatcher
from src.domain.events.session_events import SessionEventType, SessionEvent


class SessionRunner:
    """
    运行单个游戏会话从开始到结束。
    适配无状态Player架构，通过Session管理所有状态。
    """
    def __init__(self, session, event_dispatcher: Optional[EventDispatcher] = None, config: Dict[str, Any] = None):
        """
        初始化会话运行器。
        
        Args:
            session: GamingSession 实例（管理所有状态）
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
        运行会话的主要方法，按照原始设计流程。
        
        Returns:
            包含会话结果的字典
        """
        self.logger.info(f"Starting session {self.session.id} for player {self.session.player.id} on machine {self.session.machine.id}")
        self.session.start()
        
        # 初始化
        next_bet_amount = self.session.get_first_bet()  # 预计算的首次投注
        next_delay_time = 0.0
        
        try:
            while True:
                # === 硬性停止检查（SessionRunner负责） ===
                self.logger.debug(f"In runner: Checking strict termination")
                terminate_reason = self._check_termination_conditions()
                if terminate_reason:
                    self.logger.debug(f"Session terminated: {terminate_reason}")
                    break

                # === 执行Spin ===
                self.logger.debug(f"In runner: Executing Spin")
                spin_result = self.session.execute_spin(next_bet_amount)

                # 检查错误
                if "error" in spin_result:
                    error_msg = spin_result.get("error", "Unknown error")
                    
                    # 检查是否是余额不足错误
                    if "Insufficient balance" in error_msg:
                        self._dispatch_event(SessionEventType.SESSION_ENDED, {
                            "reason": "insufficient_balance",
                            "total_spins": self.session.stats.total_spins,
                            "player_time": self.session.stats.duration
                        })
                    else:
                        self._dispatch_event(SessionEventType.SESSION_ENDED, {
                            "reason": "error",
                            "error": error_msg,
                            "total_spins": self.session.stats.total_spins,
                            "player_time": self.session.stats.duration
                        })
                    
                    self.logger.warning(f"Error in spin: {error_msg}")
                    break

                # === 模型推理（为下一次spin做准备） ===
                self.logger.debug(f"In runner: Model Inference")
                # 准备当前会话状态数据
                session_data = self.session.get_session_data()

                session_data["delta_t"] = next_delay_time
                
                # 玩家决策：决定下一次的投注、延迟和是否结束（无状态调用）
                next_bet_amount, next_delay_time = self.session.player.play(self.session.machine.id, session_data)
                
                # 检查玩家是否想结束会话
                if next_bet_amount < 0 or self.session.player.should_end_session(self.session.machine.id, session_data):
                    self._dispatch_event(SessionEventType.SESSION_ENDED, {
                        "reason": "player_decision",
                        "total_spins": self.session.stats.total_spins,
                        "player_time": self.session.stats.duration
                    })
                    self.logger.debug(f"Player {self.session.player.id} decided to end session after {self.session.stats.total_spins} spins")
                    break
            
        except Exception as e:
            self.logger.error(f"Error during session execution: {str(e)}")
            self._dispatch_event(SessionEventType.SESSION_ENDED_BY_ERROR, {
                "error": str(e),
                "spins_completed": self.session.stats.total_spins
            })
            raise
        
        # 结束会话
        self.session.end()
        total_duration = self.session.get_sim_duration()
        self.logger.info(f"Session completed - Spins: {self.session.stats.total_spins}, Duration: {total_duration:.1f}s, Player time: {self.session.stats.duration:.1f}s")
        
        # 返回会话结果
        return {
            "session_id": self.session.id,
            "player_id": self.session.player.id,
            "machine_id": self.session.machine.id,
            "total_spins": self.session.stats.total_spins,
            "total_duration": total_duration,
            "player_time": self.session.stats.duration,
            "final_balance": self.session.get_current_balance(),
            "initial_balance": self.session.get_initial_balance(),
            "total_profit": self.session.stats.total_profit,
            "total_bet": self.session.stats.total_bet,
            "total_win": self.session.stats.total_win,
            "session_stats": self.session.get_session_summary()
        }
        
    def _check_termination_conditions(self) -> Optional[str]:
        """
        检查会话终止条件。
        
        Args:
            self.session.stats.total_spins: 当前旋转次数
            player_time: 累积玩家时间
            sim_start_time: 模拟开始时间
            
        Returns:
            终止原因字符串，如果不需要终止则返回None
        """
        # 检查旋转次数限制
        if self.session.stats.total_spins >= self.max_spins:
            return f"max_spins_reached_{self.max_spins}"
        
        # 检查模拟时间限制
        if self.session.get_sim_duration() >= self.max_sim_duration:
            return f"max_sim_duration_reached_{self.max_sim_duration}"
        
        # 检查玩家时间限制
        if self.session.stats.duration >= self.max_player_duration:
            return f"max_player_duration_reached_{self.max_player_duration}"
        
        return None
        
    # def _run_free_spins_sequence(self) -> Tuple[List[Dict[str, Any]], int, Optional[Exception]]:
    #     """
    #     运行免费旋转序列。
        
    #     Returns:
    #         (免费旋转结果列表, 旋转次数, 错误)
    #     """
    #     free_spin_results = []
    #     free_spins_count = 0
    #     error = None
        
    #     try:
    #         self.logger.debug(f"Starting free spins sequence: {self.session.free_spins_remaining} spins")
            
    #         while self.session.in_free_spins and self.session.free_spins_remaining > 0:
    #             # 使用基础投注进行免费旋转
    #             bet_amount = self.session.free_spins_base_bet
                
    #             # 机器旋转
    #             machine_result = self.session.machine.spin(bet_amount, self.session.player.currency)
                
    #             # 会话执行旋转
    #             spin_result = self.session.execute_spin(bet_amount, machine_result)
                
    #             free_spin_results.append({
    #                 "spin_number": spin_result.spin_number,
    #                 "bet_amount": bet_amount,
    #                 "win_amount": spin_result.win_amount,
    #                 "profit": spin_result.profit,
    #                 "balance_after": self.session.get_current_balance()
    #             })
                
    #             free_spins_count += 1
                
    #             # 派发免费旋转完成事件
    #             self._dispatch_event(SessionEventType.SPIN_COMPLETED, {
    #                 "spin_number": spin_result.spin_number,
    #                 "bet_amount": bet_amount,
    #                 "win_amount": spin_result.win_amount,
    #                 "balance_after": self.session.get_current_balance(),
    #                 "profit": spin_result.profit,
    #                 "free_spin": True
    #             })
                
    #     except Exception as e:
    #         self.logger.error(f"Error in free spins sequence: {e}")
    #         error = e
            
    #     self.logger.debug(f"Free spins sequence completed: {free_spins_count} spins")
    #     return free_spin_results, free_spins_count, error
        
    def _dispatch_event(self, event_type: SessionEventType, data: Dict[str, Any]):
        """
        派发会话事件。
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if self.event_dispatcher:
            self.event_dispatcher.dispatch(SessionEvent(
                type=event_type,
                session_id=self.session.id,
                player_id=self.session.player.id,
                machine_id=self.session.machine.id,
                data=data
            ))