# src/infrastructure/output/output_manager.py
import os
import json
import time
import logging
import shutil
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
                "simulation_dir_format": "sim_{name}_{timestamp}",  # 支持名称
                "timestamp_format": "%Y%m%d-%H%M%S",
                "simulation_name": "default"  # 默认模拟名称
            },
            "session_recording": {
                "enabled": True,
                "record_spins": True,
                "write_batches": True,
                "lru_max_size": 1000,
                "batch_size": 200,
                "compress_batches": False,
                "record_line_wins": False,
                "file_format": "json",
                # 新增: 高级统计配置
                "advanced_statistics": {
                    "enabled": False,  # 默认禁用高级统计
                    "include_in_summary": True,  # 是否在会话摘要中包含
                    "include_in_reports": True,  # 是否在报告中包含
                    "modules": {
                        "bet": True,        # 投注统计
                        "payout": True,     # 赢额统计
                        "profit": True,     # 净胜统计
                        "odds": True,       # 赔率统计
                        "balance": False    # 余额统计
                    }
                }
            },
            "json_formatting": {
                "indent": 2,                # 缩进空格数
                "compact_arrays": True,     # 简单数组是否紧凑显示
                "ensure_ascii": False       # 允许非ASCII字符
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
            
        # 当前模拟目录
        self.simulation_dir = None
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
        
        Args:
            simulation_name: 可选的模拟名称，覆盖配置中的名称
            
        Returns:
            模拟目录路径
        """
        if self.initialized:
            return self.simulation_dir
            
        # 创建基础目录
        base_dir = self.config["directories"]["base_dir"]
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        # 创建模拟目录（如果启用）
        if self.config["directories"]["use_simulation_subdir"]:
            # 使用传入的名称或配置中的名称
            sim_name = simulation_name or self.config["directories"].get("simulation_name", "default")
            
            timestamp = time.strftime(
                self.config["directories"]["timestamp_format"]
            )
            sim_dir_name = self.config["directories"]["simulation_dir_format"].format(
                name=sim_name,
                timestamp=timestamp
            )
            self.simulation_dir = os.path.join(base_dir, sim_dir_name)
            
            # 创建模拟目录
            os.makedirs(self.simulation_dir, exist_ok=True)
            
            # 创建子目录
            os.makedirs(os.path.join(self.simulation_dir, "reports"), exist_ok=True)
            os.makedirs(os.path.join(self.simulation_dir, "player_machine_summary"), exist_ok=True)
            
            if self.config["session_recording"]["enabled"]:
                os.makedirs(os.path.join(self.simulation_dir, "sessions"), exist_ok=True)
        else:
            # 如果不使用模拟子目录，直接使用基础目录
            self.simulation_dir = base_dir
            
        self.initialized = True
        self.logger.info(f"Output structure initialized at {self.simulation_dir}")
        
        return self.simulation_dir
        
    def get_session_directory(self, session_id: str) -> str:
        """
        获取会话目录路径。
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话目录路径
        """
        if not self.initialized:
            self.initialize()
            
        if not self.config["session_recording"]["enabled"]:
            return None
            
        session_dir = os.path.join(self.simulation_dir, "sessions", session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # 如果需要批次子目录
        if self.config["session_recording"]["write_batches"]:
            os.makedirs(os.path.join(session_dir, "batches"), exist_ok=True)
            
        return session_dir
        
    def get_reports_directory(self) -> str:
        """
        获取报告目录路径。
        
        Returns:
            报告目录路径
        """
        if not self.initialized:
            self.initialize()
            
        return os.path.join(self.simulation_dir, "reports")
        
    def get_player_machine_directory(self) -> str:
        """
        获取玩家-机器汇总目录路径。
        
        Returns:
            玩家-机器汇总目录路径
        """
        if not self.initialized:
            self.initialize()
            
        return os.path.join(self.simulation_dir, "player_machine_summary")

        
    def _format_json(self, obj: Any, fp: IO, indent: int, level: int = 0, 
                    compact_simple_arrays: bool = True, ensure_ascii: bool = False) -> None:
        """
        自定义JSON格式化，处理嵌套列表。
        
        Args:
            obj: 要格式化的对象
            fp: 文件指针
            indent: 缩进空格数
            level: 当前缩进级别
            compact_simple_arrays: 是否紧凑显示简单数组
            ensure_ascii: 是否确保ASCII编码
        """
        if isinstance(obj, dict):
            # 处理字典
            fp.write('{\n')
            items = list(obj.items())
            for i, (key, value) in enumerate(items):
                # 写入缩进和键
                fp.write(' ' * (level + indent) + json.dumps(key, ensure_ascii=ensure_ascii) + ': ')
                # 递归处理值
                self._format_json(value, fp, indent, level + indent, compact_simple_arrays, ensure_ascii)
                # 处理逗号和换行
                if i < len(items) - 1:
                    fp.write(',\n')
                else:
                    fp.write('\n')
            fp.write(' ' * level + '}')
            
        elif isinstance(obj, list):
            # 处理列表
            if compact_simple_arrays and all(isinstance(item, (int, float, bool, str, type(None))) for item in obj):
                # 简单列表紧凑显示
                fp.write(json.dumps(obj, ensure_ascii=ensure_ascii))
            else:
                # 复杂列表正常缩进
                fp.write('[\n')
                for i, item in enumerate(obj):
                    # 写入缩进
                    fp.write(' ' * (level + indent))
                    # 递归处理项
                    self._format_json(item, fp, indent, level + indent, compact_simple_arrays, ensure_ascii)
                    # 处理逗号和换行
                    if i < len(obj) - 1:
                        fp.write(',\n')
                    else:
                        fp.write('\n')
                fp.write(' ' * level + ']')
        else:
            # 处理基本类型
            fp.write(json.dumps(obj, ensure_ascii=ensure_ascii))
    
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
        compact_arrays = json_config.get("compact_arrays", True)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 使用自定义格式化写入JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            self._format_json(data, f, indent, 0, compact_arrays, ensure_ascii)
        
    def write_session_summary(self, session_id: str, data: Dict[str, Any]) -> str:
        """
        写入会话摘要。
        
        Args:
            session_id: 会话ID
            data: 摘要数据
            
        Returns:
            文件路径
        """
        if not self.config["session_recording"]["enabled"]:
            return None
            
        session_dir = self.get_session_directory(session_id)
        filepath = os.path.join(session_dir, "summary.json")
        
        self._write_formatted_json(filepath, data)
            
        self.logger.debug(f"Wrote session summary to {filepath}")
        return filepath
        
    def write_spin_batch(self, session_id: str, batch_data: List[Dict[str, Any]], 
                       batch_num: int = None) -> str:
        """
        写入旋转批次数据。
        
        Args:
            session_id: 会话ID
            batch_data: 批次数据
            batch_num: 批次编号（可选）
            
        Returns:
            文件路径或None（如果未启用）
        """
        if not self.config["session_recording"]["enabled"] or not self.config["session_recording"]["write_batches"]:
            return None
            
        if not batch_data:
            return None
            
        session_dir = self.get_session_directory(session_id)
        batches_dir = os.path.join(session_dir, "batches")
        
        # 生成批次文件名
        if batch_num is None:
            batch_num = int(time.time())
            
        batch_file = f"batch_{len(batch_data)}_{batch_num}.json"
        filepath = os.path.join(batches_dir, batch_file)
        
        # 写入格式化的JSON
        self._write_formatted_json(filepath, batch_data)
            
        self.logger.debug(f"Wrote {len(batch_data)} results to {filepath}")
        
        # 如果配置了压缩，压缩文件
        if self.config["session_recording"]["compress_batches"]:
            try:
                import gzip
                with open(filepath, 'rb') as f_in:
                    with gzip.open(f"{filepath}.gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(filepath)  # 删除原始文件
                filepath = f"{filepath}.gz"
            except ImportError:
                self.logger.warning("Compression requested but gzip module not available")
                
        return filepath
        
    def write_player_machine_summary(self, player_id: str, machine_id: str, 
                                   data: Dict[str, Any]) -> str:
        """
        写入玩家-机器汇总数据。
        
        Args:
            player_id: 玩家ID
            machine_id: 机器ID
            data: 汇总数据
            
        Returns:
            文件路径
        """
        summary_dir = self.get_player_machine_directory()
        filename = f"{player_id}_{machine_id}_summary.json"
        filepath = os.path.join(summary_dir, filename)
        
        self._write_formatted_json(filepath, data)
            
        self.logger.debug(f"Wrote player-machine summary to {filepath}")
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
            
        filepath = os.path.join(self.simulation_dir, "simulation_config.json")
        
        self._write_formatted_json(filepath, config)
            
        self.logger.info(f"Copied simulation config to {filepath}")
        return filepath
        
    def cleanup(self):
        """
        清理临时文件。
        如果配置了自动清理，删除批次文件但保留摘要。
        """
        if not self.config["auto_cleanup"]:
            return
            
        if not self.initialized:
            return
            
        # 目前支持的清理操作：删除批次文件
        self.logger.info("Performing cleanup...")
        
        sessions_dir = os.path.join(self.simulation_dir, "sessions")
        if not os.path.exists(sessions_dir):
            return
            
        # 遍历所有会话目录
        for session_id in os.listdir(sessions_dir):
            session_dir = os.path.join(sessions_dir, session_id)
            batches_dir = os.path.join(session_dir, "batches")
            
            if os.path.exists(batches_dir):
                # 删除批次文件
                shutil.rmtree(batches_dir)
                self.logger.debug(f"Removed batch files for session {session_id}")
                
        self.logger.info("Cleanup completed")
        
    @property
    def should_record_spins(self) -> bool:
        return (self.config["session_recording"]["enabled"] and 
                self.config["session_recording"]["record_spins"])
    
    @property
    def should_record_advanced_statistics(self) -> bool:
        return (self.config["session_recording"]["enabled"] and 
                self.config["session_recording"]["advanced_statistics"]["enabled"])
                
    @property
    def lru_max_size(self) -> int:
        """
        获取LRU内存中保留的最大记录数。
        
        Returns:
            最大旋转记录数
        """
        return self.config["session_recording"]["lru_max_size"]
        
    @property
    def batch_size(self) -> int:
        """
        获取批处理大小。
        
        Returns:
            批处理大小
        """
        return self.config["session_recording"]["batch_size"]