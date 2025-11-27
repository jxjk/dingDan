"""
任务执行服务
负责逐条执行生产任务，管理任务状态和进度
"""

import logging
import time
import threading
import csv
import os
from typing import Dict, List, Optional
from datetime import datetime

from models.production_task import ProductionTask, TaskStatus
from services.task_scheduler import TaskScheduler
from services.ui_automation import UIAutomation
from config.config_manager import get_config_manager


class TaskExecutor:
    """任务执行器"""
    
    def __init__(self, task_scheduler: TaskScheduler, ui_automation: UIAutomation):
        self.task_scheduler = task_scheduler
        self.ui_automation = ui_automation
        self.logger = logging.getLogger(__name__)
        
        # 获取配置管理器
        self.config_manager = get_config_manager()
        
        # 执行状态
        self.is_running = False
        self.execution_thread: Optional[threading.Thread] = None
        self.current_task: Optional[ProductionTask] = None
        
        # 执行配置
        self.execution_interval = 5  # 执行间隔(秒)
        self.max_retries = 3
        
        # 执行统计
        self.execution_stats = {
            'tasks_executed': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_execution_time': 0
        }
    
    def start_execution(self):
        """开始任务执行"""
        if self.is_running:
            self.logger.warning("任务执行器已在运行中")
            return
        
        self.is_running = True
        self.execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.execution_thread.start()
        self.logger.info("任务执行器已启动")
    
    def stop_execution(self):
        """停止任务执行"""
        self.is_running = False
        if self.execution_thread:
            self.execution_thread.join(timeout=5)
        self.logger.info("任务执行器已停止")
    
    def _execution_loop(self):
        """任务执行循环"""
        while self.is_running:
            try:
                # 检查是否有待执行的任务
                if self._has_ready_tasks():
                    self._execute_next_task()
                else:
                    # 没有任务时等待
                    time.sleep(self.execution_interval)
                    
            except Exception as e:
                self.logger.error(f"任务执行循环错误: {e}")
                time.sleep(self.execution_interval)
    
    def _has_ready_tasks(self) -> bool:
        """检查是否有就绪的任务"""
        # 检查运行中的任务
        ready_tasks = 0
        for task in self.task_scheduler.running_tasks.values():
            if task.status == TaskStatus.READY:
                ready_tasks += 1
        
        self.logger.debug(f"发现 {ready_tasks} 个就绪任务")
        
        if ready_tasks > 0:
            return True
        
        # 尝试调度新任务
        self.logger.debug("尝试调度新任务")
        pending_count = len(self.task_scheduler.pending_tasks)
        self.logger.debug(f"当前待处理任务数: {pending_count}")
        
        # 获取可用机床信息
        available_machines = self.task_scheduler.get_available_machines()
        self.logger.debug(f"当前可用机床: {available_machines}")
        
        scheduled_tasks = self.task_scheduler.schedule_tasks()
        scheduled_count = len(scheduled_tasks)
        self.logger.debug(f"调度了 {scheduled_count} 个新任务")
        return scheduled_count > 0
    
    def _execute_next_task(self):
        """执行下一个任务"""
        try:
            self.logger.debug("开始执行下一个任务")
            # 查找就绪状态的任务
            ready_task = None
            for task in self.task_scheduler.running_tasks.values():
                self.logger.debug(f"检查任务 {task.task_id} 状态: {task.status}")
                if task.status == TaskStatus.READY:
                    ready_task = task
                    break
            
            if not ready_task:
                self.logger.debug("没有就绪的任务")
                return
            
            # 设置当前任务
            self.current_task = ready_task
            self.logger.info(f"开始执行任务: {ready_task.task_id}")
            
            # 更新任务状态为运行中
            ready_task.update_status(TaskStatus.RUNNING, "开始执行")
            self.logger.debug(f"任务 {ready_task.task_id} 状态已更新为: {ready_task.status}")
            
            # 执行任务
            execution_success = self._execute_task(ready_task)
            
            if execution_success:
                # 标记任务完成
                self.task_scheduler.complete_task(ready_task.task_id)
                self.execution_stats['tasks_completed'] += 1
                self.logger.info(f"任务 {ready_task.task_id} 执行完成")
            else:
                # 任务执行失败
                ready_task.update_status(TaskStatus.ERROR, "执行失败")
                self.execution_stats['tasks_failed'] += 1
                self.logger.error(f"任务 {ready_task.task_id} 执行失败")
            
            self.execution_stats['tasks_executed'] += 1
            self.current_task = None
            
        except Exception as e:
            self.logger.error(f"执行任务失败: {e}")
            if self.current_task:
                self.current_task.update_status(TaskStatus.ERROR, f"执行异常: {e}")
                self.current_task = None
    
    def _execute_task(self, task: ProductionTask) -> bool:
        """执行具体任务"""
        try:
            start_time = time.time()
            self.logger.info(f"执行任务 {task.task_id}: {task.product_model} x {task.order_quantity}")
            
            # 根据系统构想，通过UI自动化将任务信息输入到DNC系统
            if not self._input_task_to_dnc(task):
                self.logger.warning(f"任务 {task.task_id} 输入DNC系统失败，但仍继续执行")
            
            # 根据新需求，读取平板IP对应的CSV文件，获取机床状态
            # 并输出以平板IP地址命名的txt文件
            if not self._process_task_to_tablet(task):
                self.logger.error(f"任务 {task.task_id} 处理失败")
                return False
            
            execution_time = time.time() - start_time
            self.execution_stats['total_execution_time'] += execution_time
            
            self.logger.info(f"任务 {task.task_id} 执行成功，耗时: {execution_time:.2f}秒")
            return True
            
        except Exception as e:
            self.logger.error(f"任务 {task.task_id} 执行异常: {e}")
            return False
    
    def _input_task_to_dnc(self, task: ProductionTask) -> bool:
        """通过UI自动化将任务输入到DNC系统"""
        try:
            self.logger.info(f"通过UI自动化将任务 {task.task_id} 输入到DNC系统")
            
            # 准备任务信息字典
            task_info = {
                'task_id': task.task_id,
                'instruction_id': task.instruction_id,
                'product_model': task.product_model,
                'material_spec': task.material_spec,
                'order_quantity': task.order_quantity,
                'assigned_machine': task.assigned_machine,
                'priority': str(task.priority) if task.priority else 'Normal'
            }
            
            # 执行UI操作
            result = self.ui_automation.execute_operation(
                "process_instruction",
                instruction_id=task.instruction_id,
                model_number=task.product_model,
                task_info=task_info
            )
            
            if result['success']:
                self.logger.info(f"任务 {task.task_id} 成功输入到DNC系统")
                return True
            else:
                self.logger.error(f"任务 {task.task_id} 输入到DNC系统失败: {result.get('error', '未知错误')}")
                return False
                
        except Exception as e:
            self.logger.error(f"输入任务到DNC系统时出错: {e}")
            return False

    def _process_task_to_tablet(self, task: ProductionTask) -> bool:
        """处理任务到平板"""
        try:
            # 获取机床配置信息
            machines_config = self.config_manager.get('machines', {})
            
            # 查找分配给该任务的机床
            assigned_machine_id = task.assigned_machine
            if not assigned_machine_id:
                self.logger.error(f"任务 {task.task_id} 未分配机床")
                return False
            
            if assigned_machine_id not in machines_config:
                self.logger.error(f"未找到机床 {assigned_machine_id} 的配置信息")
                return False
            
            machine_info = machines_config[assigned_machine_id]
            tablet_ip = machine_info.get('tablet_ip')
            if not tablet_ip:
                self.logger.error(f"机床 {assigned_machine_id} 未配置平板IP")
                return False
            
            # 读取平板IP对应的CSV文件，掌握机床状态
            csv_file_path = f"monitoring/{tablet_ip}.csv"
            if os.path.exists(csv_file_path):
                with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    # 读取CSV内容以获取机床状态
                    rows = list(reader)
                    self.logger.info(f"从 {csv_file_path} 读取到 {len(rows)} 行数据")
            else:
                self.logger.warning(f"未找到CSV文件: {csv_file_path}")
            
            # 创建以平板IP地址命名的txt文件
            txt_file_path = f"monitoring/{tablet_ip}.txt"
            
            # 内容格式：指示书编号@型号@数量
            content = f"{task.instruction_id}@{task.product_model}@{task.order_quantity}"
            
            # 写入文件（只有一行内容）
            with open(txt_file_path, 'w', encoding='utf-8') as txtfile:
                txtfile.write(content)
            
            self.logger.info(f"已创建文件 {txt_file_path}，内容: {content}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理任务到平板时出错: {e}")
            return False
    
    def _monitor_progress(self, task: ProductionTask) -> bool:
        """监控加工进度"""
        try:
            self.logger.info(f"监控任务进度: {task.product_model}")
            
            # 模拟任务处理过程
            total_steps = task.order_quantity
            for step in range(total_steps):
                if not self.is_running:
                    self.logger.warning("任务执行器已停止，中断任务处理")
                    return False
                
                # 更新完成数量
                task.completed_quantity = step + 1
                
                # 模拟处理时间
                time.sleep(0.1)
                
                # 记录进度
                progress = (step + 1) / total_steps * 100
                if (step + 1) % 5 == 0 or step == total_steps - 1:
                    self.logger.info(f"任务处理进度: {progress:.1f}% ({step + 1}/{total_steps})")
            
            self.logger.info("任务处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"任务处理监控失败: {e}")
            return False
    
    def _prepare_material(self, task: ProductionTask) -> bool:
        """准备材料"""
        try:
            self.logger.info(f"准备材料: {task.material_spec}")
            
            # 模拟材料准备过程
            time.sleep(0.5)
            
            # 更新材料检查状态
            task.material_check = True
            self.logger.info(f"材料 {task.material_spec} 准备完成")
            return True
            
        except Exception as e:
            self.logger.error(f"材料准备失败: {e}")
            return False
    
    def _load_program(self, task: ProductionTask) -> bool:
        """加载加工程序"""
        try:
            self.logger.info(f"加载程序: {task.program_name or '默认程序'}")
            
            # 模拟程序加载过程
            time.sleep(0.5)
            
            # 更新程序可用状态
            task.program_available = True
            self.logger.info("程序加载完成")
            return True
            
        except Exception as e:
            self.logger.error(f"程序加载失败: {e}")
            return False
    
    def _start_machining(self, task: ProductionTask) -> bool:
        """启动加工"""
        try:
            self.logger.info(f"启动任务处理: {task.product_model}")
            
            # 模拟任务处理启动过程
            time.sleep(0.5)
            
            self.logger.info("任务处理已启动")
            return True
            
        except Exception as e:
            self.logger.error(f"任务处理启动失败: {e}")
            return False
    
    def _complete_machining(self, task: ProductionTask) -> bool:
        """完成加工"""
        try:
            self.logger.info(f"完成任务处理: {task.product_model}")
            
            # 模拟任务处理完成过程
            time.sleep(0.5)
            
            # 更新完成状态
            task.completed_quantity = task.order_quantity
            self.logger.info("任务处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"任务处理完成失败: {e}")
            return False
    
    def get_execution_status(self) -> Dict:
        """获取执行状态"""
        current_task_info = None
        if self.current_task:
            current_task_info = {
                'task_id': self.current_task.task_id,
                'product_model': self.current_task.product_model,
                'progress': self.current_task.progress,
                'status': self.current_task.status.value
            }
        
        return {
            'is_running': self.is_running,
            'current_task': current_task_info,
            'execution_stats': self.execution_stats.copy(),
            'execution_interval': self.execution_interval
        }
    
    def get_execution_statistics(self) -> Dict:
        """获取执行统计信息"""
        return {
            'tasks_executed': self.execution_stats['tasks_executed'],
            'tasks_completed': self.execution_stats['tasks_completed'],
            'tasks_failed': self.execution_stats['tasks_failed'],
            'total_execution_time': self.execution_stats['total_execution_time'],
            'current_task': self.current_task.task_id if self.current_task else None,
            'is_running': self.is_running
        }
    
    def pause_execution(self):
        """暂停执行"""
        if self.current_task:
            self.task_scheduler.pause_task(self.current_task.task_id)
            self.logger.info(f"任务 {self.current_task.task_id} 已暂停")
    
    def resume_execution(self):
        """恢复执行"""
        if self.current_task:
            self.task_scheduler.resume_task(self.current_task.task_id)
            self.logger.info(f"任务 {self.current_task.task_id} 已恢复")