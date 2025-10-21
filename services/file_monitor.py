"""
文件监控服务
监控onoff.txt和macro.txt文件变化，实现机床状态感知
"""

import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, Callable, Optional
from pathlib import Path

from models.production_task import MachineState


class OnOffFileHandler(FileSystemEventHandler):
    """onoff.txt文件变更处理器"""
    
    def __init__(self, callback: Callable[[Dict[str, str]], None]):
        self.callback = callback
        self.logger = logging.getLogger(__name__)
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('onoff.txt'):
            self.logger.info("检测到onoff.txt文件变更")
            try:
                new_states = self.parse_onoff_file(event.src_path)
                self.callback(new_states)
            except Exception as e:
                self.logger.error(f"处理onoff.txt变更失败: {e}")
    
    def parse_onoff_file(self, file_path: str) -> Dict[str, str]:
        """解析onoff.txt文件"""
        states = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        machine_id, state = line.split('=', 1)
                        states[machine_id.strip()] = state.strip()
            self.logger.debug(f"解析onoff.txt结果: {states}")
        except Exception as e:
            self.logger.error(f"解析onoff.txt失败: {e}")
        return states


class MacroFileHandler(FileSystemEventHandler):
    """macro.txt文件变更处理器"""
    
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self.logger = logging.getLogger(__name__)
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('macro.txt'):
            self.logger.info("检测到macro.txt文件变更")
            try:
                with open(event.src_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.callback(content)
            except Exception as e:
                self.logger.error(f"处理macro.txt变更失败: {e}")


class FileMonitorManager:
    """文件监控管理器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.observer = Observer()
        self.handlers = {}
        self.is_running = False
        
        # 文件路径
        self.onoff_file_path = config_manager.get('file_monitoring.onoff_file')
        self.macro_file_path = config_manager.get('file_monitoring.macro_file')
   
        # 回调函数
        self.onoff_callback = None
        self.macro_callback = None
        
    def setup_monitoring(self, onoff_callback: Callable, macro_callback: Callable):
        """设置文件监控"""
        self.onoff_callback = onoff_callback
        self.macro_callback = macro_callback
        
        # 确保监控目录存在
        self._ensure_monitoring_directories()
        
        # 设置onoff.txt监控
        onoff_handler = OnOffFileHandler(self._onoff_callback_wrapper)
        self.observer.schedule(onoff_handler, 
                              path=os.path.dirname(self.onoff_file_path), 
                              recursive=False)
        
        # 设置macro.txt监控
        macro_handler = MacroFileHandler(self._macro_callback_wrapper)
        self.observer.schedule(macro_handler, 
                              path=os.path.dirname(self.macro_file_path), 
                              recursive=False)
        
        self.logger.info("文件监控服务已配置")
        
    def _ensure_monitoring_directories(self):
        """确保监控目录存在"""
        onoff_dir = os.path.dirname(self.onoff_file_path)
        macro_dir = os.path.dirname(self.macro_file_path)
        
        for directory in [onoff_dir, macro_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                self.logger.info(f"创建监控目录: {directory}")
    
    def _onoff_callback_wrapper(self, new_states: Dict[str, str]):
        """onoff.txt回调包装器"""
        if self.onoff_callback:
            try:
                self.onoff_callback(new_states)
            except Exception as e:
                self.logger.error(f"onoff.txt回调执行失败: {e}")
    
    def _macro_callback_wrapper(self, macro_content: str):
        """macro.txt回调包装器"""
        if self.macro_callback:
            try:
                self.macro_callback(macro_content)
            except Exception as e:
                self.logger.error(f"macro.txt回调执行失败: {e}")
    
    def start_monitoring(self):
        """启动文件监控"""
        if not self.is_running:
            self.observer.start()
            self.is_running = True
            self.logger.info("文件监控服务已启动")
        else:
            self.logger.warning("文件监控服务已在运行中")
    
    def stop_monitoring(self):
        """停止文件监控"""
        if self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            self.logger.info("文件监控服务已停止")
        else:
            self.logger.warning("文件监控服务未在运行")
    
    def get_current_onoff_states(self) -> Dict[str, str]:
        """获取当前onoff.txt状态"""
        try:
            if os.path.exists(self.onoff_file_path):
                handler = OnOffFileHandler(lambda x: None)
                return handler.parse_onoff_file(self.onoff_file_path)
            else:
                self.logger.warning(f"onoff.txt文件不存在: {self.onoff_file_path}")
                return {}
        except Exception as e:
            self.logger.error(f"获取当前onoff状态失败: {e}")
            return {}
    
    def get_current_macro_content(self) -> Optional[str]:
        """获取当前macro.txt内容"""
        try:
            if os.path.exists(self.macro_file_path):
                with open(self.macro_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning(f"macro.txt文件不存在: {self.macro_file_path}")
                return None
        except Exception as e:
            self.logger.error(f"获取当前macro内容失败: {e}")
            return None
    
    def parse_macro_variables(self, macro_content: str) -> Dict[str, str]:
        """解析macro.txt中的宏变量"""
        variables = {}
        try:
            for line in macro_content.split('\n'):
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    variables[key.strip()] = value.strip()
            self.logger.debug(f"解析macro变量: {variables}")
        except Exception as e:
            self.logger.error(f"解析macro变量失败: {e}")
        return variables


class MachineStateMonitor:
    """机床状态监控器"""
    
    def __init__(self, file_monitor: FileMonitorManager):
        self.file_monitor = file_monitor
        self.logger = logging.getLogger(__name__)
        self.current_states: Dict[str, str] = {}
        self.previous_states: Dict[str, str] = {}
        
    def start_monitoring(self, state_change_callback: Callable):
        """开始监控机床状态"""
        self.state_change_callback = state_change_callback
        self.file_monitor.setup_monitoring(
            onoff_callback=self._handle_onoff_change,
            macro_callback=self._handle_macro_change
        )
        self.file_monitor.start_monitoring()
        
        # 初始化当前状态
        self.current_states = self.file_monitor.get_current_onoff_states()
        self.previous_states = self.current_states.copy()
        
        self.logger.info("机床状态监控已启动")
    
    def _handle_onoff_change(self, new_states: Dict[str, str]):
        """处理onoff.txt变更"""
        self.previous_states = self.current_states.copy()
        self.current_states.update(new_states)
        
        # 检测状态变化
        state_changes = self._detect_state_changes()
        if state_changes:
            self.logger.info(f"检测到机床状态变化: {state_changes}")
            if self.state_change_callback:
                self.state_change_callback(state_changes)
    
    def _handle_macro_change(self, macro_content: str):
        """处理macro.txt变更"""
        variables = self.file_monitor.parse_macro_variables(macro_content)
        self.logger.info(f"检测到macro.txt更新，解析变量: {variables}")
        # 这里可以添加宏变量处理逻辑
    
    def _detect_state_changes(self) -> Dict[str, Dict[str, str]]:
        """检测状态变化"""
        changes = {}
        for machine_id, current_state in self.current_states.items():
            previous_state = self.previous_states.get(machine_id)
            if previous_state != current_state:
                changes[machine_id] = {
                    'from': previous_state,
                    'to': current_state
                }
        return changes
    
    def get_machine_state(self, machine_id: str) -> str:
        """获取指定机床状态"""
        return self.current_states.get(machine_id, 'UNKNOWN')
    
    def is_machine_available(self, machine_id: str) -> bool:
        """检查机床是否可用"""
        state = self.get_machine_state(machine_id)
        return state.upper() in ['OFF', 'IDLE', 'STANDBY', 'READY']
    
    def get_available_machines(self) -> list:
        """获取所有可用机床"""
        return [machine_id for machine_id in self.current_states.keys() 
                if self.is_machine_available(machine_id)]
    
    def get_busy_machines(self) -> list:
        """获取所有忙碌机床"""
        return [machine_id for machine_id in self.current_states.keys() 
                if not self.is_machine_available(machine_id)]
