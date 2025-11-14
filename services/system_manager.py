"""
系统管理器模块
负责整个系统的协调和管理
"""

import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
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
        
        # 状态映射配置
        self.status_mapping = self.config_manager.get_machine_status_mapping()
        self.available_states = self.config_manager.get_available_states()
        
        # 机床状态更新线程
        self.machine_monitor_thread: Optional[threading.Thread] = None
        self.machine_monitor_running = False
        self.machine_monitor_interval = 10  # 默认10秒更新一次机床状态
        
        # CNC连接器
        self.cnc_connector = None
        try:
            from cnc_machine_connector import CNCMachineManager
            self.cnc_connector = CNCMachineManager()
        except ImportError:
            self.logger.warning("CNC连接器不可用")
    
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
            
            # 清理之前的CNC连接（如果存在）
            if self.cnc_connector:
                self.cnc_connector.disconnect_all_machines()
            
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
            
            # 主动连接所有配置的机床
            self._connect_all_machines()
            
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
            
            # 将priority字符串转换为TaskPriority枚举
            try:
                priority_enum = TaskPriority[priority.upper()]
            except KeyError:
                self.logger.warning(f"无效的优先级: {priority}, 使用默认优先级 NORMAL")
                priority_enum = TaskPriority.NORMAL
            
            # 创建临时任务对象用于材料检查
            import uuid
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
            
            if available_machines:
                machine_id = available_machines[0]
            elif all_machines:
                machine_id = all_machines[0]
            else:
                self.logger.warning("系统中没有配置任何机床，使用默认机床信息进行材料检查")
                machine_id = "DEFAULT_CNC"
            
            # 获取机床当前材料
            if machine_id in self.task_scheduler.machine_states:
                machine_state = self.task_scheduler.machine_states.get(machine_id)
                current_material = machine_state.current_material if machine_state else ""
            else:
                # 如果是默认机床，从配置中获取材料信息
                machine_config = self.config_manager.get(f'machines.{machine_id}', {})
                current_material = machine_config.get('material', '') if machine_config else ""
            
            # 检查材料兼容性
            material_check = self.material_checker.check_material_compatibility(
                temp_task, machine_id, current_material
            )
            
            if not material_check['compatible']:
                self.logger.error(f"材料不兼容: {material_spec}")
                return None
            
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
    
    def stop_system(self) -> bool:
        """停止系统"""
        try:
            if self.status == SystemStatus.STOPPED:
                self.logger.info("系统已停止")
                return True
            
            # 停止机床状态监控
            self._stop_machine_monitoring()
            
            # 断开所有CNC连接
            if self.cnc_connector:
                self.cnc_connector.disconnect_all_machines()
                self.logger.info("所有CNC连接已断开")
            
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
        while self.machine_monitor_running:
            try:
                # 更新机床状态
                self._update_machine_states()
                
                # 尝试调度任务
                if self.task_scheduler and self.task_scheduler.pending_tasks:
                    self.logger.debug("尝试调度任务")
                    self.task_scheduler.schedule_tasks()
                
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
                # 如果有CNC连接器，尝试获取实际状态
                if self.cnc_connector:
                    host = machine_info.get('ip_address', '127.0.0.1')
                    port = machine_info.get('port', 8193)
                    self.logger.debug(f"机床 {machine_id} 连接信息: {host}:{port}")
                    
                    # 检查是否已连接到该机床
                    is_connected = self.cnc_connector.is_machine_connected(host, port)
                    self.logger.debug(f"机床 {machine_id} 连接状态: {is_connected}")
                    
                    # 如果没有连接，则尝试连接
                    if not is_connected:
                        self.logger.debug(f"正在连接到机床 {machine_id} ({host}:{port})")
                        connection_success = self.cnc_connector.connect_machine(host, port)
                        self.logger.debug(f"机床 {machine_id} 连接结果: {connection_success}")
                    else:
                        connection_success = True
                    
                    if connection_success:
                        # 获取机床状态
                        status_response = self.cnc_connector.get_machine_status(host, port)
                        self.logger.debug(f"机床 {machine_id} 状态响应: {status_response}")
                        if status_response and status_response.get("success"):
                            status_data = status_response["data"]
                            raw_status = status_data.get("status", "UNKNOWN")
                            
                            # 映射到系统内部状态
                            internal_status = self.map_machine_status(raw_status)
                            self.logger.debug(f"机床 {machine_id} 原始状态: {raw_status}, 映射后状态: {internal_status}")
                            
                            # 创建机床状态对象
                            machine_state = MachineState(
                                machine_id=machine_id,
                                current_state=internal_status,
                                current_material=machine_info.get('material', ''),
                                capabilities=machine_info.get('capabilities', []),
                                current_task=None,
                                last_update=datetime.now()
                            )
                            
                            # 更新任务调度器中的机床状态
                            self.task_scheduler.update_machine_state(machine_id, machine_state)
                            self.logger.info(f"✅ 更新机床 {machine_id} 状态: {internal_status}")
                            updated_machines += 1
                        else:
                            # 如果无法获取状态，设置为默认空闲状态
                            self.logger.warning(f"无法获取机床 {machine_id} 状态，设置为默认 IDLE 状态")
                            machine_state = MachineState(
                                machine_id=machine_id,
                                current_state="IDLE",
                                current_material=machine_info.get('material', ''),
                                capabilities=machine_info.get('capabilities', []),
                                current_task=None,
                                last_update=datetime.now()
                            )
                            self.task_scheduler.update_machine_state(machine_id, machine_state)
                            updated_machines += 1
                    else:
                        self.logger.warning(f"连接机床 {machine_id} ({host}:{port}) 失败")
                        # 即使连接失败，也要确保机床状态被设置为IDLE（根据容错规范）
                        machine_state = MachineState(
                            machine_id=machine_id,
                            current_state="IDLE",  # 改为IDLE而不是UNKNOWN，确保机床可用
                            current_material=machine_info.get('material', ''),
                            capabilities=machine_info.get('capabilities', []),
                            current_task=None,
                            last_update=datetime.now()
                        )
                        self.task_scheduler.update_machine_state(machine_id, machine_state)
                        updated_machines += 1
                else:
                    # 如果没有连接器，使用配置中的默认状态
                    self.logger.debug("未检测到CNC连接器，使用默认状态")
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
                # 即使出错也要确保机床状态被设置，避免任务调度器认为没有机床
                machine_state = MachineState(
                    machine_id=machine_id,
                    current_state="IDLE",  # 改为IDLE而不是UNKNOWN，确保机床可用
                    current_material=machine_info.get('material', ''),
                    capabilities=machine_info.get('capabilities', []),
                    current_task=None,
                    last_update=datetime.now()
                )
                self.task_scheduler.update_machine_state(machine_id, machine_state)
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
    
    def map_machine_status(self, source_status: str, source_system: str = "cnc_simulator") -> str:
        """将不同系统的机床状态映射到系统内部状态"""
        # 获取状态映射配置
        status_mapping = self.config_manager.get_machine_status_mapping(source_system)
        
        # 映射状态，如果找不到映射则返回原状态
        return status_mapping.get(source_status.upper(), source_status.upper())
    
    def is_machine_available(self, machine_status: str) -> bool:
        """检查机床是否可用（可以接受任务）"""
        internal_status = self.map_machine_status(machine_status)
        return internal_status in self.available_states
    
    def _connect_all_machines(self):
        """主动连接所有配置的机床"""
        if not self.cnc_connector:
            self.logger.warning("CNC连接器不可用，无法连接机床")
            return
        
        machines_config = self.config_manager.get('machines', {})
        if not machines_config:
            self.logger.info("配置中未定义任何机床")
            return
        
        self.logger.info(f"尝试连接 {len(machines_config)} 台机床...")
        
        for machine_id, machine_info in machines_config.items():
            host = machine_info.get('ip_address', '127.0.0.1')
            port = machine_info.get('port', 8193)
            
            self.logger.debug(f"正在连接机床 {machine_id} ({host}:{port})")
            connection_success = self.cnc_connector.connect_machine(host, port)
            
            # 禁用实时状态显示以避免干扰用户输入
            machine_key = f"{host}:{port}"
            if machine_key in self.cnc_connector.clients:
                self.cnc_connector.clients[machine_key].show_realtime_status = False
            
            if connection_success:
                self.logger.info(f"✅ 成功连接到机床 {machine_id}")
            else:
                self.logger.warning(f"❌ 连接机床 {machine_id} 失败")
                
        self.logger.info("机床连接尝试完成")


# 全局系统管理器实例
_system_manager: Optional[SystemManager] = None


def get_system_manager() -> SystemManager:
    """获取全局系统管理器实例"""
    global _system_manager
    if _system_manager is None:
        _system_manager = SystemManager()
    return _system_manager