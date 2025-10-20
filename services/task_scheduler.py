"""
任务调度服务
实现智能任务分配、优先级管理和负载均衡
"""

import logging
import heapq
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from models.production_task import ProductionTask, TaskStatus, TaskPriority, MachineState
from services.material_checker import EnhancedMaterialChecker, MaterialCheckResult


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config: dict, material_checker: EnhancedMaterialChecker):
        self.config = config
        self.material_checker = material_checker
        self.logger = logging.getLogger(__name__)
        
        # 任务队列
        self.pending_tasks: List[ProductionTask] = []
        self.running_tasks: Dict[str, ProductionTask] = {}
        self.completed_tasks: List[ProductionTask] = []
        
        # 机床状态
        self.machine_states: Dict[str, MachineState] = {}
        
        # 调度策略配置
        self.scheduling_strategies = {
            'material_first': self._schedule_material_first,
            'priority_first': self._schedule_priority_first,
            'load_balance': self._schedule_load_balance,
            'efficiency': self._schedule_efficiency
        }
        
        self.current_strategy = 'material_first'
        
    def add_task(self, task: ProductionTask):
        """添加任务到调度队列"""
        self.pending_tasks.append(task)
        self.logger.info(f"任务 {task.task_id} 已添加到调度队列")
        
    def remove_task(self, task_id: str) -> bool:
        """从调度队列移除任务"""
        for i, task in enumerate(self.pending_tasks):
            if task.task_id == task_id:
                self.pending_tasks.pop(i)
                self.logger.info(f"任务 {task_id} 已从调度队列移除")
                return True
        return False
    
    def update_machine_state(self, machine_id: str, state: MachineState):
        """更新机床状态"""
        self.machine_states[machine_id] = state
        self.logger.debug(f"机床 {machine_id} 状态更新: {state.current_state}")
        
    def get_available_machines(self) -> List[str]:
        """获取可用机床列表"""
        return [machine_id for machine_id, state in self.machine_states.items() 
                if state.is_available]
    
    def schedule_tasks(self) -> List[Tuple[ProductionTask, str]]:
        """执行任务调度"""
        if not self.pending_tasks:
            return []
            
        available_machines = self.get_available_machines()
        if not available_machines:
            self.logger.warning("没有可用机床，无法调度任务")
            return []
        
        # 使用当前策略进行调度
        scheduler = self.scheduling_strategies.get(self.current_strategy, 
                                                 self._schedule_material_first)
        assignments = scheduler(self.pending_tasks, available_machines)
        
        # 执行任务分配
        executed_assignments = []
        for task, machine_id in assignments:
            if self._assign_task_to_machine(task, machine_id):
                executed_assignments.append((task, machine_id))
                self.pending_tasks.remove(task)
        
        return executed_assignments
    
    def _schedule_material_first(self, tasks: List[ProductionTask], 
                               machines: List[str]) -> List[Tuple[ProductionTask, str]]:
        """材料优先调度策略"""
        assignments = []
        machine_materials = {machine_id: self.machine_states[machine_id].current_material 
                           for machine_id in machines}
        
        # 按材料匹配度排序
        for task in sorted(tasks, key=lambda t: t.priority.value, reverse=True):
            best_machine = self._find_best_machine_for_task(task, machine_materials)
            if best_machine:
                assignments.append((task, best_machine))
                # 从可用机床中移除已分配的机床
                if best_machine in machines:
                    machines.remove(best_machine)
        
        return assignments
    
    def _schedule_priority_first(self, tasks: List[ProductionTask], 
                               machines: List[str]) -> List[Tuple[ProductionTask, str]]:
        """优先级优先调度策略"""
        # 按优先级排序
        priority_order = {TaskPriority.URGENT: 3, TaskPriority.HIGH: 2, TaskPriority.NORMAL: 1}
        sorted_tasks = sorted(tasks, key=lambda t: priority_order[t.priority], reverse=True)
        
        assignments = []
        machine_materials = {machine_id: self.machine_states[machine_id].current_material 
                           for machine_id in machines}
        
        for task in sorted_tasks:
            best_machine = self._find_best_machine_for_task(task, machine_materials)
            if best_machine:
                assignments.append((task, best_machine))
                if best_machine in machines:
                    machines.remove(best_machine)
        
        return assignments
    
    def _schedule_load_balance(self, tasks: List[ProductionTask], 
                             machines: List[str]) -> List[Tuple[ProductionTask, str]]:
        """负载均衡调度策略"""
        # 计算每个机床的负载
        machine_load = defaultdict(int)
        for task in self.running_tasks.values():
            if task.assigned_machine:
                machine_load[task.assigned_machine] += task.estimated_duration
        
        assignments = []
        machine_materials = {machine_id: self.machine_states[machine_id].current_material 
                           for machine_id in machines}
        
        for task in sorted(tasks, key=lambda t: t.priority.value, reverse=True):
            # 选择负载最小的可用机床
            available_machines_with_load = [(machine_id, machine_load[machine_id]) 
                                          for machine_id in machines 
                                          if machine_id in machine_materials]
            
            if available_machines_with_load:
                best_machine = min(available_machines_with_load, key=lambda x: x[1])[0]
                material_check = self.material_checker.check_material_compatibility(
                    task, best_machine, machine_materials[best_machine])
                
                if material_check.compatible:
                    assignments.append((task, best_machine))
                    machine_load[best_machine] += task.estimated_duration
                    if best_machine in machines:
                        machines.remove(best_machine)
        
        return assignments
    
    def _schedule_efficiency(self, tasks: List[ProductionTask], 
                           machines: List[str]) -> List[Tuple[ProductionTask, str]]:
        """效率优先调度策略"""
        assignments = []
        machine_materials = {machine_id: self.machine_states[machine_id].current_material 
                           for machine_id in machines}
        
        # 计算每个任务在每台机床上的效率得分
        task_machine_scores = []
        for task in tasks:
            for machine_id in machines:
                score = self._calculate_efficiency_score(task, machine_id, 
                                                       machine_materials[machine_id])
                task_machine_scores.append((score, task, machine_id))
        
        # 按效率得分排序
        task_machine_scores.sort(reverse=True)
        
        assigned_tasks = set()
        assigned_machines = set()
        
        for score, task, machine_id in task_machine_scores:
            if task.task_id not in assigned_tasks and machine_id not in assigned_machines:
                assignments.append((task, machine_id))
                assigned_tasks.add(task.task_id)
                assigned_machines.add(machine_id)
        
        return assignments
    
    def _find_best_machine_for_task(self, task: ProductionTask, 
                                  machine_materials: Dict[str, str]) -> Optional[str]:
        """为任务寻找最佳机床"""
        best_machine = None
        best_score = -1
        
        for machine_id, current_material in machine_materials.items():
            # 材料兼容性检查
            material_check = self.material_checker.check_material_compatibility(
                task, machine_id, current_material)
            
            if material_check.compatible:
                score = self._calculate_assignment_score(task, machine_id, 
                                                       current_material, material_check)
                if score > best_score:
                    best_score = score
                    best_machine = machine_id
        
        return best_machine
    
    def _calculate_assignment_score(self, task: ProductionTask, machine_id: str, 
                                  current_material: str, 
                                  material_check: MaterialCheckResult) -> float:
        """计算任务分配得分"""
        score = 0.0
        
        # 材料匹配得分
        if not material_check.requires_change:
            score += 100  # 材料完全匹配
        else:
            score += max(0, 100 - material_check.change_cost)  # 考虑更换成本
        
        # 优先级得分
        priority_scores = {TaskPriority.URGENT: 50, TaskPriority.HIGH: 30, 
                          TaskPriority.NORMAL: 10}
        score += priority_scores.get(task.priority, 0)
        
        # 机床能力匹配得分
        machine_state = self.machine_states.get(machine_id)
        if machine_state and task.program_name:
            if any(capability in machine_state.capabilities for capability in ['turning', 'facing']):
                score += 20
        
        return score
    
    def _calculate_efficiency_score(self, task: ProductionTask, machine_id: str, 
                                  current_material: str) -> float:
        """计算效率得分"""
        material_check = self.material_checker.check_material_compatibility(
            task, machine_id, current_material)
        
        if not material_check.compatible:
            return -1
        
        # 基础效率得分
        efficiency = 100.0
        
        # 材料更换成本影响
        if material_check.requires_change:
            efficiency -= material_check.change_cost * 2
        
        # 任务优先级影响
        if task.priority == TaskPriority.URGENT:
            efficiency *= 1.5
        elif task.priority == TaskPriority.HIGH:
            efficiency *= 1.2
        
        # 机床负载影响
        running_tasks_on_machine = sum(1 for t in self.running_tasks.values() 
                                     if t.assigned_machine == machine_id)
        efficiency /= (1 + running_tasks_on_machine * 0.1)
        
        return efficiency
    
    def _assign_task_to_machine(self, task: ProductionTask, machine_id: str) -> bool:
        """将任务分配给机床"""
        try:
            # 更新任务状态
            task.assigned_machine = machine_id
            task.update_status(TaskStatus.READY, f"已分配到机床 {machine_id}")
            
            # 添加到运行任务列表
            self.running_tasks[task.task_id] = task
            
            # 更新机床状态
            if machine_id in self.machine_states:
                self.machine_states[machine_id].current_task = task.task_id
            
            self.logger.info(f"任务 {task.task_id} 已分配到机床 {machine_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"分配任务 {task.task_id} 到机床 {machine_id} 失败: {e}")
            return False
    
    def complete_task(self, task_id: str):
        """标记任务完成"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.update_status(TaskStatus.COMPLETED, "任务完成")
            
            # 从运行任务中移除
            del self.running_tasks[task_id]
            
            # 添加到完成列表
            self.completed_tasks.append(task)
            
            # 更新机床状态
            if task.assigned_machine and task.assigned_machine in self.machine_states:
                self.machine_states[task.assigned_machine].current_task = None
            
            self.logger.info(f"任务 {task_id} 已完成")
    
    def pause_task(self, task_id: str):
        """暂停任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.update_status(TaskStatus.PAUSED, "任务暂停")
            self.logger.info(f"任务 {task_id} 已暂停")
    
    def resume_task(self, task_id: str):
        """恢复任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.update_status(TaskStatus.RUNNING, "任务恢复")
            self.logger.info(f"任务 {task_id} 已恢复")
    
    def get_task_statistics(self) -> Dict:
        """获取任务统计信息"""
        return {
            'pending': len(self.pending_tasks),
            'running': len(self.running_tasks),
            'completed': len(self.completed_tasks),
            'total': len(self.pending_tasks) + len(self.running_tasks) + len(self.completed_tasks)
        }
    
    def get_machine_utilization(self) -> Dict[str, float]:
        """获取机床利用率"""
        utilization = {}
        total_tasks = len(self.running_tasks) + len(self.completed_tasks)
        
        for machine_id in self.machine_states:
            machine_tasks = sum(1 for task in list(self.running_tasks.values()) + self.completed_tasks 
                              if task.assigned_machine == machine_id)
            utilization[machine_id] = (machine_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return utilization
    
    def set_scheduling_strategy(self, strategy: str):
        """设置调度策略"""
        if strategy in self.scheduling_strategies:
            self.current_strategy = strategy
            self.logger.info(f"调度策略已设置为: {strategy}")
        else:
            self.logger.warning(f"未知的调度策略: {strategy}")
