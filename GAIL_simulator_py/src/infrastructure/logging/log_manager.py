# src/infrastructure/logging/log_manager.py
import logging
import os
import sys
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Any, Optional, List, Union


class LogManager:
    """
    Centralized logging configuration manager.
    """
    def __init__(self):
        """Initialize the log manager."""
        self.root_logger = logging.getLogger()
        self.loggers = {}  # name -> logger
        self.handlers = {}  # name -> handler
        self.initialized = False
        
    def initialize(self, config: Dict[str, Any]):
        """
        Initialize logging system based on configuration.
        
        Args:
            config: Logging configuration dictionary
        """
        if self.initialized:
            return
            
        # Get config values with defaults
        log_level = self._get_log_level(config.get('level', 'INFO'))
        log_format = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_date_format = config.get('date_format', '%Y-%m-%d %H:%M:%S')
        console_enabled = config.get('console', True)
        file_enabled = config.get('file', {}).get('enabled', False)
        
        # Configure root logger
        self.root_logger.setLevel(log_level)
        
        # Clear any existing handlers
        for handler in list(self.root_logger.handlers):
            self.root_logger.removeHandler(handler)
            
        # Create formatter
        formatter = logging.Formatter(log_format, log_date_format)
        
        # Add console handler if enabled
        if console_enabled:
            console_level = self._get_log_level(config.get('console_level', log_level))
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(console_level)
            console_handler.setFormatter(formatter)
            self.root_logger.addHandler(console_handler)
            self.handlers['console'] = console_handler
            
        # Add file handler if enabled
        if file_enabled:
            file_config = config.get('file', {})
            file_path = file_config.get('path', 'logs/simulator.log')
            file_level = self._get_log_level(file_config.get('level', log_level))
            max_bytes = file_config.get('max_bytes', 10 * 1024 * 1024)  # 10 MB
            backup_count = file_config.get('backup_count', 5)
            
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # Create rotating file handler
            file_handler = RotatingFileHandler(
                file_path, 
                maxBytes=max_bytes, 
                backupCount=backup_count
            )
            file_handler.setLevel(file_level)
            file_handler.setFormatter(formatter)
            self.root_logger.addHandler(file_handler)
            self.handlers['file'] = file_handler
            
        # Configure specialized loggers if specified
        if 'loggers' in config:
            # 首先按照 logger 名称长度排序，确保先配置父 logger，再配置子 logger
            logger_names = sorted(config['loggers'].keys(), key=lambda x: len(x.split('.')))
            
            for logger_name in logger_names:
                logger_config = config['loggers'][logger_name]
                logger_level = self._get_log_level(logger_config.get('level', log_level))
                
                # 获取或创建 logger
                logger = logging.getLogger(logger_name)
                
                # 设置级别
                logger.setLevel(logger_level)
                
                # 重要：禁止向上传播到父 logger，确保级别设置独立生效
                # 注释：如果希望同时将日志传播到父 logger，可以设置为 True
                propagate = logger_config.get('propagate', False)
                logger.propagate = propagate
                
                # 如果需要特定的处理器，可以添加
                if logger_config.get('handlers'):
                    # 处理特定的处理器配置...
                    pass
                    
                self.loggers[logger_name] = logger
                
                # 记录配置信息到调试日志
                self.root_logger.debug(
                    f"Configured logger '{logger_name}' with level={logging.getLevelName(logger_level)}, "
                    f"propagate={propagate}"
                )
                    
        self.root_logger.debug("Logging system initialized")
        self.initialized = True
        
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger by name.
        
        Args:
            name: Logger name (usually __name__ of the module)
            
        Returns:
            Logger instance
        """
        return logging.getLogger(name)
        
    def add_session_file_handler(self, session_id: str, log_dir: str = 'logs/sessions') -> logging.Handler:
        """
        Add a file handler for a specific session.
        
        Args:
            session_id: Unique session identifier
            log_dir: Directory for session logs
            
        Returns:
            The created file handler
        """
        # Create session log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Create session log file
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        log_file = os.path.join(log_dir, f"{session_id}_{timestamp}.log")
        
        # Create handler
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Add to root logger
        self.root_logger.addHandler(handler)
        self.handlers[f"session_{session_id}"] = handler
        
        return handler
        
    def remove_session_handler(self, session_id: str) -> bool:
        """
        Remove a session file handler.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if handler was removed, False otherwise
        """
        handler_key = f"session_{session_id}"
        if handler_key in self.handlers:
            handler = self.handlers[handler_key]
            self.root_logger.removeHandler(handler)
            handler.close()
            del self.handlers[handler_key]
            return True
        return False
        
    def _get_log_level(self, level_name: Union[str, int]) -> int:
        """
        Convert a log level name to its numeric value.
        
        Args:
            level_name: Level name (DEBUG, INFO, etc.) or numeric value
            
        Returns:
            Numeric log level
        """
        if isinstance(level_name, int):
            return level_name
            
        level_name = level_name.upper()
        level_map = {
            'CRITICAL': logging.CRITICAL,
            'FATAL': logging.FATAL,
            'ERROR': logging.ERROR,
            'WARNING': logging.WARNING,
            'WARN': logging.WARN,
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG,
            'NOTSET': logging.NOTSET
        }
        
        return level_map.get(level_name, logging.INFO)
        

# Singleton instance
log_manager = LogManager()


# Example usage:
@staticmethod
def initialize_logging(config: Dict[str, Any] = None):
    """
    Initialize the logging system from a configuration file or default settings.
    
    Args:
        config_path: Optional path to logging configuration file
    """

    # Default configuration
    default_config = {
        'level': 'INFO',
        'console': True,
        'console_level': 'INFO',
        'file': {
            'enabled': True,
            'path': 'logs/simulator.log',
            'level': 'DEBUG',
            'max_bytes': 10 * 1024 * 1024,  # 10 MB
            'backup_count': 5
        },
        'loggers': {
            'domain.machine': {'level': 'DEBUG'},
            'domain.player': {'level': 'DEBUG'},
            'domain.session': {'level': 'DEBUG'},
            'infrastructure.rng': {'level': 'INFO'}
        }
    }
    
    # If config file provided, load it
    if config is None:
        config = default_config
        
    # Initialize logging
    log_manager.initialize(config)

    print("Configured loggers:")
    for name, logger in log_manager.loggers.items():
        print(f"- {name}: level={logging.getLevelName(logger.level)}, propagate={logger.propagate}")
    
    return log_manager