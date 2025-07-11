# src/infrastructure/output/session_output_manager.py
import os
import json
import csv
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime


class SessionOutputManager:
    """
    Session级别的独立输出管理器。
    每个Session有自己的输出管理器实例，避免文件写入冲突。
    """
    def __init__(self, session_id: str, base_output_manager, config: Optional[Dict[str, Any]] = None):
        """
        初始化Session级输出管理器
        
        Args:
            session_id: 会话ID
            base_output_manager: 基础输出管理器实例
            config: 可选的session级配置
        """
        self.session_id = session_id
        self.base_output_manager = base_output_manager
        self.logger = logging.getLogger(f"infrastructure.output.session.{session_id}")
        
        # Session级配置
        self.config = config or {}
        self.should_record_spins = self.config.get("record_spins", True)
        
        # 独立的临时文件路径（避免冲突）
        self.temp_file_prefix = f"{session_id}_{uuid.uuid4().hex[:8]}"
        
        self.logger.debug(f"SessionOutputManager initialized for {session_id}")
    
    def save_session_data(self, session) -> bool:
        """
        保存完整的session数据（raw + summary）
        
        Args:
            session: GamingSession实例
            
        Returns:
            是否保存成功
        """
        try:
            # 保存原始spin数据
            if self.should_record_spins and session.spins:
                self._save_raw_spins_data(session)
            
            # 保存session摘要
            self._save_session_summary(session)
            
            self.logger.debug(f"Session data saved for {self.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
            return False
    
    def _save_raw_spins_data(self, session) -> Optional[str]:
        """
        保存原始spins数据到CSV
        
        Args:
            session: GamingSession实例
            
        Returns:
            保存的文件路径或None
        """
        if not self.should_record_spins or not session.spins:
            return None
            
        try:
            # 解析player_id和machine_id
            player_id = session.player.id
            machine_id = session.machine.id
            
            # 获取cluster/table/raw_data目录
            raw_data_dir = self.base_output_manager.get_cluster_table_directory(
                player_id, machine_id, "raw_data"
            )
            
            # 创建独立的临时文件名
            filename = f"{self.temp_file_prefix}_raw.csv"
            filepath = os.path.join(raw_data_dir, filename)
            
            # 写入CSV数据
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # 写入标题行 - 使用正确的字段名
                headers = [
                    'session_id', 'spin_number', 'bet', 'payout', 'profit',
                    'balance_after', 'in_free_spins', 'free_spins_triggered',
                    'symbols', 'winning_lines', 'timestamp'
                ]
                writer.writerow(headers)
                
                # 写入数据行 - 使用正确的字段名
                for spin in session.spins:
                    row = [
                        self.session_id,
                        spin.spin_number,
                        spin.bet,  # 修正：使用 bet 而不是 bet_amount
                        spin.payout,  # 修正：使用 payout 而不是 win_amount
                        spin.profit,
                        spin.balance_after,
                        spin.in_free_spins,
                        spin.free_spins_triggered,  # 修正：使用 free_spins_triggered 而不是 trigger_free_spins
                        json.dumps(spin.result_grid) if spin.result_grid else '',  # 修正：使用 result_grid 而不是 symbols
                        json.dumps(spin.line_wins_info) if spin.line_wins_info else '',  # 修正：使用 line_wins_info 而不是 winning_lines
                        spin.timestamp
                    ]
                    writer.writerow(row)
            
            self.logger.debug(f"Raw spins data saved to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save raw spins data: {e}")
            return None
    
    def _save_session_summary(self, session) -> Optional[str]:
        """
        保存session摘要数据
        
        Args:
            session: GamingSession实例
            
        Returns:
            保存的文件路径或None
        """
        try:
            # 获取session统计摘要
            summary_data = session.get_session_summary()
            
            # 添加session级别的额外信息
            summary_data.update({
                "session_id": self.session_id,
                "player_id": session.player.id,
                "machine_id": session.machine.id,
                "initial_balance": session.get_initial_balance(),
                "final_balance": session.get_current_balance(),
                "first_bet": session.get_first_bet(),
                "session_duration": session.get_session_duration(),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 解析player_id和machine_id
            player_id = session.player.id
            machine_id = session.machine.id
            
            # 获取cluster/table/summary目录
            summary_dir = self.base_output_manager.get_cluster_table_directory(
                player_id, machine_id, "summary"
            )
            
            # 创建独立的临时文件名
            filename = f"{self.temp_file_prefix}_summary.json"
            filepath = os.path.join(summary_dir, filename)
            
            # 写入JSON数据
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(summary_data, jsonfile, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Session summary saved to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save session summary: {e}")
            return None
    
    def write_session_csv_row(self, data: Dict[str, Any], csv_file_path: str) -> bool:
        """
        写入单行数据到CSV文件（用于批量合并）
        
        Args:
            data: 要写入的数据行
            csv_file_path: CSV文件路径
            
        Returns:
            是否写入成功
        """
        try:
            file_exists = os.path.exists(csv_file_path)
            
            with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=data.keys())
                
                # 如果文件不存在，写入标题行
                if not file_exists:
                    writer.writeheader()
                
                # 写入数据行
                writer.writerow(data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write CSV row: {e}")
            return False
    
    def cleanup_temp_files(self) -> None:
        """
        清理临时文件
        """
        try:
            # 这里可以实现临时文件清理逻辑
            # 由于使用了独立的文件名前缀，通常不需要特别清理
            self.logger.debug(f"Temp files cleanup completed for {self.session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup temp files: {e}")
    
    def get_temp_file_path(self, suffix: str = "") -> str:
        """
        获取临时文件路径
        
        Args:
            suffix: 文件后缀
            
        Returns:
            临时文件路径
        """
        if not self.base_output_manager.initialized:
            self.base_output_manager.initialize()
            
        temp_dir = self.base_output_manager.get_temp_summary_directory()
        filename = f"{self.temp_file_prefix}{suffix}"
        return os.path.join(temp_dir, filename)