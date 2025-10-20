"""
配置管理器
统一管理系统配置文件的加载和管理
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = {}
        self.logger = logging.getLogger(__name__)
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                self.logger.info(f"配置文件已加载: {self.config_path}")
            else:
                self.logger.warning(f"配置文件不存在: {self.config_path}")
                self._create_default_config()
                
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self.config = {
            'system': {
                'name': '数控车床生产管理系统',
                'version': '1.0.0',
                'debug': True
            },
            'logging': {
                'level': 'INFO',
                'file_path': 'logs/system.log',
                'max_size_mb': 10,
                'backup_count': 5
            },
            'file_monitoring': {
                'onoff_file': 'monitoring/onoff.txt',
                'macro_file': 'monitoring/macro.txt',
                'poll_interval': 1.0
            },
            'material_mapping': {
                'csv_path': 'config/material_mapping.csv'
            },
            'dnc_system': {
                'window_title': 'DNC系统',
                'class_name': 'DNCWindow',
                'process_name': 'dnc_system.exe',
                'timeout': 10,
                'controls': {
                    'main_input': [
                        {'method': 'auto_id', 'value': 'model_input'},
                        {'method': 'name', 'value': '型号输入'}
                    ],
                    'submit_button': [
                        {'method': 'auto_id', 'value': 'submit_btn'},
                        {'method': 'name', 'value': '提交'}
                    ]
                }
            },
            'browser_systems': {
                'daily_report': {
                    'url': 'http://localhost:8080/daily_report',
                    'instruction_input': [
                        {'selector': 'id', 'value': 'instruction_id'},
                        {'selector': 'name', 'value': 'instruction_number'}
                    ],
                    'submit_button': [
                        {'selector': 'css', 'value': 'button[type="submit"]'}
                    ]
                },
                'inspection_system': {
                    'url': 'http://localhost:8080/inspection',
                    'instruction_input': [
                        {'selector': 'id', 'value': 'instruction_input'},
                        {'selector': 'name', 'value': 'instruction'}
                    ]
                }
            },
            'scheduling': {
                'strategy': 'material_first',
                'check_interval': 10,
                'max_retries': 3
            },
            'machine_default_materials': {
                'CNC001': 'STEEL_45',
                'CNC002': 'ALUMINUM_6061',
                'CNC003': 'STAINLESS_STEEL_304'
            },
            'sample_tasks': [
                {
                    'task_id': 'TASK_20241020_080000_INS001',
                    'instruction_id': 'INS001',
                    'product_model': 'MODEL_A',
                    'material_spec': 'STEEL_45',
                    'order_quantity': 100,
                    'priority': 'Normal',
                    'estimated_duration': 120,
                    'program_available': True
                },
                {
                    'task_id': 'TASK_20241020_080100_INS002',
                    'instruction_id': 'INS002',
                    'product_model': 'MODEL_B',
                    'material_spec': 'ALUMINUM_6061',
                    'order_quantity': 50,
                    'priority': 'High',
                    'estimated_duration': 90,
                    'program_available': True
                }
            ]
        }
        
        # 保存默认配置
        self.save_config()
        self.logger.info("已创建默认配置文件")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self.logger.info(f"配置文件已保存: {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")
    
    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        
        # 遍历到最后一个键的父级
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
        
        # 自动保存
        self.save_config()
        self.logger.info(f"配置已更新: {key} = {value}")
    
    def update_section(self, section: str, new_values: Dict[str, Any]):
        """更新配置节"""
        if section in self.config:
            self.config[section].update(new_values)
        else:
            self.config[section] = new_values
        
        self.save_config()
        self.logger.info(f"配置节已更新: {section}")
    
    def validate_config(self) -> bool:
        """验证配置完整性"""
        required_sections = [
            'system',
            'logging',
            'file_monitoring',
            'material_mapping',
            'scheduling'
        ]
        
        for section in required_sections:
            if section not in self.config:
                self.logger.error(f"配置缺少必需节: {section}")
                return False
        
        # 验证文件路径
        if not self._validate_file_paths():
            return False
        
        self.logger.info("配置验证通过")
        return True
    
    def _validate_file_paths(self) -> bool:
        """验证文件路径配置"""
        try:
            # 检查监控文件目录
            onoff_dir = Path(self.get('file_monitoring.onoff_file')).parent
            macro_dir = Path(self.get('file_monitoring.macro_file')).parent
            
            # 创建必要的目录
            onoff_dir.mkdir(parents=True, exist_ok=True)
            macro_dir.mkdir(parents=True, exist_ok=True)
            
            # 检查日志目录
            log_dir = Path(self.get('logging.file_path')).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"文件路径验证失败: {e}")
            return False
    
    def reload_config(self):
        """重新加载配置"""
        self.load_config()
        self.logger.info("配置已重新加载")
    
    def get_machine_config(self, machine_id: str) -> Dict[str, Any]:
        """获取机床特定配置"""
        machine_config = self.config.get('machines', {}).get(machine_id, {})
        
        # 返回默认配置与机床特定配置的合并
        default_machine_config = {
            'material': self.config.get('machine_default_materials', {}).get(machine_id, 'UNKNOWN'),
            'capabilities': ['turning', 'facing'],
            'ip_address': '192.168.1.100'
        }
        
        default_machine_config.update(machine_config)
        return default_machine_config
    
    def get_scheduling_strategy(self) -> str:
        """获取调度策略"""
        return self.config.get('scheduling', {}).get('strategy', 'material_first')
    
    def set_scheduling_strategy(self, strategy: str):
        """设置调度策略"""
        if 'scheduling' not in self.config:
            self.config['scheduling'] = {}
        
        self.config['scheduling']['strategy'] = strategy
        self.save_config()
        self.logger.info(f"调度策略已设置为: {strategy}")
