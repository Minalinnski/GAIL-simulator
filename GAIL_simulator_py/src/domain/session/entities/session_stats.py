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
    # sim_start_time: Optional[datetime] = None
    # sim_end_time: Optional[datetime] = None
    # sim_duration: float = 0.0
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
    
    def update_spin(self, spin_result) -> None:
        """
        更新单次旋转的统计数据，接受SpinResult对象或者单独的参数。
        
        Args:
            spin_result: SpinResult对象，或者为了兼容性支持单独参数调用
        """
        # 检查是否是SpinResult对象
        if hasattr(spin_result, 'bet') and hasattr(spin_result, 'payout'):
            # 从SpinResult对象获取数据
            bet_amount = spin_result.bet
            win_amount = spin_result.payout
            is_scatter_win = getattr(spin_result, 'scatter_win', 0.0) > 0
            is_free_spin = getattr(spin_result, 'in_free_spins', False)
        else:
            # 为了兼容性，支持旧的调用方式（如果spin_result实际上是bet_amount）
            bet_amount = spin_result
            # 这种情况下需要额外的参数，但我们假设这是新的调用方式
            # 如果出现错误，说明调用方式不对
            raise ValueError("update_spin requires a SpinResult object")
        
        # 更新基本统计
        self.total_spins += 1
        self.total_bet += bet_amount
        self.total_win += win_amount
        self.total_profit = self.total_win - self.total_bet  # 保持原有的计算方式
        
        if win_amount > 0:
            self.win_count += 1
            
        # 更新胜率
        if self.total_spins > 0:
            self.win_rate = self.win_count / self.total_spins
        
        # 更新RTP
        if self.total_bet > 0:
            self.return_to_player = self.total_win / self.total_bet
        
        # 检查是否为大奖 (10倍投注以上)
        if win_amount >= bet_amount * 10:
            self.big_win_count += 1
        
        # 分类win金额
        if is_free_spin:
            self.free_game_win += win_amount
        else:
            self.base_game_win += win_amount
        
        # 如果是scatter触发的免费旋转
        if hasattr(spin_result, 'free_spins_triggered') and spin_result.free_spins_triggered:
            self.bonus_triggered = True
            self.free_spins_count += 1
        
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

        # stats["sim_start_time"] = self.sim_start_time.strftime('%Y-%m-%d %H:%M:%S') if self.sim_start_time else None
        # stats["sim_end_time"] = self.sim_end_time.strftime('%Y-%m-%d %H:%M:%S') if self.sim_end_time else None
        
        return stats