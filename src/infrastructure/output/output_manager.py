# src/infrastructure/output/output_manager.py
import os
import json
import time
import logging
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional, IO


class OutputManager:
    """
    集中管理模拟器的输出操作，处理文件结构、配置和数据写入。
    
    负责:
    - 根据配置确定输出粒度和位置
    - 创建和管理文件结构
    - 提供统一的文件写入接口
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化输出管理器。
        
        Args:
            config: 输出配置字典
        """
        self.logger = logging.getLogger("infrastructure.output.manager")
        
        # 默认配置
        default_config = {
            "directories": {
                "base_dir": "results",
                "use_simulation_subdir": True,
                "simulation_dir_format": "task_{task_id}_{timestamp}",
                "timestamp_format": "%Y%m%d-%H%M%S",
                "task_id": "default"  # 任务ID
            },
            "session_recording": {
                "enabled": True,
                "record_spins": True,
                "file_format": "csv",  # 默认使用CSV格式
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
        """
        递归合并配置字典。
        
        Args:
            target: 目标配置字典
            source: 源配置字典
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value
                
    def initialize(self, simulation_name: Optional[str] = None):
        """
        初始化输出目录结构。
        利用现有的simulation_dir_format，如果有task_id就使用，否则生成一个。
        
        Args:
            simulation_name: 可选的模拟名称（兼容现有接口）
            
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
            # 使用现有的格式字符串，支持 {timestamp} 占位符
            timestamp = time.strftime(
                self.config["directories"]["timestamp_format"]
            )
            
            # 检查格式字符串中是否包含 task_id 占位符
            dir_format = self.config["directories"]["simulation_dir_format"]
            if "{task_id}" in dir_format:
                # 使用传入的名称或配置中的task_id
                task_id = simulation_name or self.config["directories"].get("task_id", f"task_{int(time.time())}")
                task_dir_name = dir_format.format(task_id=task_id, timestamp=timestamp)
            else:
                # 兼容现有的格式（只有timestamp）
                task_dir_name = dir_format.format(timestamp=timestamp)
                
            self.task_dir = os.path.join(base_dir, task_dir_name)
            
            # 创建任务目录
            os.makedirs(self.task_dir, exist_ok=True)
            
            # 创建子目录
            os.makedirs(os.path.join(self.task_dir, "reports"), exist_ok=True)
            
        else:
            # 如果不使用任务子目录，直接使用基础目录
            self.task_dir = base_dir
            
        self.initialized = True
        self.logger.info(f"Output structure initialized at {self.task_dir}")
        
        return self.task_dir
        
    def get_player_machine_directory(self, player_id: str, machine_id: str) -> str:
        """
        获取特定玩家-机器对的目录路径。
        
        Args:
            player_id: 玩家ID
            machine_id: 机器ID
            
        Returns:
            玩家-机器对目录路径
        """
        if not self.initialized:
            self.initialize()
            
        player_machine_dir = os.path.join(self.task_dir, f"{player_id}_{machine_id}")
        os.makedirs(player_machine_dir, exist_ok=True)
        
        return player_machine_dir
        
    def get_reports_directory(self) -> str:
        """
        获取报告目录路径。
        
        Returns:
            报告目录路径
        """
        if not self.initialized:
            self.initialize()
            
        return os.path.join(self.task_dir, "reports")

    def write_session_summary(self, session_id: str, data: Dict[str, Any]) -> str:
        """
        写入会话摘要到对应的玩家-机器目录。
        
        Args:
            session_id: 会话ID (格式: player_id_machine_id_session_num)
            data: 摘要数据
            
        Returns:
            文件路径
        """
        if not self.config["session_recording"]["enabled"]:
            return None
            
        # 从session_id解析player_id和machine_id
        parts = session_id.split('_')
        if len(parts) >= 3:
            # 假设格式为 player_id_machine_id_session_num
            player_id = parts[0]
            machine_id = parts[1]
        else:
            # 如果解析失败，使用默认值
            player_id = "unknown_player"
            machine_id = "unknown_machine"
            
        player_machine_dir = self.get_player_machine_directory(player_id, machine_id)
        filepath = os.path.join(player_machine_dir, f"{session_id}_summary.json")
        
        self._write_formatted_json(filepath, data)
            
        self.logger.debug(f"Wrote session summary to {filepath}")
        return filepath
        
    def write_session_raw_data_csv(self, session_id: str, spins_data: List[Any]) -> str:
        """
        写入会话原始spin数据为CSV格式。
        
        Args:
            session_id: 会话ID
            spins_data: spin数据列表（SpinResult对象列表）
            
        Returns:
            文件路径
        """
        if not self.config["session_recording"]["enabled"] or not spins_data:
            return None
            
        # 从session_id解析player_id和machine_id
        parts = session_id.split('_')
        if len(parts) >= 3:
            player_id = parts[0]
            machine_id = parts[1]
        else:
            player_id = "unknown_player"
            machine_id = "unknown_machine"
            
        player_machine_dir = self.get_player_machine_directory(player_id, machine_id)
        filepath = os.path.join(player_machine_dir, f"{session_id}_raw.csv")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        try:
            # 动态获取CSV字段 - 从第一个SpinResult对象的to_dict()结果获取
            if hasattr(spins_data[0], 'to_dict'):
                # 如果是SpinResult对象，使用to_dict()方法
                first_spin_dict = spins_data[0].to_dict()
            else:
                # 如果已经是字典，直接使用
                first_spin_dict = spins_data[0]
                
            csv_fields = list(first_spin_dict.keys())
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_fields)
                writer.writeheader()
                
                for spin_data in spins_data:
                    # 处理SpinResult对象或字典
                    if hasattr(spin_data, 'to_dict'):
                        # SpinResult对象，转换为字典
                        spin_dict = spin_data.to_dict()
                    else:
                        # 已经是字典
                        spin_dict = spin_data
                    
                    # 处理复杂字段（转为字符串）
                    row_data = {}
                    for field in csv_fields:
                        value = spin_dict.get(field, '')
                        
                        # 处理列表和复杂对象
                        if isinstance(value, (list, dict)):
                            row_data[field] = json.dumps(value, ensure_ascii=False)
                        else:
                            row_data[field] = value
                            
                    writer.writerow(row_data)
                    
            self.logger.debug(f"Wrote {len(spins_data)} spin records to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error writing CSV file {filepath}: {str(e)}")
            return None
    
    def append_player_machine_session_summary(self, player_id: str, machine_id: str, 
                                             session_summary: Dict[str, Any]) -> str:
        """
        将会话摘要追加到玩家-机器汇总文件。
        
        Args:
            player_id: 玩家ID
            machine_id: 机器ID
            session_summary: 会话摘要数据
            
        Returns:
            文件路径
        """
        player_machine_dir = self.get_player_machine_directory(player_id, machine_id)
        filepath = os.path.join(player_machine_dir, "sessions_summary.json")
        
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
        
    def write_report(self, report_name: str, data: Dict[str, Any]) -> str:
        """
        写入报告。
        
        Args:
            report_name: 报告名称
            data: 报告数据
            
        Returns:
            文件路径
        """
        reports_dir = self.get_reports_directory()
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{report_name}_{timestamp}.json"
        filepath = os.path.join(reports_dir, filename)
        
        self._write_formatted_json(filepath, data)
            
        self.logger.info(f"Wrote report to {filepath}")
        return filepath
        
    def copy_config(self, config: Dict[str, Any]) -> str:
        """
        复制模拟配置到结果目录，便于复现。
        
        Args:
            config: 模拟配置
            
        Returns:
            文件路径
        """
        if not self.initialized:
            self.initialize()
            
        filepath = os.path.join(self.task_dir, "simulation_config.json")
        
        self._write_formatted_json(filepath, config)
            
        self.logger.info(f"Copied simulation config to {filepath}")
        return filepath
        
    def _write_formatted_json(self, filepath: str, data: Any) -> None:
        """
        写入格式化的JSON到文件。
        
        Args:
            filepath: 文件路径
            data: 要写入的数据
        """
        json_config = self.config.get("json_formatting", {})
        indent = json_config.get("indent", 2)
        ensure_ascii = json_config.get("ensure_ascii", False)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 写入JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        
    def cleanup(self):
        """
        清理临时文件。
        """
        if not self.config["auto_cleanup"]:
            return
            
        if not self.initialized:
            return
            
        self.logger.info("Cleanup completed (no action needed with new design)")
        
    @property
    def should_record_spins(self) -> bool:
        return self.config["session_recording"]["enabled"]