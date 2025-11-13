"""
系统管理器模块
负责整个系统的协调和管理
"""

import logging
import time
from typing import Dict, List, Optional
from enum import Enum
from config.config_manager import get_config_manager
from services.material_checker import MaterialChecker
from services.task_scheduler import TaskScheduler
from services.task_executor import TaskExecutor
from services.file_monitor import FileMonitorManager
from services.ui_automation import UIAutomation
from models.production_task import ProductionTask, TaskStatus


class SystemStatus(Enum):
    """系统状态枚举"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class SystemManager:
    """系统管理器"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.logger = logging.getLogger(__name__)
        
        # 系统组件
        self.material_checker: Optional[MaterialChecker] = None
        self.task_scheduler: Optional[TaskScheduler] = None
        self.task_executor: Optional[TaskExecutor] = None  # 新增
        self.file_monitor: Optional[FileMonitorManager] = None
        self.ui_automation: Optional[UIAutomation] = None
        
        # 系统状态
        self.status = SystemStatus.INITIALIZING
        self.start_time = None
        self.error_count = 0
        self.is_initialized = False  # 添加初始化状态属性
        
        # 统计数据
        self.stats = {
            'tasks_processed': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'materials_checked': 0,
            'files_processed': 0
        }
    
    def initialize_system(self) -> bool:
        """初始化系统"""
        try:
            self.logger.info("开始初始化系统...")
            self.status = SystemStatus.INITIALIZING
            self.is_initialized = False  # 重置初始化状态
            
            # 初始化配置管理器
            if not self.config_manager.reload():
                self.logger.error("配置管理器初始化失败")
                return False
            
            # 初始化材料检查器
            self.material_checker = MaterialChecker(self.config_manager)
            self.logger.info("✅ 材料检查器初始化成功")
            
            # 初始化任务调度器
            self.task_scheduler = TaskScheduler(self.config_manager.config, self.material_checker)
            self.logger.info("✅ 任务调度器初始化成功")
            
            # 初始化文件监控器
            self.file_monitor = FileMonitorManager(self.config_manager)
            self.logger.info("✅ 文件监控器初始化成功")
            
            # 初始化UI自动化
            self.ui_automation = UIAutomation(self.config_manager)
            self.logger.info("✅ UI自动化初始化成功")
            
            # 初始化任务执行器
            self.task_executor = TaskExecutor(self.task_scheduler, self.ui_automation)
            self.logger.info("✅ 任务执行器初始化成功")
            
            # 更新系统状态
            self.status = SystemStatus.RUNNING
            self.start_time = time.time()
            self.is_initialized = True  # 设置初始化完成
            
            self.logger.info("🎉 系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"系统初始化失败: {e}")
            self.status = SystemStatus.ERROR
            self.is_initialized = False
            return False
    
    def add_new_task(self, instruction_id: str, product_model: str, 
                    material_spec: str, order_quantity: int, 
                    priority: str = "Normal") -> Optional[str]:
        """添加新任务"""
        try:
            if self.status != SystemStatus.RUNNING:
                self.logger.warning("系统未运行，无法添加任务")
                return None
            
            # 检查材料兼容性
            material_check = self.material_checker.check_material_compatibility(
                material_spec, order_quantity
            )
            
            if not material_check['compatible']:
                self.logger.error(f"材料不兼容: {material_spec}")
                return None
            
            # 生成任务ID
            import uuid
            task_id = f"TASK_{uuid.uuid4().hex[:8].upper()}"
            
            # 创建任务
            task = ProductionTask(
                task_id=task_id,
                instruction_id=instruction_id,
                product_model=product_model,
                material_spec=material_spec,
                order_quantity=order_quantity,
                priority=priority
            )
            
            # 添加到调度器
            if self.task_scheduler.add_task(task):
                self.stats['tasks_processed'] += 1
                self.logger.info(f"✅ 任务添加成功: {task_id}")
                return task_id
            else:
                self.logger.error("任务添加失败")
                return None
                
        except Exception as e:
            self.logger.error(f"添加新任务失败: {e}")
            return None
    
    def scan_qr_code(self, qr_text: str) -> Dict:
        """扫描二维码"""
        try:
            if self.status != SystemStatus.RUNNING:
                return {
                    'success': False,
                    'error': '系统未运行',
                    'parsed_data': {}
                }
            
            # 检查二维码材料
            material_check = self.material_checker.check_qr_material(qr_text, 1)
            
            if not material_check['material_found']:
                return {
                    'success': False,
                    'error': '未找到对应材料',
                    'parsed_data': {}
                }
            
            # 解析二维码数据
            parsed_data = self._parse_qr_data(qr_text, material_check['material_info'])
            
            return {
                'success': True,
                'error': None,
                'parsed_data': parsed_data,
                'material_info': material_check['material_info']
            }
            
        except Exception as e:
            self.logger.error(f"扫描二维码失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'parsed_data': {}
            }
    
    def _parse_qr_data(self, qr_text: str, material_info: Dict) -> Dict:
        """解析二维码数据"""
        # 简单的二维码解析逻辑
        # 实际应用中可能需要更复杂的解析
        return {
            'qr_text': qr_text,
            'material_name': material_info['材料名称'],
            'material_spec': material_info['材料规格'],
            'current_stock': material_info['库存数量'],
            'supplier': material_info.get('供应商', '未知'),
            'unit': material_info.get('单位', '未知')
        }
    
    def start_system(self) -> bool:
        """启动系统"""
        try:
            if self.status == SystemStatus.RUNNING:
                self.logger.info("系统已在运行中")
                return True
            
            if self.status == SystemStatus.ERROR:
                self.logger.info("尝试从错误状态恢复系统...")
                return self.initialize_system()
            
            # 启动文件监控
            if self.file_monitor:
                self.file_monitor.start_monitoring()
            
            # 启动任务执行器
            if self.task_executor:
                self.task_executor.start_execution()
            
            self.status = SystemStatus.RUNNING
            self.start_time = time.time()
            
            self.logger.info("🚀 系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            self.status = SystemStatus.ERROR
            return False
    
    def stop_system(self) -> bool:
        """停止系统"""
        try:
            if self.status == SystemStatus.STOPPED:
                self.logger.info("系统已停止")
                return True
            
            # 停止任务执行器
            if self.task_executor:
                self.task_executor.stop_execution()
            
            # 停止文件监控
            if self.file_monitor:
                self.file_monitor.stop_monitoring()
            
            self.status = SystemStatus.STOPPED
            
            self.logger.info("🛑 系统已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"系统停止失败: {e}")
            return False
    
    def pause_system(self) -> bool:
        """暂停系统"""
        try:
            if self.status != SystemStatus.RUNNING:
                self.logger.warning("系统未运行，无法暂停")
                return False
            
            # 暂停任务执行器
            if self.task_executor:
                self.task_executor.pause_execution()
            
            self.status = SystemStatus.PAUSED
            
            self.logger.info("⏸️ 系统已暂停")
            return True
            
        except Exception as e:
            self.logger.error(f"系统暂停失败: {e}")
            return False
    
    def resume_system(self) -> bool:
        """恢复系统"""
        try:
            if self.status != SystemStatus.PAUSED:
                self.logger.warning("系统未暂停，无法恢复")
                return False
            
            # 恢复任务执行器
            if self.task_executor:
                self.task_executor.resume_execution()
            
            self.status = SystemStatus.RUNNING
            
            self.logger.info("▶️ 系统已恢复")
            return True
            
        except Exception as e:
            self.logger.error(f"系统恢复失败: {e}")
            return False
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        uptime = 0
        if self.start_time:
            uptime = time.time() - self.start_time
        
        # 获取任务统计
        task_stats = {}
        if self.task_scheduler:
            task_stats = self.task_scheduler.get_task_statistics()
        
        # 获取材料统计
        material_stats = {}
        if self.material_checker:
            material_stats = self.material_checker.get_material_stock_report()
        
        # 获取任务执行器状态
        executor_stats = {}
        if self.task_executor:
            executor_stats = self.task_executor.get_execution_status()
        
        return {
            'system_status': self.status.value,
            'uptime': uptime,
            'error_count': self.error_count,
            'task_statistics': task_stats,
            'material_statistics': material_stats,
            'executor_statistics': executor_stats,  # 新增
            'system_statistics': self.stats
        }

    def get_task_list(self) -> List[Dict]:
        """获取任务列表"""
        if not self.task_scheduler:
            return []
        
        task_list = []
        
        # 添加待处理任务
        for task in self.task_scheduler.pending_tasks:
            # 安全地获取priority和status的值
            priority_value = getattr(task.priority, 'value', task.priority) if task.priority else 'Normal'
            status_value = getattr(task.status, 'value', task.status) if task.status else 'Pending'
            
            task_list.append({
                'task_id': task.task_id,
                'instruction_id': task.instruction_id,
                'product_model': task.product_model,
                'material_spec': task.material_spec,
                'order_quantity': task.order_quantity,
                'priority': priority_value,  # 确保 priority 是字符串
                'status': status_value,  # 确保 status 是字符串
                'created_at': task.create_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'create_time') and task.create_time else '未知',
                'create_time': task.create_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'create_time') and task.create_time else '未知',
                'assigned_machine': task.assigned_machine
            })
        
        # 添加运行中任务
        for task in self.task_scheduler.running_tasks.values():
            # 安全地获取priority和status的值
            priority_value = getattr(task.priority, 'value', task.priority) if task.priority else 'Normal'
            status_value = getattr(task.status, 'value', task.status) if task.status else 'Running'
            
            task_list.append({
                'task_id': task.task_id,
                'instruction_id': task.instruction_id,
                'product_model': task.product_model,
                'material_spec': task.material_spec,
                'order_quantity': task.order_quantity,
                'priority': priority_value,  # 确保 priority 是字符串
                'status': status_value,  # 确保 status 是字符串
                'created_at': task.create_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'create_time') and task.create_time else '未知',
                'create_time': task.create_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'create_time') and task.create_time else '未知',
                'assigned_machine': task.assigned_machine
            })
        
        # 添加已完成任务
        for task in self.task_scheduler.completed_tasks:
            # 安全地获取priority和status的值
            priority_value = getattr(task.priority, 'value', task.priority) if task.priority else 'Normal'
            status_value = getattr(task.status, 'value', task.status) if task.status else 'Completed'
            
            task_list.append({
                'task_id': task.task_id,
                'instruction_id': task.instruction_id,
                'product_model': task.product_model,
                'material_spec': task.material_spec,
                'order_quantity': task.order_quantity,
                'priority': priority_value,  # 确保 priority 是字符串
                'status': status_value,  # 确保 status 是字符串
                'created_at': task.create_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'create_time') and task.create_time else '未知',
                'create_time': task.create_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'create_time') and task.create_time else '未知',
                'assigned_machine': task.assigned_machine
            })
        
        return task_list 
        
    def get_material_list(self) -> List[Dict]:
        """获取材料列表"""
        if not self.material_checker:
            return []
        
        return self.material_checker.get_all_materials()
    
    def search_materials(self, search_term: str) -> List[Dict]:
        """搜索材料"""
        if not self.material_checker:
            return []
        
        return self.material_checker.search_materials(search_term)
    
    def add_new_material(self, material_data: Dict) -> bool:
        """添加新材料"""
        if not self.material_checker:
            return False
        
        return self.material_checker.add_new_material(material_data)
    
    def update_material_stock(self, material_spec: str, new_stock: int) -> bool:
        """更新材料库存"""
        if not self.material_checker:
            return False
        
        return self.material_checker.update_material_stock(material_spec, new_stock)
    
    def execute_ui_operation(self, operation: str, **kwargs) -> Dict:
        """执行UI操作"""
        if not self.ui_automation:
            return {'success': False, 'error': 'UI自动化未初始化'}
        
        try:
            return self.ui_automation.execute_operation(operation, **kwargs)
        except Exception as e:
            self.logger.error(f"UI操作执行失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_file_status(self) -> Dict:
        """检查文件状态"""
        if not self.file_monitor:
            return {'status': 'error', 'message': '文件监控器未初始化'}
        
        return self.file_monitor.check_file_status()
    
    def get_system_info(self) -> Dict:
        """获取系统信息"""
        from utils.system_utils import get_system_info
        
        system_info = get_system_info()
        system_status = self.get_system_status()
        
        return {
            'system': system_info,
            'status': system_status,
            'config': {
                'system_name': self.config_manager.get('system.name'),
                'version': self.config_manager.get('system.version'),
                'environment': self.config_manager.get('system.environment')
            }
        }


# 全局系统管理器实例
_system_manager: Optional[SystemManager] = None


def get_system_manager() -> SystemManager:
    """获取全局系统管理器实例"""
    global _system_manager
    if _system_manager is None:
        _system_manager = SystemManager()
    return _system_manager