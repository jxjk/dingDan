"""
数控车床多订单宏变量管理与生产任务调度系统
主应用程序入口
"""

import os
import sys
import logging
import json
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config_manager import ConfigManager
from models.production_task import ProductionTask, TaskStatus, TaskPriority, MachineState
from services.file_monitor import FileMonitorManager, MachineStateMonitor
from services.material_checker import MaterialMappingManager, EnhancedMaterialChecker, MaterialInventoryManager
from services.task_scheduler import TaskScheduler
from services.ui_automation import AutomationManager, QRCodeScanner
from utils.logger import setup_logging


class CNCProductionSystem:
    """数控车床生产系统主控制器"""
    
    def __init__(self):
        # 初始化配置
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        # 设置日志
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)
        
        # 初始化服务组件
        self._initialize_services()
        
        # 系统状态
        self.is_running = False
        self.start_time = None
        
        self.logger.info("数控车床生产系统初始化完成")
    
    def _initialize_services(self):
        """初始化所有服务组件"""
        try:
            # 文件监控服务
            self.file_monitor = FileMonitorManager(self.config)
            self.machine_monitor = MachineStateMonitor(self.file_monitor)
            
            # 材料管理服务
            self.material_manager = MaterialMappingManager(self.config)
            self.material_checker = EnhancedMaterialChecker(self.config, self.material_manager)
            self.inventory_manager = MaterialInventoryManager(self.material_manager)
            
            # 任务调度服务
            self.task_scheduler = TaskScheduler(self.config, self.material_checker)
            
            # UI自动化服务
            self.automation_manager = AutomationManager(self.config)
            self.qr_scanner = QRCodeScanner(self.config)
            
            self.logger.info("所有服务组件初始化成功")
            
        except Exception as e:
            self.logger.error(f"服务组件初始化失败: {e}")
            raise
    
    def start_system(self):
        """启动生产系统"""
        if self.is_running:
            self.logger.warning("系统已在运行中")
            return
        
        try:
            self.is_running = True
            self.start_time = datetime.now()
            
            # 启动文件监控
            self.machine_monitor.start_monitoring(self._handle_machine_state_change)
            
            # 加载初始任务
            self._load_initial_tasks()
            
            # 启动调度循环
            self._start_scheduling_loop()
            
            self.logger.info("数控车床生产系统已启动")
            
        except Exception as e:
            self.logger.error(f"启动系统失败: {e}")
            self.is_running = False
    
    def stop_system(self):
        """停止生产系统"""
        if not self.is_running:
            self.logger.warning("系统未在运行")
            return
        
        try:
            self.is_running = False
            
            # 停止文件监控
            self.file_monitor.stop_monitoring()
            
            # 清理自动化资源
            self.automation_manager.cleanup()
            
            self.logger.info("数控车床生产系统已停止")
            
        except Exception as e:
            self.logger.error(f"停止系统失败: {e}")
    
    def _handle_machine_state_change(self, state_changes: dict):
        """处理机床状态变化"""
        for machine_id, change_info in state_changes.items():
            old_state = change_info['from']
            new_state = change_info['to']
            
            self.logger.info(f"机床 {machine_id} 状态变化: {old_state} -> {new_state}")
            
            # 更新任务调度器的机床状态
            machine_state = MachineState(
                machine_id=machine_id,
                current_state=new_state,
                current_material=self._get_machine_material(machine_id),
                last_update=datetime.now()
            )
            self.task_scheduler.update_machine_state(machine_id, machine_state)
            
            # 如果机床变为可用，触发任务调度
            if new_state.upper() in ['OFF', 'IDLE', 'STANDBY', 'READY']:
                self.logger.info(f"机床 {machine_id} 变为可用，触发任务调度")
                self._schedule_tasks()
    
    def _get_machine_material(self, machine_id: str) -> str:
        """获取机床当前材料"""
        # 这里可以从配置文件或数据库中获取机床的默认材料
        machine_materials = self.config.get('machine_default_materials', {})
        return machine_materials.get(machine_id, 'UNKNOWN')
    
    def _load_initial_tasks(self):
        """加载初始任务"""
        try:
            # 从配置文件加载示例任务
            sample_tasks = self.config.get('sample_tasks', [])
            
            for task_data in sample_tasks:
                task = ProductionTask(
                    task_id=task_data['task_id'],
                    instruction_id=task_data['instruction_id'],
                    product_model=task_data['product_model'],
                    material_spec=task_data['material_spec'],
                    order_quantity=task_data['order_quantity'],
                    priority=TaskPriority(task_data.get('priority', 'Normal')),
                    estimated_duration=task_data.get('estimated_duration', 60),
                    program_available=task_data.get('program_available', True)
                )
                
                self.task_scheduler.add_task(task)
                self.logger.info(f"加载初始任务: {task.task_id}")
            
            self.logger.info(f"共加载 {len(sample_tasks)} 个初始任务")
            
        except Exception as e:
            self.logger.error(f"加载初始任务失败: {e}")
    
    def _start_scheduling_loop(self):
        """启动调度循环"""
        import threading
        
        def scheduling_worker():
            while self.is_running:
                try:
                    self._schedule_tasks()
                    time.sleep(10)  # 每10秒调度一次
                except Exception as e:
                    self.logger.error(f"调度循环错误: {e}")
                    time.sleep(5)
        
        self.scheduling_thread = threading.Thread(target=scheduling_worker, daemon=True)
        self.scheduling_thread.start()
        self.logger.info("调度循环已启动")
    
    def _schedule_tasks(self):
        """执行任务调度"""
        try:
            assignments = self.task_scheduler.schedule_tasks()
            
            for task, machine_id in assignments:
                self.logger.info(f"任务 {task.task_id} 已分配到机床 {machine_id}")
                
                # 执行自动化流程
                self._execute_automation_workflow(task, machine_id)
                
        except Exception as e:
            self.logger.error(f"任务调度失败: {e}")
    
    def _execute_automation_workflow(self, task: ProductionTask, machine_id: str):
        """执行自动化工作流"""
        try:
            # 更新任务状态为运行中
            task.update_status(TaskStatus.RUNNING, f"开始在机床 {machine_id} 上运行")
            
            # 执行UI自动化
            automation_results = self.automation_manager.process_instruction(
                task.instruction_id, task.product_model)
            
            # 记录自动化结果
            task.notes = f"自动化结果: {automation_results}"
            
            # 如果所有系统都处理成功，标记任务完成
            if all(automation_results.values()):
                self.task_scheduler.complete_task(task.task_id)
                self.logger.info(f"任务 {task.task_id} 自动化流程完成")
            else:
                task.update_status(TaskStatus.ERROR, "自动化流程失败")
                self.logger.error(f"任务 {task.task_id} 自动化流程失败")
                
        except Exception as e:
            self.logger.error(f"执行自动化工作流失败: {e}")
            task.update_status(TaskStatus.ERROR, f"自动化工作流异常: {e}")
    
    def add_new_task(self, instruction_id: str, product_model: str, 
                    material_spec: str, order_quantity: int, 
                    priority: str = "Normal") -> str:
        """添加新任务"""
        try:
            # 生成任务ID
            task_id = f"TASK_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{instruction_id}"
            
            # 创建任务
            task = ProductionTask(
                task_id=task_id,
                instruction_id=instruction_id,
                product_model=product_model,
                material_spec=material_spec,
                order_quantity=order_quantity,
                priority=TaskPriority(priority)
            )
            
            # 添加到调度器
            self.task_scheduler.add_task(task)
            
            self.logger.info(f"新任务已添加: {task_id}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"添加新任务失败: {e}")
            raise
    
    def get_system_status(self) -> dict:
        """获取系统状态"""
        task_stats = self.task_scheduler.get_task_statistics()
        machine_utilization = self.task_scheduler.get_machine_utilization()
        
        return {
            'system_running': self.is_running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'task_statistics': task_stats,
            'machine_utilization': machine_utilization,
            'available_machines': self.machine_monitor.get_available_machines(),
            'busy_machines': self.machine_monitor.get_busy_machines()
        }
    
    def get_task_details(self, task_id: str) -> dict:
        """获取任务详情"""
        # 在所有任务队列中查找任务
        all_tasks = (self.task_scheduler.pending_tasks + 
                    list(self.task_scheduler.running_tasks.values()) + 
                    self.task_scheduler.completed_tasks)
        
        for task in all_tasks:
            if task.task_id == task_id:
                return task.to_dict()
        
        return None
    
    def scan_qr_code(self, qr_content: str) -> dict:
        """扫描二维码"""
        return self.qr_scanner.simulate_scan(qr_content)
    
    def get_material_stock_report(self) -> dict:
        """获取材料库存报告"""
        return self.inventory_manager.generate_stock_report()


def main():
    """主函数"""
    try:
        # 创建并启动系统
        system = CNCProductionSystem()
        system.start_system()
        
        print("数控车床生产系统已启动")
        print("按 Ctrl+C 停止系统")
        
        # 保持主线程运行
        while system.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在停止系统...")
        system.stop_system()
        print("系统已停止")
        
    except Exception as e:
        print(f"系统运行错误: {e}")
        logging.error(f"系统运行错误: {e}")


if __name__ == "__main__":
    main()
