# src/infrastructure/output/output_manager.py

import os
import json
import time
import logging
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional, IO, Tuple

from .s3_service import S3Service

class OutputManager:
    """
    集中管理模拟器的输出操作，处理文件结构、配置和数据写入。
    
    负责:
    - 按cluster/table两层目录组织文件
    - raw data和summary分别存放
    - 提供统一的文件写入接口
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化输出管理器。"""
        self.logger = logging.getLogger("infrastructure.output.manager")
        
        # 默认配置
        default_config = {
            "directories": {
                "base_dir": "results",
                "use_simulation_subdir": True,
                "simulation_dir_format": "sim_{timestamp}",
                "timestamp_format": "%Y%m%d-%H%M%S",
            },
            "s3":{
                "use_s3": False,
                "bucket": "bituslabs-team-ai",  # S3 Bucket 名称
                "region": "us-west-2",        # Bucket 所在区域
                "prefix": "gail_simulator_data_raw/results",
            },
            "session_recording": {
                "enabled": True,
                "record_spins": True,
                "file_format": "csv",
            },
            "json_formatting": {
                "indent": 2,
                "compact_arrays": True,
                "ensure_ascii": False
            },
            "reports": {
                "generate_reports": True,
                "include": {
                    "summary_report": True,
                    "player_preference_report": True,
                    "machine_performance_report": True,
                    "detailed_session_report": False
                }
            },
            "show_progress": True,
            "auto_cleanup": False
        }
        
        # 合并配置
        self.config = default_config
        if config:
            self._merge_config(self.config, config)
        
        self.s3 = None
        
        # 当前任务目录
        self.task_dir = None
        self.initialized = False
        
    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]):
        """递归合并配置字典。"""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value
                
    def initialize(self, simulation_name: Optional[str] = None):
        """
        初始化输出目录结构。
        
        Args:
            simulation_name: 可选的模拟名称
            
        Returns:
            任务目录路径
        """
        if self.initialized:
            return self.task_dir
            
        # 创建基础目录
        base_dir = self.config["directories"]["base_dir"]
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        # 创建任务目录（如果启用）
        if self.config["directories"]["use_simulation_subdir"]:
            timestamp = time.strftime(
                self.config["directories"]["timestamp_format"]
            )
            
            dir_format = self.config["directories"]["simulation_dir_format"]
            if "{name}" in dir_format and simulation_name:
                task_dir_name = dir_format.format(name=simulation_name, timestamp=timestamp)
            else:
                task_dir_name = dir_format.format(timestamp=timestamp)
                
            self.task_dir = os.path.join(base_dir, task_dir_name)
            os.makedirs(self.task_dir, exist_ok=True)
            
            # 创建子目录
            os.makedirs(os.path.join(self.task_dir, "reports"), exist_ok=True)
            os.makedirs(os.path.join(self.task_dir, "temp_summaries"), exist_ok=True)
            
        else:
            self.task_dir = base_dir

        if self.config["s3"]["use_s3"]:
            self.logger.info(f"s3 client Initialized")
            self.s3 = S3Service(
                region=self.config["s3"]["region"],
                bucket=self.config["s3"]["bucket"],
                prefix=self.config["s3"]["prefix"]
            )

        self.initialized = True
        self.logger.info(f"Output structure initialized at {self.task_dir}")
        
        return self.task_dir
    
    def _parse_session_id(self, session_id: str) -> Tuple[str, str]:
        """
        从session_id解析player_id和machine_id
        假设：table名称只有一个单词，不包含下划线
        
        Args:
            session_id: 格式为 "player_id_machine_id_session_num"
            
        Returns:
            (player_id, machine_id)
        """
        parts = session_id.split('_')
        if len(parts) < 3:
            self.logger.warning(f"Invalid session_id format: {session_id}")
            return "unknown_player", "unknown_machine"
        
        # 最后一个部分是session_num，倒数第二个是machine_id（单个单词）
        machine_id = parts[-2]
        # 其余部分组成player_id
        player_id = '_'.join(parts[:-2])
        
        self.logger.debug(f"Parsed session_id '{session_id}' -> player_id: '{player_id}', machine_id: '{machine_id}'")
        return player_id, machine_id
        
    def get_cluster_table_directory(self, player_id: str, machine_id: str, subdir: str = None) -> str:
        """
        获取cluster/table两层目录结构的路径
        
        Args:
            player_id: 玩家ID (cluster名称)
            machine_id: 机器ID (table名称)  
            subdir: 可选的子目录名称 (如 "raw_data", "summary")
            
        Returns:
            cluster/table目录路径
        """
        if not self.initialized:
            self.initialize()
        
        # 构建cluster/table两层目录
        cluster_dir = os.path.join(self.task_dir, player_id)
        table_dir = os.path.join(cluster_dir, machine_id)
        
        if subdir:
            final_dir = os.path.join(table_dir, subdir)
        else:
            final_dir = table_dir
            
        # 确保目录存在，但不覆盖现有文件
        os.makedirs(final_dir, exist_ok=True)
        
        self.logger.debug(f"Directory path: {final_dir}")
        return final_dir
        
    def get_temp_summary_directory(self) -> str:
        """
        获取临时summary目录路径
        
        Returns:
            临时summary目录路径
        """
        if not self.initialized:
            self.initialize()
            
        temp_dir = os.path.join(self.task_dir, "temp_summaries")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
        
    def get_reports_directory(self) -> str:
        """获取报告目录路径。"""
        if not self.initialized:
            self.initialize()
            
        return os.path.join(self.task_dir, "reports")

    def finalize_all_summaries(self) -> Dict[str, str]:
        """
        合并所有player-machine对的临时summary文件到最终CSV
        
        Returns:
            包含所有合并文件路径的字典 {pair_key: file_path}
        """
        try:
            # 获取所有临时summary文件
            temp_dir = self.get_temp_summary_directory()
            
            if not os.path.exists(temp_dir):
                self.logger.warning("Temp summary directory does not exist")
                return {}
            
            # 解析所有文件找到player-machine对
            pairs = set()
            for filename in os.listdir(temp_dir):
                if filename.endswith('_summary.json'):
                    # 从文件名解析player_id和machine_id
                    parts = filename.replace('_summary.json', '').split('_')
                    if len(parts) >= 3:
                        # 假设格式：player_id_machine_id_session_num
                        session_num = parts[-1]
                        machine_id = parts[-2]
                        player_id = '_'.join(parts[:-2])
                        pairs.add((player_id, machine_id))
            
            self.logger.info(f"Found {len(pairs)} player-machine pairs for summary finalization")
            
            # 为每个pair合并summary
            merged_files = {}
            for player_id, machine_id in pairs:
                pair_key = f"{player_id}_{machine_id}"
                merged_file = self._merge_temp_summaries_for_pair(player_id, machine_id)
                if merged_file:
                    merged_files[pair_key] = merged_file
                    self.logger.debug(f"Merged summaries for {pair_key}: {merged_file}")
            
            self.logger.info(f"Successfully merged summaries for {len(merged_files)} pairs")
            return merged_files
            
        except Exception as e:
            self.logger.error(f"Error finalizing all summaries: {str(e)}")
            return {}

    def _merge_temp_summaries_for_pair(self, player_id: str, machine_id: str) -> Optional[str]:
        """
        将特定player-machine对的临时summary文件合并成最终CSV
        
        Args:
            player_id: 玩家ID
            machine_id: 机器ID
            
        Returns:
            合并后的CSV文件路径或S3相对路径
        """
        try:
            # 找到所有相关的临时summary文件
            temp_dir = self.get_temp_summary_directory()
            session_prefix = f"{player_id}_{machine_id}_"
            
            temp_files = []
            for filename in os.listdir(temp_dir):
                if filename.startswith(session_prefix) and filename.endswith('_summary.json'):
                    temp_files.append(os.path.join(temp_dir, filename))
            
            if not temp_files:
                self.logger.warning(f"No temp summary files found for {player_id}_{machine_id}")
                return None
            
            # 按文件名排序确保session顺序
            temp_files.sort()
            
            self.logger.info(f"Found {len(temp_files)} temp summary files for {player_id}_{machine_id}")
            
            # 读取所有summary数据
            all_summaries = []
            for temp_file in temp_files:
                try:
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                        all_summaries.append(summary_data)
                except Exception as e:
                    self.logger.error(f"Error reading temp file {temp_file}: {str(e)}")
                    continue
            
            if not all_summaries:
                self.logger.error(f"No valid summary data found for {player_id}_{machine_id}")
                return None
            
            # 如果使用S3，直接上传而不保存本地文件
            if self.s3:
                # 构造S3路径（相对于task_dir）
                task_dir_name = os.path.basename(self.task_dir)
                s3_rel_path = f"{task_dir_name}/{player_id}/{machine_id}/summary/{player_id}_{machine_id}_sessions_summary.csv"
                
                # 创建CSV内容
                all_fields = set()
                for summary in all_summaries:
                    all_fields.update(summary.keys())
                
                csv_fields = sorted(list(all_fields))
                
                # 构建CSV内容字符串
                import io
                csv_content = io.StringIO()
                writer = csv.DictWriter(csv_content, fieldnames=csv_fields)
                writer.writeheader()
                
                for summary in all_summaries:
                    # 处理复杂字段
                    row_data = {}
                    for field in csv_fields:
                        value = summary.get(field, '')
                        
                        if isinstance(value, (list, dict)):
                            row_data[field] = json.dumps(value, ensure_ascii=False)
                        else:
                            row_data[field] = value
                    
                    writer.writerow(row_data)
                
                # 上传到S3
                csv_bytes = csv_content.getvalue().encode('utf-8')
                self.s3.upload_bytes(csv_bytes, s3_rel_path)
                self.logger.info(f"Uploaded merged summary CSV to S3: {s3_rel_path}")
                
                return s3_rel_path
            
            else:
                # 本地存储
                summary_dir = self.get_cluster_table_directory(player_id, machine_id, "summary")
                csv_filepath = os.path.join(summary_dir, f"{player_id}_{machine_id}_sessions_summary.csv")
                
                # 获取所有字段名
                all_fields = set()
                for summary in all_summaries:
                    all_fields.update(summary.keys())
                
                csv_fields = sorted(list(all_fields))
                
                with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=csv_fields)
                    writer.writeheader()
                    
                    for summary in all_summaries:
                        # 处理复杂字段
                        row_data = {}
                        for field in csv_fields:
                            value = summary.get(field, '')
                            
                            if isinstance(value, (list, dict)):
                                row_data[field] = json.dumps(value, ensure_ascii=False)
                            else:
                                row_data[field] = value
                        
                        writer.writerow(row_data)
                
                self.logger.info(f"Merged {len(all_summaries)} summaries to {csv_filepath}")
                return csv_filepath
            
        except Exception as e:
            self.logger.error(f"Error merging temp summaries for {player_id}_{machine_id}: {str(e)}")
            return None
        finally:
            # 清理临时文件
            if self.config.get("auto_cleanup", False):
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                        self.logger.debug(f"Removed temp file: {temp_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to remove temp file {temp_file}: {str(e)}")
        
    def write_report(self, report_name: str, data: Dict[str, Any]) -> str:
        """写入报告。"""
        reports_dir = self.get_reports_directory()
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{report_name}_{timestamp}.json"
        filepath = os.path.join(reports_dir, filename)
        
        self._write_formatted_json(filepath, data)
        self.logger.info(f"Wrote report to {filepath}")
        return filepath
        
    def copy_config(self, config: Dict[str, Any]) -> str:
        """复制模拟配置到结果目录，便于复现。"""
        if not self.initialized:
            self.initialize()
            
        filepath = os.path.join(self.task_dir, "simulation_config.json")
        self._write_formatted_json(filepath, config)
        self.logger.info(f"Copied simulation config to {filepath}")
        return filepath
        
    def _write_formatted_json(self, filepath: str, data: Any) -> None:
        """写入格式化的JSON到文件。"""
        json_config = self.config.get("json_formatting", {})
        indent = json_config.get("indent", 2)
        ensure_ascii = json_config.get("ensure_ascii", False)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 写入JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        
    def cleanup(self):
        """清理临时文件。"""
        if not self.config["auto_cleanup"]:
            return
            
        if not self.initialized:
            return
            
        self.logger.info("Cleanup completed")
        
    @property
    def should_record_spins(self) -> bool:
        return self.config["session_recording"]["enabled"]