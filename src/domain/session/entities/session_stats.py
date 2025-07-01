# src/domain/session/entities/session_stats.py
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class SessionStats:
    """简化的会话统计数据类，保持你原始的字段名。"""
    # 基本信息 - 完全按照你原来的字段
    session_id: str
    player_id: str
    machine_id: str
    sim_start_time: Optional[datetime] = None
    sim_end_time: Optional[datetime] = None
    sim_duration: float = 0.0
    active: bool = False
    
    # 基本统计数据 - 完全按照你原来的字段名
    total_spins: int = 0
    duration: float = 0.0
    win_count: int = 0
    win_rate: float = 0.0
    total_bet: float = 0.0
    total_win: float = 0.0
    total_profit: float = 0.0  # 你原来的字段名
    base_game_win: float = 0.0  # 你原来的字段名
    free_game_win: float = 0.0  # 你原来的字段名，不是free_spins_win
    return_to_player: float = 0.0  # 你原来的字段名
    bonus_triggered: bool = False
    free_spins_count: int = 0
    big_win_count: int = 0
    start_balance: Optional[float] = None
    end_balance: float = 0.0
    balance_change: float = 0.0
    batch_count: int = 0  # 你原来有这个字段
    
    def update_spin(self, bet_amount: float, win_amount: float, is_scatter_win: bool = False):
        """
        更新单次旋转的统计数据，保持你原来的逻辑。
        """
        self.total_spins += 1
        self.total_bet += bet_amount
        self.total_win += win_amount
        self.total_profit = self.total_win - self.total_bet  # 保持你原来的计算方式
        
        if win_amount > 0:
            self.win_count += 1
            
        # 更新胜率
        self.win_rate = self.win_count / self.total_spins if self.total_spins > 0 else 0.0
        
        # 更新RTP
        self.return_to_player = self.total_win / self.total_bet if self.total_bet > 0 else 0.0
        
        # 检查是否为大奖 (10倍投注以上)
        if win_amount >= bet_amount * 10:
            self.big_win_count += 1
        
    def to_dict(self, include_advanced: bool = False) -> Dict[str, Any]:
        """
        转换为字典格式，完全按照你原来的字段。
        
        Args:
            include_advanced: 保留为兼容性，但不再支持高级统计
            
        Returns:
            统计数据字典
        """
        # 完全按照你原来的get_statistics()逻辑
        stats = {attr: getattr(self, attr) for attr in dir(self) 
            if not attr.startswith("_") and not callable(getattr(self, attr))}

        stats["sim_start_time"] = self.sim_start_time.strftime('%Y-%m-%d %H:%M:%S') if self.sim_start_time else None
        stats["sim_end_time"] = self.sim_end_time.strftime('%Y-%m-%d %H:%M:%S') if self.sim_end_time else None
        
        return stats