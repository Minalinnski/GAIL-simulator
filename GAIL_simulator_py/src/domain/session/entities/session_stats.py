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
    
    # 统一字段名：使用 initial_balance 和 final_balance
    initial_balance: Optional[float] = None
    final_balance: float = 0.0
    
    balance_change: float = 0.0
    # batch_count: int = 0  # 你原来有这个字段
    
    # 为了兼容性，保留旧字段名的属性访问
    @property
    def start_balance(self) -> Optional[float]:
        """兼容性属性：映射到 initial_balance"""
        return self.initial_balance
    
    @start_balance.setter
    def start_balance(self, value: Optional[float]):
        """兼容性属性：映射到 initial_balance"""
        self.initial_balance = value
    
    @property
    def end_balance(self) -> float:
        """兼容性属性：映射到 final_balance"""
        return self.final_balance
    
    @end_balance.setter
    def end_balance(self, value: float):
        """兼容性属性：映射到 final_balance"""
        self.final_balance = value
    
    def update_spin(self, spin_result) -> None:
        """
        更新单次旋转的统计数据，接受SpinResult对象。
        
        Args:
            spin_result: SpinResult对象
        """
        if not (hasattr(spin_result, 'bet') and hasattr(spin_result, 'payout')):
            raise ValueError("update_spin requires a SpinResult object with 'bet' and 'payout' attributes")
        
        bet_amount = spin_result.bet
        win_amount = spin_result.payout
        is_free_spin = getattr(spin_result, 'in_free_spins', False)
        
        # 更新基本统计
        self.total_spins += 1
        
        # 只有非免费旋转才计入total_bet
        if not is_free_spin:
            self.total_bet += bet_amount
        
        self.total_win += win_amount
        self.total_profit = self.total_win - self.total_bet
        
        if win_amount > 0:
            self.win_count += 1
        
        # 更新胜率
        if self.total_spins > 0:
            self.win_rate = self.win_count / self.total_spins
        
        # 更新RTP
        if self.total_bet > 0:
            self.return_to_player = self.total_win / self.total_bet
        
        # 检查是否为大奖
        if bet_amount > 0 and win_amount >= bet_amount * 10:
            self.big_win_count += 1
        
        # 分类win金额
        if is_free_spin:
            self.free_game_win += win_amount
            self.free_spins_count += 1
        else:
            self.base_game_win += win_amount
        
        # 检查免费旋转触发
        if hasattr(spin_result, 'free_spins_triggered') and spin_result.free_spins_triggered:
            self.bonus_triggered = True
        
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

        # 移除兼容性属性，避免重复
        if 'start_balance' in stats:
            del stats['start_balance']
        if 'end_balance' in stats:
            del stats['end_balance']
        
        return stats