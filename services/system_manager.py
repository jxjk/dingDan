"""
系统管理器模块
负责整个系统的协调和管理
"""

import logging
import time
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import asyncio
import functools
from config.config_manager import get_config_manager
from services.material_checker import MaterialChecker
from services.task_scheduler import TaskScheduler
from services.task_executor import TaskExecutor
from services.file_monitor import FileMonitorManager
from services.ui_automation import UIAutomation
from models.production_task import ProductionTask, TaskStatus, TaskPriority, MachineState


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
        """初始化系统管理器"""
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        self.is_running = False
        
        # 统计信息
        self.stats = {
            'tasks_processed': 0,
            'files_monitored': 0,
            'errors_occurred': 0
        }
        
        # 配置管理器
        self.config_manager = get_config_manager()
        
        # 初始化核心服务
        self.material_checker = None
        self.task_scheduler = None
        self.task_executor = None
        self.file_monitor_manager = None
        self.ui_automation = None
        
        # 定时调度相关
        self.auto_schedule_timer = None
        self.auto_schedule_interval = 60  # 60秒
        
        # 系统状态
        self.status = SystemStatus.INITIALIZING
    
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
            
            # 获取状态映射配置
            self.status_mapping = self.config_manager.get_machine_status_mapping()
            self.available_states = self.config_manager.get_available_states()
            
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
            
            # 启动定时自动调度
            self._start_auto_scheduling()
            
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
    
    def _start_auto_scheduling(self):
        """启动定时自动调度"""
        def run_auto_schedule():
            while self.is_running:
                try:
                    time.sleep(self.auto_schedule_interval)
                    if self.is_running:
                        self.logger.debug("执行定时自动调度")
                        self.task_scheduler.schedule_tasks()
                except Exception as e:
                    self.logger.error(f"定时自动调度出错: {e}")
        
        self.is_running = True
        self.auto_schedule_timer = threading.Thread(target=run_auto_schedule, daemon=True)
        self.auto_schedule_timer.start()
        self.logger.info("定时自动调度已启动，每60秒执行一次")
    
    def _stop_auto_scheduling(self):
        """停止定时自动调度"""
        self.is_running = False
        if self.auto_schedule_timer:
            self.auto_schedule_timer.join()
        self.logger.info("定时自动调度已停止")
    
    def add_new_task(self, instruction_id: str, product_model: str, 
                     material_spec: str, order_quantity: int, 
                     priority: str = "Normal") -> Optional[str]:
        """添加新任务"""
        try:
            self.logger.info(f"开始添加新任务: 指示书={instruction_id}, 产品={product_model}, 材料={material_spec}, 数量={order_quantity}")
            
            # 检查材料是否在材料库中存在
            material_exists = self._check_material_exists(material_spec)
            if not material_exists:
                self.logger.warning(f"材料 {material_spec} 在材料库中不存在")
                # 提示用户确认是否继续添加任务
                print(f"⚠️  警告: 材料 '{material_spec}' 在材料库中不存在。")
                user_input = input("是否继续添加任务? 输入 'yes' 确认，其他任意键取消: ").strip().lower()
                if user_input != 'yes':
                    self.logger.info("用户取消添加任务")
                    return None
            
            # 验证优先级
            priority_map = {
                'normal': 'NORMAL',
                'high': 'HIGH', 
                'urgent': 'URGENT'
            }
            
            priority_key = priority.lower()
            if priority_key not in priority_map:
                self.logger.warning(f"无效的优先级: {priority}, 使用默认优先级 NORMAL")
                priority_key = 'normal'
            
            priority_enum = priority_map[priority_key]
            
            # 生成临时任务ID用于材料检查
            temp_task_id = f"TASK_{uuid.uuid4().hex[:8].upper()}"
            temp_task = ProductionTask(
                task_id=temp_task_id,
                instruction_id=instruction_id,
                product_model=product_model,
                material_spec=material_spec,
                order_quantity=order_quantity,
                priority=priority_enum
            )
            
            # 获取第一台可用机床用于材料检查，如果没有可用机床，则使用第一台机床
            available_machines = self.task_scheduler.get_available_machines()
            all_machines = list(self.task_scheduler.machine_states.keys())
            
            machine_id = None
            current_material = ""
            
            # 优先使用可用机床进行材料检查
            if available_machines:
                machine_id = available_machines[0]
            elif all_machines:
                # 如果没有可用机床，使用任意一台机床
                machine_id = all_machines[0]
            
            # 获取机床当前材料
            if machine_id and machine_id in self.task_scheduler.machine_states:
                machine_state = self.task_scheduler.machine_states.get(machine_id)
                current_material = machine_state.current_material if machine_state else ""
                self.logger.debug(f"使用机床 {machine_id} 进行材料检查，当前材料: {current_material}")
            else:
                # 如果没有机床信息，允许材料检查通过（材料更换成本会体现在调度评分中）
                self.logger.warning("未找到机床信息，将使用空材料进行检查")
                current_material = ""
            
            # 检查材料兼容性
            check_machine_id = machine_id or "DEFAULT_CNC"
            material_check = self.material_checker.check_material_compatibility(
                temp_task, check_machine_id, current_material
            )
            
            # 即使材料不完全匹配，只要兼容就允许添加任务
            # 材料更换成本会在调度时考虑
            if not material_check['compatible'] and current_material != "":
                self.logger.warning(f"材料不兼容: {material_spec}，但任务仍可添加")
            
            # 生成任务ID
            task_id = temp_task_id
            
            # 创建任务
            task = ProductionTask(
                task_id=task_id,
                instruction_id=instruction_id,
                product_model=product_model,
                material_spec=material_spec,
                order_quantity=order_quantity,
                priority=priority_enum
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
    
    def _check_material_exists(self, material_spec: str) -> bool:
        """检查材料是否在材料库中存在"""
        try:
            # 获取所有材料
            all_materials = self.material_checker.get_all_materials()
            
            # 检查是否有匹配的材料规格
            for material in all_materials:
                if material.get('材料规格') == material_spec:
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"检查材料存在性失败: {e}")
            # 出错时默认返回True，避免阻止用户添加任务
            return True
    
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
            
            # 启动机床状态监控
            self._start_machine_monitoring()
            
            self.status = SystemStatus.RUNNING
            self.start_time = time.time()
            
            self.logger.info("🚀 系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            self.status = SystemStatus.ERROR
            return False
    
    def stop_system(self):
        """停止系统"""
        self.logger.info("正在停止系统...")
        self.is_running = False
        self.status = SystemStatus.STOPPED
        
        # 停止定时自动调度
        self._stop_auto_scheduling()
        
        # 停止文件监控
        if self.file_monitor_manager:
            self.file_monitor_manager.stop_monitoring()
        
        # 停止任务执行器
        if self.task_executor:
            self.task_executor.stop()
        
        self.logger.info("✅ 系统已停止")
    
    def _start_machine_monitoring(self):
        """启动机床状态监控"""
        if not self.machine_monitor_running:
            self.machine_monitor_running = True
            self.machine_monitor_thread = threading.Thread(
                target=self._machine_monitor_loop, 
                daemon=True
            )
            self.machine_monitor_thread.start()
            self.logger.info("机床状态监控已启动")
    
    def _stop_machine_monitoring(self):
        """停止机床状态监控"""
        self.machine_monitor_running = False
        if self.machine_monitor_thread:
            self.machine_monitor_thread.join(timeout=5)
        self.logger.info("机床状态监控已停止")
    
    def _machine_monitor_loop(self):
        """机床状态监控循环"""
        # 添加自动调度计数器，用于实现每分钟自动调度
        auto_schedule_counter = 0
        auto_schedule_interval = 60  # 60秒 = 1分钟
        
        while self.machine_monitor_running:
            try:
                # 更新机床状态
                self._update_machine_states()
                
                # 尝试调度任务（原有的基于待处理任务的调度）
                if self.task_scheduler and self.task_scheduler.pending_tasks:
                    self.logger.debug("尝试调度任务")
                    self.task_scheduler.schedule_tasks()
                
                # 每分钟自动执行一次调度（新增功能）
                auto_schedule_counter += self.machine_monitor_interval
                if auto_schedule_counter >= auto_schedule_interval:
                    self.logger.debug("执行定时自动调度")
                    if self.task_scheduler:
                        self.task_scheduler.schedule_tasks()
                    auto_schedule_counter = 0  # 重置计数器
                
                # 等待下一次更新
                for _ in range(self.machine_monitor_interval):
                    if not self.machine_monitor_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"机床状态监控错误: {e}")
                time.sleep(self.machine_monitor_interval)
    
    def _update_machine_states(self):
        """更新机床状态"""
        if not self.task_scheduler:
            self.logger.debug("任务调度器未初始化，无法更新机床状态")
            return
        
        # 从配置中获取机床列表
        machines_config = self.config_manager.get('machines', {})
        self.logger.debug(f"配置中的机床数量: {len(machines_config)}")
        
        # 计数器用于跟踪成功更新的机床数量
        updated_machines = 0
        
        # 为每台机床更新状态
        for machine_id, machine_info in machines_config.items():
            try:
                self.logger.debug(f"处理机床 {machine_id}")
                # 使用配置中的默认状态
                self.logger.debug("使用默认状态")
                machine_state = MachineState(
                    machine_id=machine_id,
                    current_state="IDLE",  # 默认空闲状态
                    current_material=machine_info.get('material', ''),
                    capabilities=machine_info.get('capabilities', []),
                    current_task=None,
                    last_update=datetime.now()
                )
                self.task_scheduler.update_machine_state(machine_id, machine_state)
                self.logger.info(f"✅ 使用默认状态更新机床 {machine_id}: IDLE")
                updated_machines += 1
                    
            except Exception as e:
                self.logger.error(f"更新机床 {machine_id} 状态失败: {e}")
                # 即使出错也尝试设置基础状态，确保机床可用
                self.task_scheduler.update_machine_state(
                    machine_id, 
                    MachineState(
                        machine_id=machine_id,
                        current_state="IDLE",
                        current_material=machine_info.get('material', '') if machine_info else '',
                        capabilities=[],
                        current_task=None,
                        last_update=datetime.now()
                    )
                )
                self.logger.info(f"✅ 已为机床 {machine_id} 设置基础状态")
                updated_machines += 1
        
        self.logger.info(f"总共更新了 {updated_machines} 台机床的状态")
        
        # 打印当前所有机床状态以供调试
        self.logger.debug("当前所有机床状态:")
        for machine_id, state in self.task_scheduler.machine_states.items():
            self.logger.debug(f"  机床 {machine_id}: {state.current_state}")
    
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
        # 在获取状态前自动刷新机床状态
        self._refresh_machine_states_for_status()
        
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
    
    def _refresh_machine_states_for_status(self):
        """为状态获取刷新机床状态"""
        try:
            # 更新机床状态以确保显示最新信息
            self._update_machine_states()
            self.logger.debug("为状态获取刷新机床状态完成")
        except Exception as e:
            self.logger.error(f"为状态获取刷新机床状态时出错: {e}")
    
    def get_task_list(self) -> List[Dict]:
        """获取任务列表"""
        if not self.task_scheduler:
            self.logger.debug("任务调度器未初始化")
            return []
        
        self.logger.debug("获取任务列表")
        task_list = []
        
        # 添加待处理任务
        pending_count = len(self.task_scheduler.pending_tasks)
        self.logger.debug(f"待处理任务数: {pending_count}")
        for task in self.task_scheduler.pending_tasks:
            # 安全地获取priority和status的值
            priority_value = getattr(task.priority, 'value', task.priority) if task.priority else 'Normal'
            status_value = getattr(task.status, 'value', task.status) if task.status else 'Pending'
            
            task_info = {
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
            }
            task_list.append(task_info)
            self.logger.debug(f"待处理任务详情: {task_info}")
        
        # 添加运行中任务
        running_count = len(self.task_scheduler.running_tasks)
        self.logger.debug(f"运行中任务数: {running_count}")
        for task in self.task_scheduler.running_tasks.values():
            # 安全地获取priority和status的值
            priority_value = getattr(task.priority, 'value', task.priority) if task.priority else 'Normal'
            status_value = getattr(task.status, 'value', task.status) if task.status else 'Running'
            
            task_info = {
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
            }
            task_list.append(task_info)
            self.logger.debug(f"运行中任务详情: {task_info}")
        
        # 添加已完成任务
        completed_count = len(self.task_scheduler.completed_tasks)
        self.logger.debug(f"已完成任务数: {completed_count}")
        for task in self.task_scheduler.completed_tasks:
            # 安全地获取priority和status的值
            priority_value = getattr(task.priority, 'value', task.priority) if task.priority else 'Normal'
            status_value = getattr(task.status, 'value', task.status) if task.status else 'Completed'
            
            task_info = {
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
            }
            task_list.append(task_info)
            self.logger.debug(f"已完成任务详情: {task_info}")
        
        self.logger.debug(f"总共返回任务数: {len(task_list)}")
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
    
    def _initialize_cnc_connector(self):
        """初始化CNC连接器"""
        # 根据新需求，不再需要CNC连接器
        self.cnc_connector = None
        self.logger.info("根据新需求，不初始化CNC连接器")
    
    def _connect_all_machines(self):
        """主动连接所有配置的机床"""
        # 根据新需求，不再需要连接实际机床
        self.logger.info("根据新需求，不连接实际机床")

# 全局系统管理器实例
_system_manager: Optional[SystemManager] = None


def get_system_manager() -> SystemManager:
    """获取全局系统管理器实例"""
    global _system_manager
    if _system_manager is None:
        _system_manager = SystemManager()
    return _system_manager