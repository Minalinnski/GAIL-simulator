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
        """
        更新余额
        
        Args:
            amount: 要添加到余额的金额（负数为扣除）
        """
        self.session_balance += amount
        self.logger.debug(f"Balance updated: {self.session_balance:.2f} ({amount:+.2f})")
    
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
        current_time = time.time()
        
        # 基本会话数据
        session_data = {
            "session_id": self.id,
            "machine_id": self.machine.id,
            "start_time": self.sim_start_time,
            "current_time": current_time,
            "duration": current_time - self.sim_start_time if self.sim_start_time else 0,
            "start_balance": self.initial_balance,
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
        
        # 初始化统计开始时间和余额
        self.stats.start_time = self.sim_start_time
        self.stats.start_balance = self.initial_balance
        
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
                    "start_balance": self.initial_balance,
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
        
        # 更新统计结束时间
        self.stats.end_time = self.sim_end_time
        self.stats.final_balance = self.session_balance
        
        duration = self.sim_end_time - self.sim_start_time
        self.logger.info(f"Session ended - Duration: {duration:.1f}s, Final balance: {self.session_balance:.2f}")
        
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
                    "duration": duration,
                    "final_balance": self.session_balance,
                    "total_spins": self.stats.total_spins,
                    "total_profit": self.stats.total_win - self.stats.total_bet
                }
            ))
            
    def execute_spin(self, bet_amount: float, machine_result: Dict[str, Any]) -> SpinResult:
        """
        Execute a single spin and update session state.
        
        Args:
            bet_amount: Amount bet on this spin
            machine_result: Result from slot machine spin
            
        Returns:
            SpinResult instance with complete spin information
        """
        # 保存旋转前余额
        balance_before = self.session_balance
        
        # 从余额中扣除投注
        self.update_balance(-bet_amount)
        
        # 获取赢取金额
        win_amount = machine_result.get("total_win", 0.0)
        payout = win_amount  # payout即为win_amount
        
        if win_amount > 0:
            self.update_balance(win_amount)
        
        # 计算利润
        profit = win_amount - bet_amount
        
        # 计算odds
        odds = win_amount / bet_amount if bet_amount > 0 else 0.0
        
        # 创建旋转结果 - 使用正确的字段名
        spin_result = SpinResult(
            session_id=self.id,  # 必需的session_id
            spin_number=len(self.spins) + 1,
            bet=bet_amount,  # 注意字段名是 bet 不是 bet_amount
            payout=payout,   # 注意字段名是 payout 不是 win_amount
            profit=profit,
            odds=odds,
            balance_before=balance_before,
            balance_after=self.session_balance,
            result_grid=machine_result.get("symbols", []),
            in_free_spins=self.in_free_spins,
            free_spins_triggered=machine_result.get("trigger_free_spins", False),
            free_spins_remaining=self.free_spins_remaining,
            line_wins=machine_result.get("line_wins", []),
            line_wins_info=machine_result.get("line_wins_info", []),
            scatter_win=machine_result.get("scatter_win", 0.0),
            timestamp=time.time()
        )
        
        # 记录旋转结果
        if self.should_record_spins:
            self.spins.append(spin_result)
        
        # 更新统计 - 使用SpinResult对象
        self.stats.update_spin(spin_result)
        
        # 处理免费旋转触发
        if machine_result.get("trigger_free_spins", False):
            self.in_free_spins = True
            self.free_spins_remaining = machine_result.get("free_spins_count", 0)
            self.free_spins_base_bet = bet_amount
            
            # 派发免费旋转触发事件
            if self.event_dispatcher:
                self.event_dispatcher.dispatch(SessionEvent(
                    type=SessionEventType.FREE_SPINS_TRIGGERED,
                    session_id=self.id,
                    player_id=self.player.id,
                    machine_id=self.machine.id,
                    data={
                        "free_spins_count": self.free_spins_remaining,
                        "trigger_spin": spin_result.spin_number
                    }
                ))
        
        # 处理免费旋转计数
        if self.in_free_spins:
            self.free_spins_remaining -= 1
            if self.free_spins_remaining <= 0:
                self.in_free_spins = False
                self.free_spins_base_bet = 0.0
                
                # 派发免费旋转结束事件
                if self.event_dispatcher:
                    self.event_dispatcher.dispatch(SessionEvent(
                        type=SessionEventType.FREE_SPINS_ENDED,
                        session_id=self.id,
                        player_id=self.player.id,
                        machine_id=self.machine.id,
                        data={
                            "final_spin": spin_result.spin_number
                        }
                    ))
        
        # 检查大奖 - 使用odds而不是不存在的win_multiplier
        if odds >= self.BIG_WIN_THRESHOLD:
            spin_result.big_win = True
            if self.event_dispatcher:
                self.event_dispatcher.dispatch(SessionEvent(
                    type=SessionEventType.BIG_WIN,
                    session_id=self.id,
                    player_id=self.player.id,
                    machine_id=self.machine.id,
                    data={
                        "win_amount": win_amount,
                        "multiplier": odds,
                        "spin_number": spin_result.spin_number
                    }
                ))
        
        return spin_result
        
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
        
    def get_session_duration(self) -> float:
        """Get the session duration in seconds."""
        if not self.sim_start_time:
            return 0.0
        end_time = self.sim_end_time if self.sim_end_time else time.time()
        return end_time - self.sim_start_time
        
    def get_session_summary(self) -> Dict[str, Any]:
        """
        获取会话摘要信息（保持原有格式用于分析）
        """
        return self.stats.to_dict()