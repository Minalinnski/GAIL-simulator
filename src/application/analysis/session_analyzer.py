# src/application/analysis/session_analyzer.py
import logging
import statistics
from typing import Dict, List, Any, Optional, Tuple


class SessionAnalyzer:
    """
    分析会话数据，计算统计指标，并识别模式。
    
    这个类处理单个会话和会话集合的分析，提供详细的指标和摘要。
    """
    def __init__(self):
        """初始化会话分析器。"""
        self.logger = logging.getLogger("application.analysis.session")
        
    def analyze_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单个会话的数据。
        
        Args:
            session_data: 会话数据字典
            
        Returns:
            会话分析结果
        """
        self.logger.debug(f"Analyzing session {session_data.get('session_id', 'unknown')}")
        
        # 提取基本数据
        session_id = session_data.get("session_id", "unknown")
        player_id = session_data.get("player_id", "unknown")
        machine_id = session_data.get("machine_id", "unknown")
        
        # 提取游戏指标
        total_spins = session_data.get("total_spins", 0)
        total_bet = session_data.get("total_bet", 0.0)
        total_win = session_data.get("total_win", 0.0)
        base_game_win = session_data.get("base_game_win", 0.0)
        free_spins_win = session_data.get("free_spins_win", 0.0)
        
        # 计算派生指标
        rtp = total_win / total_bet if total_bet > 0 else 0.0
        base_game_rtp = base_game_win / total_bet if total_bet > 0 else 0.0
        free_spins_rtp = free_spins_win / total_bet if total_bet > 0 else 0.0
        
        # 如果有详细的旋转数据，计算波动指标
        spin_results = session_data.get("results", [])
        volatility_metrics = self._calculate_volatility_metrics(spin_results) if spin_results else {}
        
        # 创建分析结果
        analysis = {
            "session_id": session_id,
            "player_id": player_id,
            "machine_id": machine_id,
            "performance": {
                "total_spins": total_spins,
                "total_bet": total_bet,
                "total_win": total_win,
                "net_result": total_win - total_bet,
                "rtp": rtp,
                "hit_rate": session_data.get("win_count", 0) / total_spins if total_spins > 0 else 0.0
            },
            "game_breakdown": {
                "base_game_win": base_game_win,
                "free_spins_win": free_spins_win,
                "base_game_rtp": base_game_rtp,
                "free_spins_rtp": free_spins_rtp,
                "base_game_contribution": base_game_win / total_win if total_win > 0 else 0.0,
                "free_spins_contribution": free_spins_win / total_win if total_win > 0 else 0.0,
                "free_spins_count": session_data.get("free_spins_count", 0),
                "big_win_count": session_data.get("big_win_count", 0)
            },
            "player_behavior": {
                "duration": session_data.get("duration", 0.0),
                "avg_bet": total_bet / total_spins if total_spins > 0 else 0.0,
                "bet_progression": self._analyze_bet_progression(spin_results),
                "quit_balance": session_data.get("end_balance", 0.0),
                "balance_change_percent": self._calculate_balance_change_percent(session_data)
            },
            "volatility": volatility_metrics
        }
        
        self.logger.debug(f"Completed analysis for session {session_id}")
        return analysis
        
    def analyze_sessions(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析多个会话的数据，生成聚合报告。
        
        Args:
            sessions: 会话数据列表
            
        Returns:
            会话分析聚合结果
        """
        self.logger.info(f"Analyzing {len(sessions)} sessions")
        
        # 分析每个会话
        session_analyses = [self.analyze_session(session) for session in sessions]
        
        # 按玩家和机器分组
        player_sessions = {}
        machine_sessions = {}
        
        for analysis in session_analyses:
            player_id = analysis["player_id"]
            machine_id = analysis["machine_id"]
            
            if player_id not in player_sessions:
                player_sessions[player_id] = []
            player_sessions[player_id].append(analysis)
            
            if machine_id not in machine_sessions:
                machine_sessions[machine_id] = []
            machine_sessions[machine_id].append(analysis)
        
        # 计算聚合指标
        return {
            "overall_metrics": self._calculate_overall_metrics(session_analyses),
            "player_metrics": {
                player_id: self._calculate_player_metrics(sessions)
                for player_id, sessions in player_sessions.items()
            },
            "machine_metrics": {
                machine_id: self._calculate_machine_metrics(sessions)
                for machine_id, sessions in machine_sessions.items()
            },
            "session_count": len(sessions),
            "player_count": len(player_sessions),
            "machine_count": len(machine_sessions)
        }
        
    def _calculate_volatility_metrics(self, spin_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算会话的波动性指标。
        
        Args:
            spin_results: 旋转结果列表
            
        Returns:
            波动性指标字典
        """
        if not spin_results:
            return {}
            
        # 提取每次旋转的输赢值
        profits = []
        win_sizes = []
        balance_progression = []
        
        for result in spin_results:
            bet = result.get("bet", 0.0)
            win = result.get("win", 0.0)
            profit = win - bet
            
            profits.append(profit)
            if win > 0:
                win_sizes.append(win / bet if bet > 0 else 0.0)  # 赢额与投注的比例
                
            balance_progression.append(result.get("balance_after", 0.0))
        
        # 计算波动性指标
        try:
            profit_std_dev = statistics.stdev(profits) if len(profits) > 1 else 0.0
            max_win_multiplier = max(win_sizes) if win_sizes else 0.0
            
            # 计算余额最大回撤
            max_drawdown = 0.0
            peak_balance = balance_progression[0] if balance_progression else 0.0
            
            for balance in balance_progression:
                if balance > peak_balance:
                    peak_balance = balance
                else:
                    drawdown = peak_balance - balance
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
            
            return {
                "profit_std_dev": profit_std_dev,
                "max_win_multiplier": max_win_multiplier,
                "max_drawdown": max_drawdown,
                "max_drawdown_percent": max_drawdown / peak_balance if peak_balance > 0 else 0.0,
                "win_frequency": len(win_sizes) / len(spin_results)
            }
        except Exception as e:
            self.logger.error(f"Error calculating volatility metrics: {str(e)}")
            return {}
            
    def _analyze_bet_progression(self, spin_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析玩家的投注进展。
        
        Args:
            spin_results: 旋转结果列表
            
        Returns:
            投注进展分析
        """
        if not spin_results:
            return {}
            
        # 提取投注额
        bets = [result.get("bet", 0.0) for result in spin_results]
        
        # 识别投注模式
        bet_changes = sum(1 for i in range(1, len(bets)) if bets[i] != bets[i-1])
        
        # 最大和最小投注
        max_bet = max(bets) if bets else 0.0
        min_bet = min(bets) if bets else 0.0
        
        return {
            "bet_change_count": bet_changes,
            "bet_change_frequency": bet_changes / (len(bets) - 1) if len(bets) > 1 else 0.0,
            "max_bet": max_bet,
            "min_bet": min_bet,
            "bet_range": max_bet - min_bet,
            "last_bet": bets[-1] if bets else 0.0
        }
        
    def _calculate_balance_change_percent(self, session_data: Dict[str, Any]) -> float:
        """
        计算余额变动百分比。
        
        Args:
            session_data: 会话数据
            
        Returns:
            余额变动百分比
        """
        start_balance = session_data.get("start_balance", 0.0)
        end_balance = session_data.get("end_balance", 0.0)
        
        if start_balance <= 0:
            return 0.0
            
        return (end_balance - start_balance) / start_balance
        
    def _calculate_overall_metrics(self, session_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算所有会话的整体指标。
        
        Args:
            session_analyses: 会话分析列表
            
        Returns:
            整体指标
        """
        # 提取关键指标
        total_spins = sum(a["performance"]["total_spins"] for a in session_analyses)
        total_bet = sum(a["performance"]["total_bet"] for a in session_analyses)
        total_win = sum(a["performance"]["total_win"] for a in session_analyses)
        base_game_win = sum(a["game_breakdown"]["base_game_win"] for a in session_analyses)
        free_spins_win = sum(a["game_breakdown"]["free_spins_win"] for a in session_analyses)
        durations = [a["player_behavior"]["duration"] for a in session_analyses]
        
        # 计算平均值
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        return {
            "total_spins": total_spins,
            "total_bet": total_bet,
            "total_win": total_win,
            "rtp": total_win / total_bet if total_bet > 0 else 0.0,
            "base_game_rtp": base_game_win / total_bet if total_bet > 0 else 0.0,
            "free_spins_rtp": free_spins_win / total_bet if total_bet > 0 else 0.0,
            "avg_session_duration": avg_duration,
            "net_result": total_win - total_bet
        }
        
    def _calculate_player_metrics(self, session_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算玩家在多个会话中的聚合指标。
        
        Args:
            session_analyses: 会话分析列表
            
        Returns:
            玩家指标
        """
        # 提取关键指标
        total_spins = sum(a["performance"]["total_spins"] for a in session_analyses)
        total_bet = sum(a["performance"]["total_bet"] for a in session_analyses)
        total_win = sum(a["performance"]["total_win"] for a in session_analyses)
        durations = [a["player_behavior"]["duration"] for a in session_analyses]
        
        # 计算投注偏好
        bets = []
        for a in session_analyses:
            # 假设所有旋转历史都可用
            if a.get("player_behavior", {}).get("avg_bet", 0) > 0:
                bets.append(a["player_behavior"]["avg_bet"])
                
        avg_bet = sum(bets) / len(bets) if bets else 0.0
        
        return {
            "total_spins": total_spins,
            "total_bet": total_bet,
            "total_win": total_win,
            "rtp": total_win / total_bet if total_bet > 0 else 0.0,
            "avg_session_duration": sum(durations) / len(durations) if durations else 0.0,
            "avg_bet": avg_bet,
            "session_count": len(session_analyses),
            "net_result": total_win - total_bet
        }
        
    def _calculate_machine_metrics(self, session_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算机器在多个会话中的聚合指标。
        
        Args:
            session_analyses: 会话分析列表
            
        Returns:
            机器指标
        """
        # 提取关键指标
        total_spins = sum(a["performance"]["total_spins"] for a in session_analyses)
        total_bet = sum(a["performance"]["total_bet"] for a in session_analyses)
        total_win = sum(a["performance"]["total_win"] for a in session_analyses)
        base_game_win = sum(a["game_breakdown"]["base_game_win"] for a in session_analyses)
        free_spins_win = sum(a["game_breakdown"]["free_spins_win"] for a in session_analyses)
        free_spins_counts = [a["game_breakdown"]["free_spins_count"] for a in session_analyses]
        big_win_counts = [a["game_breakdown"]["big_win_count"] for a in session_analyses]
        
        # 计算RTP和贡献率
        rtp = total_win / total_bet if total_bet > 0 else 0.0
        base_rtp = base_game_win / total_bet if total_bet > 0 else 0.0
        free_rtp = free_spins_win / total_bet if total_bet > 0 else 0.0
        
        # 波动性指标（合并所有会话）
        max_win_multipliers = []
        for a in session_analyses:
            if "volatility" in a and "max_win_multiplier" in a["volatility"]:
                max_win_multipliers.append(a["volatility"]["max_win_multiplier"])
                
        max_win = max(max_win_multipliers) if max_win_multipliers else 0.0
        
        return {
            "total_spins": total_spins,
            "total_bet": total_bet,
            "total_win": total_win,
            "rtp": rtp,
            "base_game_rtp": base_rtp,
            "free_spins_rtp": free_rtp,
            "base_game_contribution": base_game_win / total_win if total_win > 0 else 0.0,
            "free_spins_contribution": free_spins_win / total_win if total_win > 0 else 0.0,
            "free_spins_frequency": sum(free_spins_counts) / total_spins if total_spins > 0 else 0.0,
            "big_win_frequency": sum(big_win_counts) / total_spins if total_spins > 0 else 0.0,
            "max_win_multiplier": max_win,
            "session_count": len(session_analyses)
        }