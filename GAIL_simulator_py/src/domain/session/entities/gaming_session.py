# src/domain/session/entities/gaming_session.py
import logging
import time
from datetime import datetime
from collections import deque
from typing import Dict, List, Any, Optional, Tuple

from src.domain.events.event_dispatcher import EventDispatcher
from src.domain.events.session_events import SessionEventType, SessionEvent
from .spin_result import SpinResult
from .session_stats import SessionStats


class GamingSession:
    """
    Represents a gaming session between a player and a slot machine.
    Tracks the session state, results, and statistics.
    """
    def __init__(self, session_id: str, player, machine,
                event_dispatcher: Optional[EventDispatcher] = None, output_manager=None):
        """
        Initialize a gaming session.
        
        Args:
            session_id: Unique identifier for this session
            player: Player entity instance
            machine: SlotMachine entity instance
            event_dispatcher: Optional event dispatcher for session events
            output_manager: Optional output manager for saving data
        """
        self.id = session_id
        self.player = player
        self.machine = machine
        self.event_dispatcher = event_dispatcher
        self.output_manager = output_manager
        
        self.logger = logging.getLogger(f"domain.session.{session_id}")
        self.logger.info(f"Initializing session between player {player.id} and machine {machine.id}")
        
        # Session state
        self.sim_start_time = None
        self.sim_end_time = None
        self.active = False
        
        # 记录配置 - 简化，移除LRU和batch相关配置
        self.should_record_spins = True  # 默认值
        
        # 从output_manager读取配置
        if output_manager:
            self.should_record_spins = output_manager.should_record_spins
        
        # 初始化统计对象（所有统计数据都由它管理）
        self.stats = SessionStats(
            session_id=session_id,
            player_id=player.id,
            machine_id=machine.id
        )
        
        # Tracking data - 改为简单的list，移除LRU限制
        # self.spins = deque(maxlen=self.lru_max_size)  # 原来的LRU队列
        self.spins = []  # 简化为普通list
        
        # 当前状态
        self.in_free_spins = False
        self.free_spins_remaining = 0
        self.free_spins_base_bet = 0.0
        
        # 移除批次处理相关
        # self.batch_number = 0
        # self.result_batch = []
        
        # 可用投注列表
        self.available_bets = []
        self._load_available_bets()
        
        # 常量定义
        self.NUM_TRACK_BACK = 10           # 记录追溯次数
        self.BIG_WIN_THRESHOLD = 10        # 大奖阈值
        
    def _load_available_bets(self):
        """Load available bet options for the player's currency."""
        currency = self.player.currency
        
        if currency in self.machine.bet_table:
            self.available_bets = self.machine.bet_table[currency]
        else:
            # Use CNY as fallback
            self.available_bets = self.machine.bet_table.get("CNY", [1.0])
            
        self.logger.debug(f"Available bets for {currency}: {self.available_bets}")
        
    def start(self):
        """Start the gaming session."""
        if self.active:
            self.logger.warning("Session is already active")
            return
            
        self.sim_start_time = time.time()
        self.active = True
        
        # 初始化统计开始时间
        self.stats.start_time = self.sim_start_time
        self.stats.start_balance = self.player.balance
        
        self.logger.info(f"Session started - Balance: {self.player.balance}")
        
        # 派发会话开始事件
        if self.event_dispatcher:
            self.event_dispatcher.dispatch(SessionEvent(
                type=SessionEventType.SESSION_STARTED,
                session_id=self.id,
                player_id=self.player.id,
                machine_id=self.machine.id,
                data={
                    "start_time": self.sim_start_time,
                    "start_balance": self.player.balance
                }
            ))
    
    def end(self):
        """End the gaming session."""
        if not self.active:
            self.logger.warning("Session is not active")
            return
            
        self.sim_end_time = time.time()
        self.active = False
        
        # 移除原来的_flush_batch()调用
        
        # 更新统计状态
        self.stats.sim_end_time = datetime.fromtimestamp(self.sim_end_time)
        self.stats.sim_duration = self.sim_end_time - self.sim_start_time
        self.stats.active = False
        self.stats.end_balance = self.player.balance
        self.stats.balance_change = self.player.balance - self.stats.start_balance if self.stats.start_balance is not None else 0
        # 移除 self.stats.batch_count = self.batch_number
            
        # 派发会话结束事件
        if self.event_dispatcher:
            self.event_dispatcher.dispatch(SessionEvent(
                type=SessionEventType.SESSION_ENDED,
                session_id=self.id,
                player_id=self.player.id,
                machine_id=self.machine.id,
                data=self.get_statistics()
            ))
            
        # 写入会话数据 - 新增，session结束时一次性写入
        self._write_session_data()
            
        self.logger.info(f"Session ended with {self.stats.total_spins} spins, " +
                       f"bet: {self.stats.total_bet}, payout: {self.stats.total_win}, " +
                       f"final balance: {self.player.balance}")
                       
    def execute_spin(self, bet_amount: float) -> Dict[str, Any]:
        """保持你原来的方法名和签名"""
        if not self.active:
            self.logger.warning("Attempted to spin on inactive session")
            return {"error": "Session not active"}
            
        if self.in_free_spins:
            return self._execute_free_spin()
        else:
            return self._execute_normal_spin(bet_amount)
        
    def _execute_normal_spin(self, bet_amount: float) -> Dict[str, Any]:
        # 验证投注金额
        if bet_amount <= 0:
            self.logger.warning(f"Invalid bet amount: {bet_amount}")
            return {"error": "Invalid bet amount"}
            
        # 检查玩家余额是否足够
        if self.player.balance < bet_amount:
            self.logger.warning(f"Insufficient balance: {self.player.balance} < {bet_amount}")
            return {"error": "Insufficient balance"}
    
        prev_balance = self.player.balance
            
        self.player.update_balance(-bet_amount)
        self.stats.total_bet += bet_amount
        
        # 执行机器上的旋转并处理结果
        return self._process_spin_result(bet_amount, prev_balance)
    
    def _execute_free_spin(self) -> Dict[str, Any]:
        # 确保在免费旋转模式中
        if not self.in_free_spins or self.free_spins_remaining <= 0:
            self.logger.warning("Attempted to execute free spin when not in free spins mode")
            return {"error": "Not in free spins mode"}

        bet_amount = self.free_spins_base_bet
        if bet_amount <= 0:
            self.logger.warning(f"Invalid free spins base bet amount: {bet_amount}")
            return {"error": "Invalid bet amount"}

        prev_balance = self.player.balance
        
        # 执行机器上的旋转并处理结果
        return self._process_spin_result(bet_amount, prev_balance)

    def _process_spin_result(self, bet_amount: float, prev_balance: float) -> Dict[str, Any]:
        # 执行机器上的旋转
        result_grid, trigger_free, free_remaining = self.machine.spin(
            in_free=self.in_free_spins,
            num_free_left=self.free_spins_remaining
        )
        
        # 评估赢额
        win_data = self.machine.evaluate_win(
            grid=result_grid,
            bet=bet_amount,
            in_free = self.in_free_spins,
            active_lines=self.player.config.get("active_lines", None)
        )
        
        # 将赢额添加到玩家余额
        win_amount = win_data.get("total_win", 0)
        self.player.update_balance(win_amount)
        
        # 更新统计数据
        self.stats.total_spins += 1
        self.stats.total_win += win_amount
        
        if self.in_free_spins:
            self.stats.free_spins_count += 1
            self.stats.free_game_win += win_amount
        else:
            self.stats.base_game_win += win_amount
        
        if win_amount > 0:
            self.stats.win_count += 1
        self.stats.win_rate = self.stats.win_count / self.stats.total_spins

        self.stats.total_profit = self.stats.total_win - self.stats.total_bet
        self.stats.return_to_player = self.stats.total_win / self.stats.total_bet if self.stats.total_bet > 0 else 0.0
        
        # 检查大奖
        win_odds = win_amount / bet_amount if bet_amount > 0 else 0
        is_big_win = win_odds >= self.BIG_WIN_THRESHOLD
        if is_big_win:
            self.stats.big_win_count += 1
        
        # 处理免费旋转触发和状态更新
        if trigger_free and not self.in_free_spins:
            # 新触发免费旋转
            self.in_free_spins = True
            self.free_spins_remaining = free_remaining
            self.free_spins_base_bet = bet_amount
            self.stats.bonus_triggered = True
            self.logger.info(f"Free spins triggered: {free_remaining} spins at bet {bet_amount}")
        elif self.in_free_spins:
            # 更新免费旋转剩余次数
            self.free_spins_remaining = free_remaining
            if self.free_spins_remaining <= 0:
                self.in_free_spins = False
                self.free_spins_base_bet = 0.0
                self.logger.info("Free spins sequence completed")
        
        # 计算当前streak
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

        # 创建旋转结果对象
        spin_result = SpinResult(
            session_id=self.id,
            spin_number=self.stats.total_spins,
            bet=bet_amount,
            payout=win_amount,
            profit=win_amount - bet_amount,
            odds = win_odds,
            balance_before=prev_balance,
            balance_after=self.player.balance,
            result_grid=result_grid,
            in_free_spins=self.in_free_spins,
            free_spins_triggered=trigger_free,
            free_spins_remaining=free_remaining,
            free_spins_base_bet=self.free_spins_base_bet,
            line_wins=win_data.get("line_wins", []),
            line_wins_info=win_data.get("line_wins_info", []),
            scatter_win=win_data.get("scatter_win", 0),
            streak=streak,
            big_win=is_big_win
        )
        
        # Log result
        if win_amount > 0:
            self.logger.debug(f"Spin won: {win_amount} (x{win_amount/bet_amount:.1f})")
        
        self.logger.debug(
            f"Spin result: bet={bet_amount}, payout={win_amount}, " +
            f"balance={self.player.balance}, " + 
            f"free_spins={'active' if self.in_free_spins else 'inactive'}, " +
            f"remaining={self.free_spins_remaining}"
        )
        
        # 转换为字典格式
        result_dict = spin_result.to_dict()
        self.spins.append(result_dict)
        # 添加win_data便于其他组件使用
        result_dict["win_data"] = win_data
            
        return result_dict

    def _write_session_data(self):
        """会话结束时写入数据文件"""
        if not self.output_manager:
            self.logger.warning("No output_manager, skipping data write")
            return
            
        self.logger.debug(f"Writing session data for {self.id}")
        
        # 写入session统计摘要
        self._write_session_summary()
        
        # 写入原始spin数据为CSV
        if self.should_record_spins and self.spins:
            self.logger.debug(f"Writing raw spins data: {len(self.spins)} spins for session {self.id}")
            self._write_raw_spins_csv()
        else:
            if not self.should_record_spins:
                self.logger.debug(f"Skipping raw spins data: record_spins disabled for session {self.id}")
            if not self.spins:
                self.logger.debug(f"Skipping raw spins data: no spins data for session {self.id}")

    # 移除原来的_flush_batch方法，替换为简单的写入方法
        
    def _write_session_summary(self):
        """写入会话摘要。"""
        if not self.output_manager:
            return
            
        stats = self.get_statistics()
        self.output_manager.write_session_summary(self.id, stats)
        
    def _write_raw_spins_csv(self):
        """写入原始spin数据为CSV格式"""
        if not self.output_manager or not self.spins:
            self.logger.warning(f"Cannot write raw spins: output_manager={bool(self.output_manager)}, spins_count={len(self.spins) if self.spins else 0}")
            return
            
        self.logger.debug(f"Calling output_manager.write_session_raw_data_csv for session {self.id}")
        
        # 写入CSV格式的原始数据
        filepath = self.output_manager.write_session_raw_data_csv(self.id, self.spins)
        
        if filepath:
            self.logger.debug(f"Successfully wrote raw data to: {filepath}")
        else:
            self.logger.error(f"Failed to write raw data for session {self.id}")
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取会话统计数据。
        
        Returns:
            包含会话统计信息的字典
        """
        # 使用SessionStats的to_dict方法获取统计数据
        # 不再支持高级统计
        return self.stats.to_dict(include_advanced=False)
        
    def get_data_for_decision(self) -> Dict[str, Any]:
        """
        Get session data formatted for player decision-making.
        保持你原来的方法名和返回格式
        """
        current_time = time.time()
        
        # 基本会话数据
        session_data = {
            "session_id": self.id,
            "machine_id": self.machine.id,
            "start_time": self.sim_start_time,
            "current_time": current_time,
            "duration": current_time - self.sim_start_time if self.sim_start_time else 0,
            "start_balance": self.stats.start_balance if self.stats.start_balance is not None else self.player.balance,
            "current_balance": self.player.balance,
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
        
        # 添加最近的旋转结果（最多NUM_TRACK_BACK个）
        recent_results = []
        # 改为从list获取最近的结果
        for spin in self.spins[-self.NUM_TRACK_BACK:]:
            recent_results.append(spin)
        session_data["results"] = recent_results
        
        return session_data
        
    def reset(self):
        """重置会话状态以进行新的模拟运行。保持你原来的方法"""
        self.sim_start_time = None
        self.sim_end_time = None
        self.active = False
        self.spins.clear()  # 改为list的clear()
        # 移除 balance_history
        self.in_free_spins = False
        self.free_spins_remaining = 0
        self.free_spins_base_bet = 0.0
        # 移除 result_batch 和 batch_number
        
        # 重置统计对象
        self.stats = SessionStats(
            session_id=self.id,
            player_id=self.player.id,
            machine_id=self.machine.id
        )
        
        # 移除高级统计配置
        
        self.logger.debug("Session reset")
        
    def is_active(self) -> bool:
        """Check if the session is currently active."""
        return self.active
        
    def get_current_balance(self) -> float:
        """Get the player's current balance."""
        return self.player.balance
        
    def get_total_spins(self) -> int:
        """Get the total number of spins played."""
        return self.stats.total_spins
        
    def get_session_duration(self) -> float:
        """Get the session duration in seconds."""
        if not self.sim_start_time:
            return 0.0
        end_time = self.sim_end_time if self.sim_end_time else time.time()
        return end_time - self.sim_start_time