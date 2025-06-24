# src/infrastructure/config/loaders/yaml_loader.py
import os
import yaml
import json
import logging
from typing import Dict, Any, List, Tuple, Optional, Union


class ConfigError(Exception):
    """表示配置加载或验证过程中的错误的基类。"""
    pass


class FileNotFoundConfigError(ConfigError):
    """表示配置文件或目录不存在。"""
    def __init__(self, path, message=None):
        self.path = path
        self.message = message or f"Configuration file or directory not found: {path}"
        super().__init__(self.message)


class YamlParseError(ConfigError):
    """表示YAML解析错误。"""
    def __init__(self, file_path, yaml_error):
        self.file_path = file_path
        self.yaml_error = yaml_error
        self.message = f"Error parsing YAML file {file_path}: {str(yaml_error)}"
        super().__init__(self.message)


class SchemaValidationError(ConfigError):
    """表示配置验证错误。"""
    def __init__(self, file_path, errors):
        self.file_path = file_path
        self.errors = errors
        error_msg = "\n  - ".join([""] + errors)
        self.message = f"Configuration validation failed for {file_path}:{error_msg}"
        super().__init__(self.message)


class YamlConfigLoader:
    """
    加载和验证YAML配置文件。
    
    提供详细的错误报告和可选的默认值机制。
    """
    def __init__(self, schema_validator=None):
        """
        初始化YAML配置加载器。
        
        Args:
            schema_validator: 可选的验证器，用于检查配置是否符合模式
        """
        self.logger = logging.getLogger(__name__)
        self.schema_validator = schema_validator
        self.strict_mode = True  # 严格模式下，文件不存在会抛出异常
        
    def set_strict_mode(self, strict: bool = True):
        """
        设置严格模式。在严格模式下，文件不存在会抛出异常。
        
        Args:
            strict: 是否启用严格模式
        """
        self.strict_mode = strict
        return self  # 允许方法链式调用
        
    def load_file(self, file_path: str, schema_path: Optional[str] = None, 
                default_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        加载单个YAML配置文件并可选地验证它。
        
        Args:
            file_path: YAML文件的路径
            schema_path: 用于验证的JSON模式的可选路径
            default_config: 文件不存在或加载失败时的默认配置
            
        Returns:
            解析后的配置字典
            
        Raises:
            FileNotFoundConfigError: 如果文件不存在且strict_mode=True
            YamlParseError: 如果YAML解析失败且没有提供默认配置或strict_mode=True
            SchemaValidationError: 如果验证失败且strict_mode=True
        """
        # 检查文件是否存在
        if not os.path.isfile(file_path):
            error_msg = f"Configuration file not found: {file_path}"
            self.logger.error(error_msg)
            
            if default_config is not None and not self.strict_mode:
                self.logger.warning(f"Using default configuration instead of missing file: {file_path}")
                return default_config
                
            raise FileNotFoundConfigError(file_path)
        
        # 加载YAML文件
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                
            # 记录成功加载
            self.logger.debug(f"Successfully loaded configuration from {file_path}")
            
            # 如果加载的结果为None（空文件），使用默认配置或空字典
            if config is None:
                self.logger.warning(f"Empty configuration file: {file_path}")
                config = default_config if default_config is not None else {}
                
            # 验证（如果提供了模式）
            if schema_path and self.schema_validator:
                schema = self._load_schema(schema_path)
                is_valid, errors = self.schema_validator.validate(config, schema)
                
                if not is_valid:
                    error = SchemaValidationError(file_path, errors)
                    
                    if self.strict_mode:
                        raise error
                        
                    self.logger.warning(f"{error.message}\nUsing unvalidated configuration.")
                else:
                    self.logger.debug(f"Successfully validated configuration against schema: {schema_path}")
                    
            return config
            
        except yaml.YAMLError as e:
            error = YamlParseError(file_path, e)
            self.logger.error(error.message)
            
            if default_config is not None and not self.strict_mode:
                self.logger.warning(f"Using default configuration due to parse error in {file_path}")
                return default_config
                
            raise error from e
            
    def load_directory(self, directory_path: str, schema_path: Optional[str] = None,
                     ignore_errors: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        从目录加载所有YAML文件。
        
        Args:
            directory_path: 包含YAML文件的目录的路径
            schema_path: 用于验证的可选模式路径
            ignore_errors: 是否忽略单个文件的加载错误
            
        Returns:
            将文件名（不带扩展名）映射到配置字典的字典
            
        Raises:
            FileNotFoundConfigError: 如果目录不存在且strict_mode=True
        """
        # 检查目录是否存在
        if not os.path.isdir(directory_path):
            error_msg = f"Configuration directory not found: {directory_path}"
            self.logger.error(error_msg)
            
            if not self.strict_mode:
                self.logger.warning(f"Returning empty configuration for missing directory: {directory_path}")
                return {}
                
            raise FileNotFoundConfigError(directory_path)
            
        # 获取目录中的所有YAML文件
        yaml_files = [f for f in os.listdir(directory_path) 
                     if f.endswith('.yaml') or f.endswith('.yml')]
        
        if not yaml_files:
            self.logger.warning(f"No YAML files found in {directory_path}")
            return {}
            
        # 加载每个文件
        configs = {}
        errors = []
        
        for filename in yaml_files:
            file_path = os.path.join(directory_path, filename)
            config_name = os.path.splitext(filename)[0]  # 移除扩展名
            
            try:
                config = self.load_file(file_path, schema_path)
                configs[config_name] = config
            except ConfigError as e:
                errors.append(f"{filename}: {str(e)}")
                if not ignore_errors and self.strict_mode:
                    # 在严格模式下重新抛出
                    raise
        
        if errors and not ignore_errors:
            self.logger.error(f"Errors occurred while loading files from {directory_path}:\n" + 
                          "\n".join(f"  - {err}" for err in errors))
        
        loaded_count = len(configs)
        failed_count = len(yaml_files) - loaded_count
        
        self.logger.info(
            f"Loaded {loaded_count} configuration files from {directory_path}" +
            (f" ({failed_count} failed)" if failed_count > 0 else "")
        )
        
        return configs
        
    def _load_schema(self, schema_path: str) -> Dict[str, Any]:
        """
        加载JSON模式文件。
        
        Args:
            schema_path: JSON模式文件的路径
            
        Returns:
            解析后的模式字典
            
        Raises:
            FileNotFoundConfigError: 如果模式文件不存在
            ConfigError: 如果模式解析失败
        """
        if not os.path.isfile(schema_path):
            error_msg = f"Schema file not found: {schema_path}"
            self.logger.error(error_msg)
            raise FileNotFoundConfigError(schema_path, error_msg)
            
        try:
            with open(schema_path, 'r', encoding='utf-8') as file:
                schema = json.load(file)
            return schema
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing schema file {schema_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ConfigError(error_msg) from e
    
    def load_with_fallbacks(self, file_paths: List[str], schema_path: Optional[str] = None) -> Dict[str, Any]:
        """
        尝试从多个路径加载配置，使用第一个成功的。
        
        Args:
            file_paths: 要尝试的文件路径列表，按优先级排序
            schema_path: 用于验证的可选模式路径
            
        Returns:
            第一个成功加载的配置
            
        Raises:
            ConfigError: 如果所有文件都加载失败且strict_mode=True
        """
        errors = []
        original_strict_mode = self.strict_mode
        
        try:
            # 暂时禁用严格模式以允许尝试多个文件
            self.strict_mode = False
            
            for path in file_paths:
                try:
                    config = self.load_file(path, schema_path)
                    self.logger.info(f"Successfully loaded configuration from {path}")
                    return config
                except ConfigError as e:
                    errors.append(f"{path}: {str(e)}")
            
            # 如果所有文件都失败
            error_msg = "All configuration files failed to load:\n" + "\n".join(f"  - {err}" for err in errors)
            self.logger.error(error_msg)
            
            if original_strict_mode:
                raise ConfigError(error_msg)
                
            # 非严格模式下返回空配置
            self.logger.warning("Using empty configuration as fallback")
            return {}
            
        finally:
            # 恢复原始严格模式
            self.strict_mode = original_strict_mode