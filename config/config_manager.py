"""
配置管理器模块
负责配置文件的加载、验证和管理
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
from utils.system_utils import validate_config, backup_file


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> bool:
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                self._create_default_config()
                return True
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
            
            # 验证配置
            validation = validate_config(self.config)
            if not validation['valid']:
                print("配置验证错误:")
                for error in validation['errors']:
                    print(f"  ❌ {error}")
                return False
            
            if validation['warnings']:
                print("配置警告:")
                for warning in validation['warnings']:
                    print(f"  ⚠️ {warning}")
            
            return True
            
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def _create_default_config(self) -> None:
        """创建默认配置文件"""
        default_config = {
            'system': {
                'name': '订单管理助手',
                'version': '1.0.0',
                'environment': 'production'
            },
            'material_mapping': {
                'csv_path': 'config/material_mapping.csv'
            },
            'file_monitoring': {
                'onoff_file': 'C:/macro/onoff.txt',
                'macro_file': 'C:/macro/macro.txt'
            },
            'dnc_system': {
                'window_title': 'DNC System',
                'process_name': 'dnc.exe',
                'class_name': 'DNC_Class'
            },
            'performance': {
                'ui_automation_timeout': 10,
                'file_monitoring_timeout': 30,
                'task_scheduling_timeout': 60,
                'material_check_timeout': 15
            },
            'automation': {
                'retry_attempts': 3,
                'max_workers': 5,
                'delay_between_retries': 1.0
            },
            'materials': {
                'low_stock_threshold': 10,
                'critical_stock_threshold': 5
            },
            'tasks': {
                'priority_levels': ['Normal', 'High', 'Urgent'],
                'auto_start': True
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/system.log',
                'max_size': '10MB',
                'backup_count': 5
            },
            'machine_status_mapping': {
                'system_internal': {
                    'OFF': '关机',
                    'IDLE': '空闲',
                    'STANDBY': '待机',
                    'READY': '就绪',
                    'RUNNING': '运行',
                    'ALARM': '报警'
                },
                'available_states': ['OFF', 'IDLE', 'STANDBY', 'READY', 'RUNNING', 'ALARM'],
                'cnc_simulator': {
                    '0': 'OFF',
                    '1': 'IDLE',
                    '2': 'STANDBY',
                    '3': 'READY',
                    '4': 'RUNNING',
                    '5': 'ALARM'
                }
            }
        }
        
        # 确保配置目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入默认配置
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        
        self.config = default_config
        print(f"✅ 已创建默认配置文件: {self.config_path}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置值"""
        try:
            keys = key.split('.')
            config = self.config
            
            # 遍历到最后一个键的父级
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            
            # 保存配置
            return self.save()
            
        except Exception as e:
            print(f"设置配置失败: {e}")
            return False
    
    def save(self) -> bool:
        """保存配置到文件"""
        try:
            # 备份原配置文件
            if self.config_path.exists():
                backup_file(str(self.config_path))
            
            # 保存新配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ 配置已保存: {self.config_path}")
            return True
            
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def reload(self) -> bool:
        """重新加载配置"""
        return self._load_config()
    
    def validate_current_config(self) -> Dict[str, Any]:
        """验证当前配置"""
        return validate_config(self.config)
    
    def export_config(self, export_path: str) -> bool:
        """导出配置到指定路径"""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ 配置已导出: {export_path}")
            return True
            
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """从指定路径导入配置"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                print(f"❌ 导入文件不存在: {import_path}")
                return False
            
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_config = yaml.safe_load(f)
            
            # 验证导入的配置
            validation = validate_config(imported_config)
            if not validation['valid']:
                print("导入配置验证失败:")
                for error in validation['errors']:
                    print(f"  ❌ {error}")
                return False
            
            # 备份当前配置
            if self.config_path.exists():
                backup_file(str(self.config_path))
            
            # 应用新配置
            self.config = imported_config
            return self.save()
            
        except Exception as e:
            print(f"导入配置失败: {e}")
            return False
    
    def get_material_mapping_path(self) -> str:
        """获取材料映射表路径"""
        return self.get('material_mapping.csv_path', 'config/material_mapping.csv')
    
    def get_output_directory(self) -> str:
        """获取输出目录"""
        return self.get('file_monitoring.macro_file', 'C:/macro/macro.txt').rsplit('/', 1)[0]
    
    def get_status_directory(self) -> str:
        """获取状态目录"""
        return self.get('file_monitoring.onoff_file', 'C:/macro/onoff.txt').rsplit('/', 1)[0]
    
    def get_ui_timeout(self) -> float:
        """获取UI自动化超时时间"""
        return float(self.get('performance.ui_automation_timeout', 10))
    
    def get_ui_retry_count(self) -> int:
        """获取UI自动化重试次数"""
        return int(self.get('automation.retry_attempts', 3))
    
    def get_low_stock_threshold(self) -> int:
        """获取低库存阈值"""
        return int(self.get('materials.low_stock_threshold', 10))
    
    def get_critical_stock_threshold(self) -> int:
        """获取严重库存阈值"""
        return int(self.get('materials.critical_stock_threshold', 5))
    
    def get_max_concurrent_tasks(self) -> int:
        """获取最大并发任务数"""
        return int(self.get('automation.max_workers', 5))
    
    def get_priority_levels(self) -> list:
        """获取优先级级别"""
        return self.get('tasks.priority_levels', ['Normal', 'High', 'Urgent'])

    def get_machine_status_mapping(self, source_system: str = "cnc_simulator") -> Dict[str, str]:
        """获取机床状态映射配置
        
        Args:
            source_system: 来源系统标识符
            
        Returns:
            包含外部状态到内部状态映射的字典
        """
        mapping = self.get(f"machine_status_mapping.{source_system}", {})
        return mapping if mapping else {}
    
    def get_internal_status_definitions(self) -> Dict[str, str]:
        """获取系统内部状态定义
        
        Returns:
            包含内部状态码及其描述的字典
        """
        return self.get("machine_status_mapping.system_internal", {})
    
    def get_available_states(self) -> list:
        """获取可用状态列表
        
        Returns:
            状态代码列表
        """
        return self.get("machine_status_mapping.available_states", ["OFF", "IDLE", "STANDBY", "READY"])
    
    def print_config_summary(self) -> None:
        """打印配置摘要"""
        print("\n📋 配置摘要:")
        print(f"  系统名称: {self.get('system.name')}")
        print(f"  版本: {self.get('system.version')}")
        print(f"  环境: {self.get('system.environment')}")
        print(f"  材料映射表: {self.get_material_mapping_path()}")
        print(f"  输出目录: {self.get_output_directory()}")
        print(f"  状态目录: {self.get_status_directory()}")
        print(f"  最大并发任务: {self.get_max_concurrent_tasks()}")
        print(f"  UI超时: {self.get_ui_timeout()}秒")
        print(f"  UI重试次数: {self.get_ui_retry_count()}")
        print(f"  低库存阈值: {self.get_low_stock_threshold()}")
        print(f"  严重库存阈值: {self.get_critical_stock_threshold()}")


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager