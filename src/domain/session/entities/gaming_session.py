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
        
        # 记录保留的常量配置（避免频繁调用output_manager）
        self.lru_max_size = 1000  # 默认值
        self.batch_size = 200     # 默认值
        self.should_record_spins = True  # 默认值
        self.record_advanced_stats = False  # 默认值
        
        # 从output_manager读取配置
        if output_manager:
            self.lru_max_size = output_manager.lru_max_size
            self.batch_size = output_manager.batch_size
            self.should_record_spins = output_manager.should_record_spins
            self.record_advanced_stats = output_manager.should_record_advanced_statistics
        
        # 初始化统计对象（所有统计数据都由它管理）
        self.stats = SessionStats(
            session_id=session_id,
            player_id=player.id,
            machine_id=machine.id
        )
        
        # 配置高级统计模块
        if self.record_advanced_stats:
            stats_config = self._get_stats_config()
            self.stats.configure_stats(stats_config)
        
        # Tracking data (non-statistical)
        self.spins = deque(maxlen=self.lru_max_size)  # LRU队列，限制内存使用
        self.balance_history = deque(maxlen=self.lru_max_size)  # LRU队列
        
        # 当前状态
        self.in_free_spins = False
        self.free_spins_remaining = 0
        self.free_spins_base_bet = 0.0
        
        # 批次处理
        self.batch_number = 0              # 当前批次编号
        self.result_batch = []             # 当前批次数据
        
        # 可用投注列表
        self.available_bets = []
        self._load_available_bets()
        
        # 常量定义
        self.NUM_TRACK_BACK = 10           # 记录追溯次数
        self.BIG_WIN_THRESHOLD = 10        # 大奖阈值
        
    def _get_stats_config(self) -> Dict[str, bool]:
        """从输出管理器配置中获取高级统计配置"""
        if not self.output_manager or not hasattr(self.output_manager, 'config'):
            return {}
            
        # 获取默认配置
        default_config = {
            "bet": True,        # 投注统计
            "payout": True,     # 赢额统计
            "profit": True,     # 净胜统计
            "odds": True,       # 赔率统计
            "balance": False    # 余额统计
        }
        
        # 从输出管理器配置中获取覆盖设置
        stats_config = self.output_manager.config.get("session_recording", {}).get(
            "advanced_statistics", {}).get("modules", {})
        
        # 合并配置
        for key, value in stats_config.items():
            if key in default_config:
                default_config[key] = value
                
        return default_config
        
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
        """开始游戏会话。"""
        if self.active:
            self.logger.warning("Attempted to start an already active session")
            return
            
        self.sim_start_time = time.time()
        self.active = True
        
        # 记录起始余额
        self.balance_history.append(self.player.balance)
        
        # 更新统计状态
        self.stats.sim_start_time = datetime.fromtimestamp(self.sim_start_time)
        self.stats.active = True
        self.stats.start_balance = self.player.balance
        
        # 初始化余额统计
        if self.record_advanced_stats and "balance" in self.stats._active_stats and self.stats.balance_stats:
            self.stats.balance_stats.update(self.player.balance)
        
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
            
        self.logger.info(f"Session started with balance {self.player.balance}")
        
    def end(self):
        """结束游戏会话。"""
        if not self.active:
            self.logger.warning("Attempted to end an inactive session")
            return
            
        self.sim_end_time = time.time()
        self.active = False
        
        # 确保将所有剩余结果写入文件
        if self.result_batch and self.output_manager:
            self._flush_batch()
        
        # 更新统计状态
        self.stats.sim_end_time = datetime.fromtimestamp(self.sim_end_time)
        self.stats.sim_duration = self.sim_end_time - self.sim_start_time
        self.stats.active = False
        self.stats.end_balance = self.player.balance
        self.stats.balance_change = self.player.balance - self.stats.start_balance if self.stats.start_balance is not None else 0
        self.stats.batch_count = self.batch_number
            
        # 派发会话结束事件
        if self.event_dispatcher:
            self.event_dispatcher.dispatch(SessionEvent(
                type=SessionEventType.SESSION_ENDED,
                session_id=self.id,
                player_id=self.player.id,
                machine_id=self.machine.id,
                data=self.get_statistics()
            ))
            
        # 写入会话摘要
        self._write_session_summary()
            
        self.logger.info(f"Session ended with {self.stats.total_spins} spins, " +
                       f"bet: {self.stats.total_bet}, payout: {self.stats.total_win}, " +
                       f"final balance: {self.player.balance}")
                       
    def execute_spin(self, bet_amount: float) -> Dict[str, Any]:
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
        self.stats.win_rate = self.stats.win_count / self.stats.total_spins if self.stats.total_spins > 0 else 0
        
        # 更新RTP和净利润
        self.stats.total_profit = self.stats.total_win - self.stats.total_bet
        self.stats.return_to_player = self.stats.total_win / self.stats.total_bet if self.stats.total_bet > 0 else 0
            
        # 检查大奖
        win_odds = win_amount / bet_amount if bet_amount > 0 else 0
        is_big_win = win_odds >= self.BIG_WIN_THRESHOLD
        if is_big_win:
            self.stats.big_win_count += 1
        
        # 更新免费旋转状态
        if trigger_free and not self.in_free_spins:
            self.in_free_spins = True
            self.stats.bonus_triggered = True
            self.free_spins_remaining = free_remaining
            self.free_spins_base_bet = bet_amount
            
            # 派发免费旋转触发事件
            if self.event_dispatcher:
                self.event_dispatcher.dispatch(SessionEvent(
                    type=SessionEventType.FREE_SPINS_TRIGGERED,
                    session_id=self.id,
                    player_id=self.player.id,
                    machine_id=self.machine.id,
                    data={
                        "base_bet": bet_amount,
                        "free_spins": free_remaining,
                        "multiplier": self.machine.free_spins_multiplier
                    }
                ))
        elif self.in_free_spins:
            self.free_spins_remaining = free_remaining
            if free_remaining <= 0:
                self.in_free_spins = False
                self.free_spins_base_bet = 0.0
        
        # 记录余额
        self.balance_history.append(self.player.balance)
        
        # 计算当前streak
        streak = 0
        if len(self.spins) > 0:
            prev_win = self.spins[-1].payout > 0
            curr_win = win_amount > 0
            if curr_win == prev_win:
                streak = self.spins[-1].streak
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
        
        # 添加到历史记录
        self.spins.append(spin_result)
        
        # 更新高级统计
        if self.record_advanced_stats:
            self.stats.add_spin_result(spin_result)
        
        if self.should_record_spins:
            # 添加到批处理队列
            result_dict = spin_result.to_dict()
            self.result_batch.append(result_dict)
            
            # 如果批处理队列已满，写入文件
            if self.output_manager and len(self.result_batch) >= self.batch_size:
                self._flush_batch()
        
        # 如果是大奖，记录日志
        if is_big_win:
            # 派发大奖事件
            if self.event_dispatcher:
                self.event_dispatcher.dispatch(SessionEvent(
                    type=SessionEventType.BIG_WIN,
                    session_id=self.id,
                    player_id=self.player.id,
                    machine_id=self.machine.id,
                    data={
                        "bet": bet_amount,
                        "payout": win_amount,
                        "odds": win_odds
                    }
                ))
                
            self.logger.info(f"Big win! {win_amount} (x{win_amount/bet_amount:.1f})")
        
        self.logger.debug(
            f"Spin result: bet={bet_amount}, payout={win_amount}, " +
            f"balance={self.player.balance}, " + 
            f"free_spins={'active' if self.in_free_spins else 'inactive'}, " +
            f"remaining={self.free_spins_remaining}"
        )
        
        # 转换为字典格式
        result_dict = spin_result.to_dict()
        # 添加win_data便于其他组件使用
        result_dict["win_data"] = win_data
            
        return result_dict

    def _flush_batch(self):
        """将当前批次写入文件，并清除批次数据。"""
        if not self.result_batch or not self.output_manager:
            return
            
        self.batch_number += 1
        self.output_manager.write_spin_batch(
            self.id, 
            self.result_batch.copy(), 
            self.batch_number
        )
        
        # 清空批次
        self.result_batch = []
        
    def _write_session_summary(self):
        """写入会话摘要。"""
        if not self.output_manager:
            return
            
        stats = self.get_statistics()
        self.output_manager.write_session_summary(self.id, stats)
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取会话统计数据。
        
        Returns:
            包含会话统计信息的字典
        """
        # 使用SessionStats的to_dict方法获取统计数据
        # 根据是否启用高级统计决定是否包含高级统计数据
        return self.stats.to_dict(include_advanced=self.record_advanced_stats)
        
    def get_data_for_decision(self) -> Dict[str, Any]:
        """
        Get session data formatted for player decision-making.
        
        Returns:
            Dictionary with session data for player decisions
        """
        current_time = time.time()
        
        # 基本会话数据
        session_data = {
            "session_id": self.id,
            "machine_id": self.machine.id,
            "start_time": self.sim_start_time,
            "current_time": current_time,
            "duration": current_time - self.sim_start_time if self.sim_start_time else 0,
            "start_balance": self.balance_history[0] if self.balance_history else self.player.balance,
            "current_balance": self.player.balance,
            "total_spins": self.stats.total_spins,
            "win_count": self.stats.win_count,
            "total_bet": self.stats.total_bet,
            "total_win": self.stats.total_win,
            "total_profit": self.stats.total_profit,
            "available_bets": self.available_bets,
            "currency": self.player.currency,
            "in_free_spins": self.in_free_spins,
            "free_spins_remaining": self.free_spins_remaining,
            "bonus_triggered": self.stats.bonus_triggered
        }
        
        # 添加最近的旋转结果（最多NUM_TRACK_BACK个）
        recent_results = []
        spins_list = list(self.spins)
        for spin in spins_list[-self.NUM_TRACK_BACK:]:
            recent_results.append(spin.to_dict())
        session_data["results"] = recent_results
        
        return session_data
        
    def reset(self):
        """重置会话状态以进行新的模拟运行。"""
        self.sim_start_time = None
        self.sim_end_time = None
        self.active = False
        self.spins.clear()
        self.balance_history.clear()
        self.in_free_spins = False
        self.free_spins_remaining = 0
        self.free_spins_base_bet = 0.0
        self.result_batch = []
        self.batch_number = 0
        
        # 重置统计对象
        self.stats = SessionStats(
            session_id=self.id,
            player_id=self.player.id,
            machine_id=self.machine.id
        )
        
        # 重新配置高级统计模块
        if self.record_advanced_stats:
            stats_config = self._get_stats_config()
            self.stats.configure_stats(stats_config)
        
        self.logger.debug("Session reset")