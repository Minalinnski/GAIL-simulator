# src/domain/session/entities/session_stats.py
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from .incremental_stats import IncrementalStats

@dataclass
class SessionStats:
    """实体类，记录会话统计数据，使用懒加载方式创建实际需要的统计对象。"""
    # 基本信息
    session_id: str
    player_id: str
    machine_id: str
    sim_start_time: Optional[datetime] = None
    sim_end_time: Optional[datetime] = None
    sim_duration: float = 0.0
    active: bool = False
    
    # 基本统计数据
    total_spins: int = 0
    duration: float = 0.0
    win_count: int = 0
    win_rate: float = 0.0
    total_bet: float = 0.0
    total_win: float = 0.0  # 总赢额
    total_profit: float = 0.0  # 净胜额(payout-bet)
    base_game_win: float = 0.0  # 常规游戏赢额
    free_game_win: float = 0.0  # 免费旋转赢额
    return_to_player: float = 0.0  # RTP比率(payout/bet)
    bonus_triggered: bool = False
    free_spins_count: int = 0
    big_win_count: int = 0
    start_balance: Optional[float] = None
    end_balance: float = 0.0
    balance_change: float = 0.0
    batch_count: int = 0
    
    # 高级统计配置和存储
    _stats_config: Dict[str, bool] = field(default_factory=dict)
    _stats_objects: Dict[str, Any] = field(default_factory=dict)
    _active_stats: Set[str] = field(default_factory=set)
    
    def configure_stats(self, config: Dict[str, bool]) -> None:
        """配置需要激活的统计模块"""
        self._stats_config.update(config)
        
    def _get_stats_object(self, key: str):
        """获取或创建指定类型的统计对象(懒加载)"""
        # 检查是否启用该统计类型
        if not self._stats_config.get(key, False):
            return None
            
        # 如果已创建，直接返回
        if key in self._stats_objects:
            return self._stats_objects[key]
            
        # 否则，创建新的统计对象
        stats_obj = IncrementalStats()
        self._stats_objects[key] = stats_obj
        self._active_stats.add(key)
        return stats_obj
    
    def add_spin_result(self, result) -> None:
        """添加旋转结果数据用于统计计算"""
        # 提取数据
        bet_amount = result.bet
        payout_amount = result.payout
        profit = result.profit
        odds = result.odds
        
        # 更新各类统计
        for stat_type in self._stats_config:
            if self._stats_config[stat_type]:
                stats_obj = self._get_stats_object(stat_type)
                if stats_obj:
                    if stat_type == "bet":
                        stats_obj.update(bet_amount)
                    elif stat_type == "payout":
                        stats_obj.update(payout_amount)
                    elif stat_type == "profit":
                        stats_obj.update(profit)
                    elif stat_type == "odds" and bet_amount > 0:
                        stats_obj.update(odds)
                    elif stat_type == "balance":
                        stats_obj.update(result.balance_after)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取基本统计数据字典"""
        stats = {attr: getattr(self, attr) for attr in dir(self) 
            if not attr.startswith("_") and not callable(getattr(self, attr))}

        stats["sim_start_time"] = self.sim_start_time.strftime('%Y-%m-%d %H:%M:%S') if self.sim_start_time else None
        stats["sim_end_time"] = self.sim_end_time.strftime('%Y-%m-%d %H:%M:%S') if self.sim_end_time else None

        # stats = {
        #     "session_id": self.session_id,
        #     "player_id": self.player_id,
        #     "machine_id": self.machine_id,
        #     "sim_start_time": sim_start_time_str,
        #     "sim_end_time": sim_end_time_str,
        #     "sim_duration": self.sim_duration,
        #     "active": self.active,
        #     "total_spins": self.total_spins,
        #     "duration": self.duration,
        #     "win_count": self.win_count,
        #     "win_rate": self.win_rate,
        #     "total_bet": self.total_bet,
        #     "total_win": self.total_win,
        #     "total_profit": self.total_profit,
        #     "base_game_win": self.base_game_win,
        #     "free_game_win": self.free_game_win,
        #     "return_to_player": self.return_to_player,
        #     "bonus_triggered": self.bonus_triggered,
        #     "free_spins_count": self.free_spins_count,
        #     "big_win_count": self.big_win_count,
        #     "start_balance": self.start_balance,
        #     "end_balance": self.end_balance,
        #     "balance_change": self.balance_change,
        #     "batch_count": self.batch_count
        # }
        
        return stats
    
    def get_advanced_statistics(self) -> Dict[str, Any]:
        """获取高级统计数据字典"""
        advanced_stats = {}
        
        # 遍历所有激活的统计模块
        for stat_type in self._active_stats:
            stats_obj = self._stats_objects.get(stat_type)
            if stats_obj:
                advanced_stats[f"{stat_type}_statistics"] = stats_obj.to_dict()
                
        return advanced_stats
    
    def to_dict(self, include_advanced: bool = True) -> Dict[str, Any]:
        """
        转换为字典格式，方便存储或传输
        
        Args:
            include_advanced: 是否包含高级统计数据
        """
        basic_stats = self.get_statistics()
        
        if include_advanced:
            # 合并高级统计
            advanced_stats = self.get_advanced_statistics()
            return {**basic_stats, **advanced_stats}
        else:
            return basic_stats