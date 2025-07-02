# src/domain/session/entities/spin_result.py
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import time


@dataclass
class SpinResult:
    """
    实体类，记录单次旋转的详细结果。
    用于跟踪历史数据并支持模型训练。
    """
    # 基本信息
    session_id: str
    spin_number: int
    timestamp: float = field(default_factory=time.time)
    
    # 投注和结果
    bet: float = 0.0
    payout: float = 0.0
    profit: float = 0.0  # win - bet
    odds: float = 0.0    # win / bet
    balance_before: float = 0.0
    balance_after: float = 0.0
    
    # 游戏状态
    result_grid: List[int] = field(default_factory=list)
    in_free_spins: bool = False
    free_spins_triggered: bool = False
    free_spins_remaining: int = 0
    free_spins_base_bet: float = 0.0
    
    # 赢线信息
    line_wins: List[float] = field(default_factory=list)
    line_wins_info: List[Dict[str, Any]] = field(default_factory=list)
    scatter_win: float = 0.0
    
    # 用于分析的辅助字段
    streak: int = 0  # 连续输赢的计数（正数=连赢，负数=连输）
    big_win: bool = False  # 标记大奖
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，方便存储或传输。"""
        # return {
        #     "session_id": self.session_id,
        #     "spin_number": self.spin_number,
        #     "timestamp": self.timestamp,
        #     "bet": self.bet,
        #     "payout": self.payout,
        #     "profit": self.profit,
        #     "odds": self.odds,
        #     "balance_before": self.balance_before,
        #     "balance_after": self.balance_after,
        #     "result_grid": self.result_grid,
        #     "in_free_spins": self.in_free_spins,
        #     "free_spins_triggered": self.free_spins_triggered,
        #     "free_spins_remaining": self.free_spins_remaining,
        #     "free_spins_base_bet": self.free_spins_base_bet,
        #     "line_wins": self.line_wins,
        #     "line_wins_info": self.line_wins_info,
        #     "scatter_win": self.scatter_win,
        #     "streak": self.streak,
        #     "big_win": self.big_win
        # }
        return {attr: getattr(self, attr) for attr in dir(self) 
            if not attr.startswith("__") and not callable(getattr(self, attr))}