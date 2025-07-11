# src/domain/session/entities/gaming_session.py
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from src.domain.events.event_dispatcher import EventDispatcher
from src.domain.events.session_events import SessionEventType, SessionEvent
from .spin_result import SpinResult
from .session_stats import SessionStats


class GamingSession:
    """
    Represents a gaming session with centralized state management.
    All player states (balance, first_bet, etc.) are managed here.
    """
    def __init__(self, session_id: str, player, machine,
                event_dispatcher: Optional[EventDispatcher] = None, output_manager=None):
        """
        Initialize a gaming session with state management.
        
        Args:
            session_id: Unique identifier for this session
            player: Stateless Player entity instance
            machine: SlotMachine entity instance
            event_dispatcher: Optional event dispatcher for session events
            output_manager: Optional session-specific output manager
        """
        self.id = session_id
        self.player = player
        self.machine = machine
        self.event_dispatcher = event_dispatcher
        self.output_manager = output_manager
        
        self.logger = logging.getLogger(f"domain.session.{session_id}")
        self.logger.info(f"Initializing session between player {player.id} and machine {machine.id}")
        
        # === 状态管理（从Player转移过来） ===
        self.session_balance = self.player.generate_initial_balance()  # 当前余额
        self.initial_balance = self.session_balance  # 初始余额
        self.first_bet = self.player.generate_first_bet(self.session_balance)  # 首次投注
        
        # Session state
        self.sim_start_time = None
        self.sim_end_time = None
        self.active = False
        
        # 记录配置
        self.should_record_spins = True
        if output_manager:
            self.should_record_spins = output_manager.should_record_spins
        
        # 初始化统计对象（使用session管理的initial_balance）
        self.stats = SessionStats(
            session_id=session_id,
            player_id=player.id,
            machine_id=machine.id
        )
        
        # Tracking data - 简化为普通list
        self.spins = []
        
        # 当前状态
        self.in_free_spins = False
        self.free_spins_remaining = 0
        self.free_spins_base_bet = 0.0
        
        # 可用投注列表
        self.available_bets = []
        self._load_available_bets()
        
        # 常量定义
        self.NUM_TRACK_BACK = 10
        self.BIG_WIN_THRESHOLD = 10
        
        self.logger.info(f"Session initialized - Initial balance: {self.initial_balance:.2f}, First bet: {self.first_bet:.2f}")
        
    def _load_available_bets(self):
        """Load available bet options for the player's currency."""
        currency = self.player.currency
        
        if currency in self.machine.bet_table:
            self.available_bets = self.machine.bet_table[currency]
        else:
            # Use CNY as fallback
            self.available_bets = self.machine.bet_table.get("CNY", [1.0])
            
        self.logger.debug(f"Available bets for {currency}: {self.available_bets}")

    # === 状态管理方法（代理Player状态操作） ===
    def get_current_balance(self) -> float:
        """获取当前余额"""
        return self.session_balance
    
    def update_balance(self, amount: float):
        """更新余额"""
        self.session_balance += amount
        self.logger.debug(f"Balance updated: {self.session_balance:.2f} ({amount:+.2f})")

    def update_duration(self, delay: float):
        """更新时长"""
        if delay <= 0:
            self.logger.warning(f"Invalid delay accumulated: {delay}")
        self.stats.duration += delay
        self.logger.debug(f"Duration updated: {self.stats.duration:.2f} ({delay:+.2f})")
    
    def get_initial_balance(self) -> float:
        """获取初始余额"""
        return self.initial_balance
    
    def get_first_bet(self) -> float:
        """获取首次投注额"""
        return self.first_bet

    def get_session_data(self) -> Dict[str, Any]:
        """
        准备会话数据供Player决策使用（包含状态信息）
        """
        # current_time = time.time()
        
        # 基本会话数据
        session_data = {
            "session_id": self.id,
            "machine_id": self.machine.id,
            # "start_time": self.sim_start_time,
            # "current_time": current_time,
            "duration": self.stats.duration,
            # "sim_duration": current_time - self.sim_start_time if self.sim_start_time else 0,
            "initial_balance": self.initial_balance,
            "current_balance": self.session_balance,  # 使用session管理的余额
            "total_spins": self.stats.total_spins,
            "win_count": self.stats.win_count,
            "total_bet": self.stats.total_bet,
            "total_win": self.stats.total_win,
            "total_profit": self.stats.total_win - self.stats.total_bet,
            "available_bets": self.available_bets,
            "currency": self.player.currency,
            "in_free_spins": self.in_free_spins,
            "free_spins_remaining": self.free_spins_remaining,
            "bonus_triggered": self.stats.bonus_triggered
        }
        
        # 添加最近的旋转结果 - 转换为字典格式
        recent_results = []
        for spin in self.spins[-self.NUM_TRACK_BACK:]:
            recent_results.append(spin)
        session_data["results"] = recent_results
        
        return session_data
        
    def start(self):
        """Start the gaming session."""
        if self.active:
            self.logger.warning("Session is already active")
            return
            
        self.sim_start_time = time.time()
        self.active = True
        
        # 初始化统计开始时间和余额 - 使用新的字段名
        self.stats.initial_balance = self.initial_balance
        
        self.logger.info(f"Session started - Initial balance: {self.initial_balance:.2f}, Current balance: {self.session_balance:.2f}")
        
        # 派发会话开始事件
        if self.event_dispatcher:
            self.event_dispatcher.dispatch(SessionEvent(
                type=SessionEventType.SESSION_STARTED,
                session_id=self.id,
                player_id=self.player.id,
                machine_id=self.machine.id,
                data={
                    "start_time": self.sim_start_time,
                    "initial_balance": self.initial_balance,
                    "current_balance": self.session_balance,
                    "first_bet": self.first_bet
                }
            ))
    
    def end(self):
        """End the gaming session."""
        if not self.active:
            self.logger.warning("Session is not active")
            return
            
        self.sim_end_time = time.time()
        self.active = False
        
        # 更新统计结束时间和最终余额 - 使用新的字段名
        self.stats.final_balance = self.session_balance
        self.stats.balance_change = self.session_balance - self.initial_balance
        
        sim_duration = self.get_sim_duration()
        self.logger.info(f"Session ended - Duration: {sim_duration}s, Final balance: {self.session_balance:.2f}")
        
        # 保存会话数据（如果有输出管理器）
        if self.output_manager:
            try:
                self.output_manager.save_session_data(self)
                self.logger.debug("Session data saved")
            except Exception as e:
                self.logger.error(f"Failed to save session data: {e}")
        
        # 派发会话结束事件
        if self.event_dispatcher:
            self.event_dispatcher.dispatch(SessionEvent(
                type=SessionEventType.SESSION_ENDED,
                session_id=self.id,
                player_id=self.player.id,
                machine_id=self.machine.id,
                data={
                    "end_time": self.sim_end_time,
                    "duration": self.stats.duration,
                    "sim_duration": sim_duration,
                    "final_balance": self.session_balance,
                    "total_spins": self.stats.total_spins,
                    "total_profit": self.stats.total_win - self.stats.total_bet
                }
            ))
            
    def execute_spin(self, bet_amount: float) -> Dict[str, Any]:
        """Execute a single spin and update session state."""
        if not self.active:
            self.logger.warning("Attempted to spin on inactive session")
            return {"error": "Session not active"}
        
        prev_balance = self.session_balance

        # 检查余额（只有非免费旋转需要检查）
        if not self.in_free_spins:
            if bet_amount > self.session_balance:
                self.logger.warning(f"Insufficient balance: {self.session_balance:.2f} < {bet_amount:.2f}")
                return {"error": f"Insufficient balance: {self.session_balance:.2f} < {bet_amount:.2f}"}
            
            # 扣除投注金额
            self.update_balance(-bet_amount)
        else:
            # 免费旋转使用基础投注金额
            bet_amount = self.free_spins_base_bet

        # 执行机器旋转
        result_grid, trigger_free, free_remaining = self.machine.spin(
            in_free=self.in_free_spins,
            num_free_left=self.free_spins_remaining
        )
        
        # 评估赢额
        win_data = self.machine.evaluate_win(
            grid=result_grid,
            bet=bet_amount,
            in_free=self.in_free_spins,
            active_lines=self.player.config.get("active_lines", None)
        )
        
        # 添加赢额到余额
        win_amount = win_data.get("total_win", 0)
        self.update_balance(win_amount)
        
        # 处理免费旋转状态
        if trigger_free and not self.in_free_spins:
            self.in_free_spins = True
            self.free_spins_remaining = free_remaining
            self.free_spins_base_bet = bet_amount
            self.stats.bonus_triggered = True
        elif self.in_free_spins:
            self.free_spins_remaining = free_remaining
            if self.free_spins_remaining <= 0:
                self.in_free_spins = False
                self.free_spins_base_bet = 0.0

        # 计算倍数和streak
        win_odds = win_amount / bet_amount if bet_amount > 0 else 0
        is_big_win = win_odds >= self.BIG_WIN_THRESHOLD
        
        streak = 0
        if len(self.spins) > 0:
            prev_win = self.spins[-1].get('payout', 0) > 0
            curr_win = win_amount > 0
            if curr_win == prev_win:
                streak = self.spins[-1].get('streak', 0)
                streak = streak + 1 if curr_win else streak - 1
            else:
                streak = 1 if curr_win else -1
        else:
            streak = 1 if win_amount > 0 else -1

        if win_amount > 0:
            self.logger.debug(f"Spin won: {win_amount} (x{win_amount/bet_amount:.1f})")
        
        self.logger.debug(
            f"Spin result: bet={bet_amount}, payout={win_amount}, " +
            f"balance={self.session_balance}, " + 
            f"free_spins={'active' if self.in_free_spins else 'inactive'}, " +
            f"remaining={self.free_spins_remaining}"
        )

        # 创建SpinResult对象
        spin_result = SpinResult(
            session_id=self.id,
            spin_number=self.stats.total_spins + 1,  # 注意：这里用+1，因为还没更新
            bet=bet_amount,
            payout=win_amount,
            profit=win_amount - bet_amount,
            odds=win_odds,
            balance_before=prev_balance,
            balance_after=self.session_balance,
            result_grid=result_grid,
            in_free_spins=self.in_free_spins,
            free_spins_triggered=trigger_free,
            free_spins_remaining=free_remaining,
            free_spins_base_bet=self.free_spins_base_bet,
            line_wins=win_data.get("line_wins", []),
            line_wins_info=win_data.get("line_wins_info", []),
            scatter_count=win_data.get("scatter_count", 0),
            scatter_win=win_data.get("scatter_win", 0),
            streak=streak,
            big_win=is_big_win
        )
        
        # 记录spin（如果需要）
        if self.should_record_spins:
            result_dict = spin_result.to_dict()
            # result_dict["win_data"] = win_data
            result_dict["session_index"] = (lambda x: x.split("_")[-1] if "_" in x else x)(self.id)
            result_dict["player_id"] = self.player.id
            result_dict["machine_id"] = self.machine.id
            self.spins.append(result_dict)
        
        # 统一使用update_spin方法更新所有统计
        self.stats.update_spin(spin_result)
        
        return spin_result.to_dict()

    def reset(self):
        """重置会话状态以进行新的模拟运行"""
        # 重新生成状态
        self.session_balance = self.player.generate_initial_balance()
        self.initial_balance = self.session_balance
        self.first_bet = self.player.generate_first_bet(self.session_balance)
        
        # 重置时间状态
        self.sim_start_time = None
        self.sim_end_time = None
        self.active = False
        
        # 清空记录
        self.spins.clear()
        
        # 重置游戏状态
        self.in_free_spins = False
        self.free_spins_remaining = 0
        self.free_spins_base_bet = 0.0
        
        # 重置统计对象
        self.stats = SessionStats(
            session_id=self.id,
            player_id=self.player.id,
            machine_id=self.machine.id
        )
        
        self.logger.debug(f"Session reset - New initial balance: {self.initial_balance:.2f}, New first bet: {self.first_bet:.2f}")
        
    def is_active(self) -> bool:
        """Check if the session is currently active."""
        return self.active
        
    def get_total_spins(self) -> int:
        """Get the total number of spins played."""
        return self.stats.total_spins
        
    def get_sim_duration(self) -> float:
        """Get the session simulation duration in seconds."""
        if not self.sim_start_time:
            return 0.0
        end_time = self.sim_end_time if self.sim_end_time else time.time()
        return end_time - self.sim_start_time
        
    def get_session_summary(self) -> Dict[str, Any]:
        """
        获取会话摘要信息（保持原有格式用于分析）
        """
        return self.stats.to_dict()