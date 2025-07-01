# src/infrastructure/output/output_manager.py

import os
import json
import time
import logging
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional, IO, Tuple


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

    def write_session_summary(self, session_id: str, data: Dict[str, Any]) -> str:
        """
        写入会话摘要到临时目录
        
        Args:
            session_id: 会话ID (格式: player_id_machine_id_session_num)
            data: 摘要数据
            
        Returns:
            文件路径
        """
        if not self.config["session_recording"]["enabled"]:
            return None
            
        # 写入到临时目录
        temp_dir = self.get_temp_summary_directory()
        filepath = os.path.join(temp_dir, f"{session_id}_summary.json")
        
        self._write_formatted_json(filepath, data)
        self.logger.debug(f"Wrote session summary to temp: {filepath}")
        return filepath
        
    def write_session_raw_data_csv(self, session_id: str, spins_data: List[Any]) -> str:
        """
        写入会话原始spin数据为CSV格式到cluster/table/raw_data目录
        
        Args:
            session_id: 会话ID
            spins_data: spin数据列表
            
        Returns:
            文件路径
        """
        if not self.config["session_recording"]["enabled"] or not spins_data:
            self.logger.debug(f"Skipping raw data write: enabled={self.config['session_recording']['enabled']}, data_count={len(spins_data) if spins_data else 0}")
            return None
            
        # 解析session_id
        player_id, machine_id = self._parse_session_id(session_id)
        self.logger.debug(f"Writing raw data for session {session_id}: player='{player_id}', machine='{machine_id}'")
            
        # 写入到cluster/table/raw_data目录
        raw_data_dir = self.get_cluster_table_directory(player_id, machine_id, "raw_data")
        filepath = os.path.join(raw_data_dir, f"{session_id}_raw.csv")
        
        self.logger.debug(f"Raw data file path: {filepath}")
        
        # 动态获取CSV字段
        if not spins_data:
            return None
            
        first_item = spins_data[0]
        
        # 检查第一个项目是SpinResult对象还是字典
        if hasattr(first_item, 'to_dict'):
            first_dict = first_item.to_dict()
            csv_fields = list(first_dict.keys())
        elif isinstance(first_item, dict):
            csv_fields = list(first_item.keys())
        else:
            csv_fields = [attr for attr in dir(first_item) 
                         if not attr.startswith('_') and not callable(getattr(first_item, attr))]
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_fields)
                writer.writeheader()
                
                for spin_data in spins_data:
                    # 处理不同类型的输入数据
                    if hasattr(spin_data, 'to_dict'):
                        data_dict = spin_data.to_dict()
                    elif isinstance(spin_data, dict):
                        data_dict = spin_data
                    else:
                        data_dict = {field: getattr(spin_data, field, '') for field in csv_fields}
                    
                    # 处理复杂字段（转为字符串）
                    row_data = {}
                    for field in csv_fields:
                        value = data_dict.get(field, '')
                        
                        if isinstance(value, (list, dict)):
                            row_data[field] = json.dumps(value, ensure_ascii=False)
                        else:
                            row_data[field] = value
                            
                    writer.writerow(row_data)
                    
            self.logger.debug(f"Wrote {len(spins_data)} spin records to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error writing CSV file {filepath}: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def append_player_machine_session_summary(self, player_id: str, machine_id: str, 
                                             session_summary: Dict[str, Any]) -> str:
        """
        将会话摘要追加到cluster/table/summary目录的汇总文件
        
        Args:
            player_id: 玩家ID (cluster)
            machine_id: 机器ID (table)
            session_summary: 会话摘要数据
            
        Returns:
            文件路径
        """
        # 写入到cluster/table/summary目录
        summary_dir = self.get_cluster_table_directory(player_id, machine_id, "summary")
        filepath = os.path.join(summary_dir, "sessions_summary.json")
        
        # 读取现有数据或创建新的
        sessions_data = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                sessions_data = []
        
        # 添加新的会话摘要
        sessions_data.append(session_summary)
        
        # 写入更新后的数据
        self._write_formatted_json(filepath, sessions_data)
        
        self.logger.debug(f"Appended session summary to {filepath}")
        return filepath
    
    def merge_temp_summaries_to_csv(self, player_id: str, machine_id: str) -> str:
        """
        将临时summary文件合并成一个大CSV放在cluster/table/summary目录下
        
        Args:
            player_id: 玩家ID
            machine_id: 机器ID
            
        Returns:
            合并后的CSV文件路径
        """
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
            return None
        
        # 写入合并后的CSV
        summary_dir = self.get_cluster_table_directory(player_id, machine_id, "summary")
        csv_filepath = os.path.join(summary_dir, f"{player_id}_{machine_id}_sessions_summary.csv")
        
        # 获取所有字段名
        all_fields = set()
        for summary in all_summaries:
            all_fields.update(summary.keys())
        
        csv_fields = sorted(list(all_fields))
        
        try:
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
            
            # 删除临时文件
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except Exception as e:
                    self.logger.warning(f"Failed to remove temp file {temp_file}: {str(e)}")
            
            return csv_filepath
            
        except Exception as e:
            self.logger.error(f"Error writing merged CSV {csv_filepath}: {str(e)}")
            return None
        
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