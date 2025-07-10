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
        is_first_spin = True  # 标记首次旋转
        
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
                        "error": str(error)
                    })
                    break
                    
                # 免费旋转完成后继续正常流程
                continue
            
            # 准备当前会话状态数据
            session_data = self.session.prepare_session_data()
            
            # 玩家决策时间开始
            player_decision_start = time.time()
            
            # 检查玩家是否想要结束会话（无状态调用）
            if self.session.player.should_end_session(self.session.machine.id, session_data):
                self.logger.debug("Player decided to end session")
                self._dispatch_event(SessionEventType.SESSION_ENDED_BY_PLAYER, {
                    "reason": "player_decision",
                    "spins_played": spin_count
                })
                break
            
            # 玩家做出投注决策（无状态调用）
            bet_amount, delay_time = self.session.player.play(self.session.machine.id, session_data)
            
            # 检查特殊投注值
            if bet_amount <= 0:
                self.logger.debug(f"Invalid bet amount {bet_amount}, ending session")
                self._dispatch_event(SessionEventType.SESSION_ENDED_BY_PLAYER, {
                    "reason": "invalid_bet",
                    "bet_amount": bet_amount
                })
                break
            
            # 对于首次旋转，使用预计算的first_bet（如果available）
            if is_first_spin:
                first_bet = self.session.get_first_bet()
                if first_bet > 0 and first_bet <= self.session.get_current_balance():
                    bet_amount = first_bet
                    self.logger.debug(f"Using pre-calculated first bet: {bet_amount}")
                is_first_spin = False
            
            # 检查余额是否足够
            if bet_amount > self.session.get_current_balance():
                self.logger.debug(f"Insufficient balance for bet {bet_amount}, current balance: {self.session.get_current_balance()}")
                self._dispatch_event(SessionEventType.SESSION_ENDED_BY_BALANCE, {
                    "reason": "insufficient_balance",
                    "bet_amount": bet_amount,
                    "balance": self.session.get_current_balance()
                })
                break
            
            # 机器旋转（无状态调用）
            machine_result = self.session.machine.spin(bet_amount, self.session.player.currency)
            
            # 会话执行旋转并更新状态
            spin_result = self.session.execute_spin(bet_amount, machine_result)
            
            spin_count += 1
            
            # 记录玩家决策时间
            player_decision_end = time.time()
            decision_time = player_decision_end - player_decision_start
            player_time += decision_time
            
            # 模拟延迟
            if delay_time > 0:
                time.sleep(delay_time)
                player_time += delay_time
            
            # 派发旋转完成事件
            self._dispatch_event(SessionEventType.SPIN_COMPLETED, {
                "spin_number": spin_result.spin_number,
                "bet_amount": bet_amount,
                "win_amount": spin_result.win_amount,
                "balance_after": self.session.get_current_balance(),
                "profit": spin_result.profit
            })
            
            # 检查余额是否过低
            if self.session.get_current_balance() <= 0:
                self.logger.debug("Balance depleted, ending session")
                self._dispatch_event(SessionEventType.SESSION_ENDED_BY_BALANCE, {
                    "reason": "balance_depleted",
                    "final_balance": self.session.get_current_balance()
                })
                break
        
        # 结束会话
        self.session.end()
        
        # 计算最终统计
        sim_end_time = time.time()
        total_duration = sim_end_time - sim_start_time
        
        self.logger.info(f"Session completed - Spins: {spin_count}, Duration: {total_duration:.1f}s, Player time: {player_time:.1f}s")
        
        # 返回会话统计（保持原有格式）
        return self.session.get_session_summary()
        
    def _check_termination_conditions(self, spin_count: int, player_time: float, sim_start_time: float) -> Optional[str]:
        """
        检查会话终止条件。
        
        Args:
            spin_count: 当前旋转次数
            player_time: 累积玩家时间
            sim_start_time: 模拟开始时间
            
        Returns:
            终止原因字符串，如果不需要终止则返回None
        """
        # 检查旋转次数限制
        if spin_count >= self.max_spins:
            return f"max_spins_reached_{self.max_spins}"
        
        # 检查模拟时间限制
        current_time = time.time()
        sim_duration = current_time - sim_start_time
        if sim_duration >= self.max_sim_duration:
            return f"max_sim_duration_reached_{self.max_sim_duration}"
        
        # 检查玩家时间限制
        if player_time >= self.max_player_duration:
            return f"max_player_duration_reached_{self.max_player_duration}"
        
        return None
        
    def _run_free_spins_sequence(self) -> Tuple[List[Dict[str, Any]], int, Optional[Exception]]:
        """
        运行免费旋转序列。
        
        Returns:
            (免费旋转结果列表, 旋转次数, 错误)
        """
        free_spin_results = []
        free_spins_count = 0
        error = None
        
        try:
            self.logger.debug(f"Starting free spins sequence: {self.session.free_spins_remaining} spins")
            
            while self.session.in_free_spins and self.session.free_spins_remaining > 0:
                # 使用基础投注进行免费旋转
                bet_amount = self.session.free_spins_base_bet
                
                # 机器旋转
                machine_result = self.session.machine.spin(bet_amount, self.session.player.currency)
                
                # 会话执行旋转
                spin_result = self.session.execute_spin(bet_amount, machine_result)
                
                free_spin_results.append({
                    "spin_number": spin_result.spin_number,
                    "bet_amount": bet_amount,
                    "win_amount": spin_result.win_amount,
                    "profit": spin_result.profit,
                    "balance_after": self.session.get_current_balance()
                })
                
                free_spins_count += 1
                
                # 派发免费旋转完成事件
                self._dispatch_event(SessionEventType.SPIN_COMPLETED, {
                    "spin_number": spin_result.spin_number,
                    "bet_amount": bet_amount,
                    "win_amount": spin_result.win_amount,
                    "balance_after": self.session.get_current_balance(),
                    "profit": spin_result.profit,
                    "free_spin": True
                })
                
        except Exception as e:
            self.logger.error(f"Error in free spins sequence: {e}")
            error = e
            
        self.logger.debug(f"Free spins sequence completed: {free_spins_count} spins")
        return free_spin_results, free_spins_count, error
        
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