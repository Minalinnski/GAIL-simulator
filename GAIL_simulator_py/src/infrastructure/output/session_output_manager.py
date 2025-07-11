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
            # 保存原始spin数据到raw_data目录
            if self.should_record_spins and session.spins:
                self._save_raw_spins_data(session)
            
            # 保存session摘要到temp_summaries目录
            self._save_session_summary_to_temp(session)
            
            self.logger.debug(f"Session data saved for {self.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
            return False
    
    def _save_raw_spins_data(self, session) -> Optional[str]:
        """
        保存原始spins数据到CSV，直接使用spins中的字典数据
        
        Args:
            session: GamingSession实例
            
        Returns:
            保存的文件路径或S3相对路径
        """
        if not self.should_record_spins or not session.spins:
            return None
            
        try:
            # 解析player_id和machine_id
            player_id = session.player.id
            machine_id = session.machine.id
            
            # 获取所有字段名（从第一个spin获取）
            if not session.spins:
                return None
                
            first_spin = session.spins[0]
            if isinstance(first_spin, dict):
                csv_fields = list(first_spin.keys())
            else:
                # 如果是对象，使用to_dict()方法
                csv_fields = list(first_spin.to_dict().keys()) if hasattr(first_spin, 'to_dict') else []
            
            # 如果使用S3，直接上传而不保存本地文件
            if self.base_output_manager.s3:
                # 构造S3路径（包含task_dir名称）
                task_dir_name = os.path.basename(self.base_output_manager.task_dir)
                s3_rel_path = f"{task_dir_name}/{player_id}/{machine_id}/raw_data/{self.session_id}_raw.csv"
                
                # 创建CSV内容
                import io
                csv_content = io.StringIO()
                writer = csv.DictWriter(csv_content, fieldnames=csv_fields)
                writer.writeheader()
                
                for spin in session.spins:
                    # 处理数据格式
                    if isinstance(spin, dict):
                        row_data = spin.copy()
                    else:
                        row_data = spin.to_dict() if hasattr(spin, 'to_dict') else {}
                    
                    # 处理复杂字段（如列表、字典）转为JSON字符串
                    for field in csv_fields:
                        value = row_data.get(field, '')
                        if isinstance(value, (list, dict)):
                            row_data[field] = json.dumps(value, ensure_ascii=False)
                    
                    writer.writerow(row_data)
                
                # 上传到S3
                csv_bytes = csv_content.getvalue().encode('utf-8')
                self.base_output_manager.s3.upload_bytes(csv_bytes, s3_rel_path)
                self.logger.debug(f"Raw spins data uploaded to S3: {s3_rel_path}")
                
                return s3_rel_path
            
            else:
                # 本地存储
                # 获取cluster/table/raw_data目录
                raw_data_dir = self.base_output_manager.get_cluster_table_directory(
                    player_id, machine_id, "raw_data"
                )
                
                # 使用session_id作为文件名
                filename = f"{self.session_id}_raw.csv"
                filepath = os.path.join(raw_data_dir, filename)
                
                # 写入CSV数据
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=csv_fields)
                    writer.writeheader()
                    
                    for spin in session.spins:
                        # 处理数据格式
                        if isinstance(spin, dict):
                            row_data = spin.copy()
                        else:
                            row_data = spin.to_dict() if hasattr(spin, 'to_dict') else {}
                        
                        # 处理复杂字段（如列表、字典）转为JSON字符串
                        for field in csv_fields:
                            value = row_data.get(field, '')
                            if isinstance(value, (list, dict)):
                                row_data[field] = json.dumps(value, ensure_ascii=False)
                        
                        writer.writerow(row_data)
                
                self.logger.debug(f"Raw spins data saved to: {filepath}")
                return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save raw spins data: {e}")
            return None
    
    def _save_session_summary_to_temp(self, session) -> Optional[str]:
        """
        保存session摘要数据到临时目录
        
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
                # TODO session id？
                "session_id": (lambda x: x.split("_")[-1] if "_" in x else x)(self.session_id) if self.session_id else self.session_id,
                "player_id": session.player.id,
                "machine_id": session.machine.id,
                "initial_balance": session.get_initial_balance(),
                "final_balance": session.get_current_balance(),
                "first_bet": session.get_first_bet(),
                "sim_duration": session.get_sim_duration(),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 获取临时目录
            temp_dir = self.base_output_manager.get_temp_summary_directory()
            
            # 使用session_id作为文件名
            filename = f"{self.session_id}_summary.json"
            filepath = os.path.join(temp_dir, filename)
            
            # 写入JSON数据
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(summary_data, jsonfile, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Session summary saved to temp: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save session summary: {e}")
            return None
    
    def cleanup_temp_files(self) -> None:
        """
        清理临时文件
        """
        try:
            self.logger.debug(f"Temp files cleanup completed for {self.session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup temp files: {e}")