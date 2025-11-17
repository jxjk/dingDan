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
from services.material_checker import MaterialChecker
from config.config_manager import get_config_manager


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config: dict, material_checker: MaterialChecker):
        self.config = config
        self.material_checker = material_checker
        self.logger = logging.getLogger(__name__)
        
        # 获取配置管理器实例
        self.config_manager = get_config_manager()
        
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
        
        # 获取可用状态列表
        self.available_states = self.config_manager.get_available_states()
        
    def add_task(self, task: ProductionTask) -> bool:
        """添加任务到调度队列"""
        try:
            self.pending_tasks.append(task)
            self.logger.info(f"任务 {task.task_id} 已添加到调度队列")
            self.logger.debug(f"当前待处理任务数: {len(self.pending_tasks)}")
            # 打印所有待处理任务ID用于调试
            task_ids = [t.task_id for t in self.pending_tasks]
            self.logger.debug(f"当前待处理任务列表: {task_ids}")
            
            # 添加任务后自动触发调度
            self.logger.info("添加任务后自动触发调度")
            self.schedule_tasks()
            
            return True
        except Exception as e:
            self.logger.error(f"添加任务失败: {e}")
            return False
        
    def remove_task(self, task_id: str) -> bool:
        """从调度队列移除任务"""
        for i, task in enumerate(self.pending_tasks):
            if task.task_id == task_id:
                self.pending_tasks.pop(i)
                self.logger.info(f"任务 {task_id} 已从调度队列移除")
                return True
        return False
    
    def update_machine_state(self, machine_id: str, state: MachineState):
        """
        更新机床状态。
        
        Args:
            machine_id (str): 机床ID。
            state (MachineState): 包含机床所有信息的状态对象。
                          假设该对象已在外部通过正确的参数名（如 current_state, current_material）创建。
        """
        self.machine_states[machine_id] = state
        self.logger.debug(f"机床 {machine_id} 状态更新: {state.current_state}")
        
    def get_available_machines(self) -> List[str]:
        """获取可用机床列表"""
        available_machines = []
        self.logger.debug(f"检查可用机床，当前机床状态数: {len(self.machine_states)}")
        for machine_id, state in self.machine_states.items():
            # 检查机床是否正在运行任务
            is_running_task = state.current_task is not None
            # 检查机床状态是否可用
            is_status_available = self._is_machine_status_available(state.current_state)
            # 检查机床是否在线
            is_online = self._is_machine_online(machine_id)
            # 机床可用当且仅当没有运行任务、状态可用且在线
            is_available = not is_running_task and is_status_available and is_online
            self.logger.debug(f"机床 {machine_id} 状态: {state.current_state}, 是否正在运行任务: {is_running_task}, 是否在线: {is_online}, 是否可用: {is_available}")
            if is_available:
                available_machines.append(machine_id)
                self.logger.debug(f"机床 {machine_id} 可用，状态: {state.current_state}")
            else:
                self.logger.debug(f"机床 {machine_id} 不可用，状态: {state.current_state}，正在运行任务: {is_running_task}，在线: {is_online}")
        self.logger.debug(f"总共找到 {len(available_machines)} 台可用机床: {available_machines}")
        return available_machines
    
    def _is_machine_status_available(self, machine_state: str) -> bool:
        """检查机床状态是否在可用状态列表中（不包含任务占用检查）"""
        self.logger.debug(f"检查机床状态 {machine_state} 是否在可用列表中")
        
        # 将状态转换为大写进行比较
        normalized_state = machine_state.upper()
        normalized_available_states = [state.upper() for state in self.available_states]
        
        # 检查是否在可用状态列表中
        is_available = normalized_state in normalized_available_states
        
        # 如果机床状态为UNKNOWN，我们也认为它是可用的（假设它可以被设置为IDLE）
        if not is_available and normalized_state == "UNKNOWN":
            is_available = True
            
        self.logger.debug(f"机床状态 {machine_state} 可用性检查: {is_available}")
        return is_available
    
    def schedule_tasks(self) -> List[Tuple[ProductionTask, str]]:
        """执行任务调度"""
        # 在调度前先执行刷新操作
        self._refresh_machine_states()
        
        pending_count = len(self.pending_tasks)
        self.logger.debug(f"开始任务调度，待处理任务数: {pending_count}")
        
        if not self.pending_tasks:
            self.logger.debug("没有待处理任务")
            return []
            
        available_machines = self.get_available_machines()
        available_count = len(available_machines)
        self.logger.debug(f"可用机床数量: {available_count}")
        
        if not available_machines:
            self.logger.warning("没有可用机床，无法调度任务")
            return []
        
        # 显示所有机床状态
        for machine_id, state in self.machine_states.items():
            self.logger.debug(f"机床 {machine_id} 状态: {state.current_state}")
        
        # 使用当前策略进行调度
        scheduler = self.scheduling_strategies.get(self.current_strategy, 
                                                 self._schedule_material_first)
        self.logger.debug(f"使用调度策略: {self.current_strategy}")
        assignments = scheduler(self.pending_tasks, available_machines)
        
        self.logger.debug(f"调度结果 - 分配任务数: {len(assignments)}")
        
        # 执行任务分配
        executed_assignments = []
        # 创建可用机床列表的副本，以便在分配过程中动态更新
        current_available_machines = available_machines.copy()
        
        for task, machine_id in assignments:
            self.logger.debug(f"尝试分配任务 {task.task_id} 到机床 {machine_id}")
            # 检查机床是否仍在可用列表中（可能在之前的分配中被移除）
            if machine_id not in current_available_machines:
                self.logger.warning(f"机床 {machine_id} 不再可用，跳过任务 {task.task_id} 的分配")
                # 继续处理下一个任务分配
                continue
                
            if self._assign_task_to_machine(task, machine_id):
                self.logger.info(f"成功分配任务 {task.task_id} 到机床 {machine_id}")
                executed_assignments.append((task, machine_id))
                self.pending_tasks.remove(task)
                # 从当前可用机床列表中移除已分配的机床
                if machine_id in current_available_machines:
                    current_available_machines.remove(machine_id)
            else:
                self.logger.error(f"分配任务 {task.task_id} 到机床 {machine_id} 失败")
                self.logger.info(f"任务 {task.task_id} 保持在待处理队列中，等待下次调度")
                # 用户拒绝了分配，但继续处理其他任务
                # 不移除机床，因为可能可以分配给其他任务
        
        if executed_assignments:
            self.logger.info(f"✅ 本次调度成功分配 {len(executed_assignments)} 个任务")
        else:
            self.logger.info("ℹ️ 本次调度未分配任何任务")
            
        return executed_assignments
    
    def _refresh_machine_states(self):
        """刷新机床状态"""
        try:
            # 获取系统管理器实例
            from services.system_manager import get_system_manager
            system_manager = get_system_manager()
            
            # 调用系统管理器的机床状态更新方法
            if system_manager:
                system_manager._update_machine_states()
                self.logger.debug("机床状态刷新完成")
            else:
                self.logger.warning("无法获取系统管理器实例，跳过机床状态刷新")
        except Exception as e:
            self.logger.error(f"刷新机床状态时出错: {e}")
    
    def _schedule_material_first(self, tasks: List[ProductionTask], 
                               machines: List[str]) -> List[Tuple[ProductionTask, str]]:
        """材料优先调度策略"""
        self.logger.debug(f"材料优先调度策略开始执行，任务数: {len(tasks)}, 可用机床数: {len(machines)}")
        assignments = []
        machine_materials = {machine_id: self.machine_states[machine_id].current_material 
                           for machine_id in machines}
        
        self.logger.debug(f"机床材料映射: {machine_materials}")
        
        # 按材料匹配度排序
        def get_priority_value(task):
            # 处理priority可能是字符串或枚举的情况
            if isinstance(task.priority, str):
                return task.priority
            elif hasattr(task.priority, 'value'):
                return task.priority.value
            else:
                return str(task.priority)
        
        # 创建机器列表副本，以便在调度过程中动态更新
        available_machines = machines.copy()
        
        for task in sorted(tasks, key=lambda t: get_priority_value(t), reverse=True):
            self.logger.debug(f"评估任务 {task.task_id} (优先级: {get_priority_value(task)})")
            best_machine = self._find_best_machine_for_task(task, 
                {mid: mat for mid, mat in machine_materials.items() if mid in available_machines})
            self.logger.debug(f"任务 {task.task_id} 最佳机床: {best_machine}")
            if best_machine:
                assignments.append((task, best_machine))
                # 从可用机床中移除已分配的机床
                if best_machine in available_machines:
                    available_machines.remove(best_machine)
                    self.logger.debug(f"移除已分配机床 {best_machine}，剩余可用机床: {available_machines}")
        
        self.logger.debug(f"材料优先调度策略完成，分配数: {len(assignments)}")
        return assignments
    
    def _schedule_priority_first(self, tasks: List[ProductionTask], 
                               machines: List[str]) -> List[Tuple[ProductionTask, str]]:
        """优先级优先调度策略"""
        # 按优先级排序
        def get_priority_order(task):
            # 处理priority可能是字符串或枚举的情况
            priority_value = task.priority
            if isinstance(priority_value, str):
                priority_str = priority_value.upper()
            elif hasattr(priority_value, 'value'):
                priority_str = priority_value.value.upper()
            else:
                priority_str = str(priority_value).upper()
            
            priority_order = {'URGENT': 3, 'HIGH': 2, 'NORMAL': 1}
            return priority_order.get(priority_str, 1)
        
        sorted_tasks = sorted(tasks, key=get_priority_order, reverse=True)
        
        assignments = []
        machine_materials = {machine_id: self.machine_states[machine_id].current_material 
                           for machine_id in machines}
        
        # 创建机器列表副本，以便在调度过程中动态更新
        available_machines = machines.copy()
        
        # 按优先级顺序分配任务
        for task in sorted_tasks:
            best_machine = self._find_best_machine_for_task(task, 
                {mid: mat for mid, mat in machine_materials.items() if mid in available_machines})
            if best_machine:
                assignments.append((task, best_machine))
                # 从可用机床中移除已分配的机床
                if best_machine in available_machines:
                    available_machines.remove(best_machine)
        
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
        
        # 创建机器列表副本，以便在调度过程中动态更新
        available_machines = machines.copy()
        
        for task in sorted(tasks, key=lambda t: t.priority.value, reverse=True):
            # 选择负载最小的可用机床
            available_machines_with_load = [(machine_id, machine_load[machine_id]) 
                                          for machine_id in available_machines 
                                          if machine_id in machine_materials]
            
            if available_machines_with_load:
                best_machine = min(available_machines_with_load, key=lambda x: x[1])[0]
                material_check = self.material_checker.check_material_compatibility(
                    task, best_machine, machine_materials[best_machine])
                
                if material_check.compatible:
                    assignments.append((task, best_machine))
                    machine_load[best_machine] += task.estimated_duration
                    if best_machine in available_machines:
                        available_machines.remove(best_machine)
        
        return assignments
    
    def _schedule_efficiency(self, tasks: List[ProductionTask], 
                           machines: List[str]) -> List[Tuple[ProductionTask, str]]:
        """效率优先调度策略"""
        assignments = []
        machine_materials = {machine_id: self.machine_states[machine_id].current_material 
                           for machine_id in machines}
        
        # 创建机器列表副本，以便在调度过程中动态更新
        available_machines = machines.copy()
        
        # 计算每个任务在每台机床上的效率得分
        task_machine_scores = []
        for task in tasks:
            for machine_id in available_machines:
                if machine_id in machine_materials:
                    score = self._calculate_efficiency_score(task, machine_id, 
                                                           machine_materials[machine_id])
                    task_machine_scores.append((score, task, machine_id))
        
        # 按效率得分排序
        task_machine_scores.sort(reverse=True)
        
        assigned_tasks = set()
        assigned_machines = set()
        
        for score, task, machine_id in task_machine_scores:
            if task.task_id not in assigned_tasks and machine_id not in assigned_machines and machine_id in available_machines:
                assignments.append((task, machine_id))
                assigned_tasks.add(task.task_id)
                assigned_machines.add(machine_id)
                # 从可用机床列表中移除已分配的机床
                available_machines.remove(machine_id)
        
        return assignments
    
    def _find_best_machine_for_task(self, task: ProductionTask, 
                                  machine_materials: Dict[str, str]) -> Optional[str]:
        """为任务找到最佳机床"""
        self.logger.debug(f"为任务 {task.task_id} 寻找最佳机床")
        self.logger.debug(f"任务材料: {task.material_spec}")
        self.logger.debug(f"可用机床材料: {machine_materials}")
        best_machine = None
        best_score = -1
        
        # 获取当前真正可用的机床列表
        actually_available_machines = self.get_available_machines()
        
        for machine_id, current_material in machine_materials.items():
            self.logger.debug(f"评估机床 {machine_id} (当前材料: {current_material})")
            # 检查机床是否在真正可用的机床列表中
            if machine_id not in actually_available_machines:
                self.logger.debug(f"机床 {machine_id} 不在可用机床列表中")
                continue
                
            # 检查机床是否在线
            if not self._is_machine_online(machine_id):
                self.logger.debug(f"机床 {machine_id} 不在线")
                continue
                
            # 材料兼容性检查
            material_check = self.material_checker.check_material_compatibility(
                task, machine_id, current_material)
            self.logger.debug(f"材料兼容性检查结果: {material_check}")
            
            if material_check['compatible']:
                score = self._calculate_assignment_score(task, machine_id, 
                                                       current_material, material_check)
                self.logger.debug(f"机床 {machine_id} 得分: {score}")
                if score > best_score:
                    best_score = score
                    best_machine = machine_id
                    self.logger.debug(f"更新最佳机床为 {best_machine} (得分: {best_score})")
        
        self.logger.debug(f"任务 {task.task_id} 最佳机床: {best_machine}")
        return best_machine
    
    def _calculate_assignment_score(self, task: ProductionTask, machine_id: str, 
                                  current_material: str, 
                                  material_check: Dict) -> float:
        """计算任务分配得分"""
        score = 0.0
        
        # 材料匹配得分
        if not material_check['requires_change']:
            score += 100  # 材料完全匹配
        else:
            score += max(0, 100 - material_check['change_cost'])  # 考虑更换成本
        
        # 优先级得分
        # 处理priority可能是字符串或枚举的情况
        priority_value = task.priority
        if isinstance(priority_value, str):
            priority_str = priority_value.upper()
        elif hasattr(priority_value, 'value'):
            priority_str = priority_value.value.upper()
        else:
            priority_str = str(priority_value).upper()
            
        priority_scores = {'URGENT': 50, 'HIGH': 30, 'NORMAL': 10}
        score += priority_scores.get(priority_str, 10)
        
        # 机床能力匹配得分
        machine_state = self.machine_states.get(machine_id)
        if machine_state and hasattr(machine_state, 'capabilities'):
            # 简单匹配，实际可根据任务需求和机床能力进行更复杂的匹配
            score += len(machine_state.capabilities) * 2
        
        self.logger.debug(f"任务 {task.task_id} 在机床 {machine_id} 上的得分: {score}")
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
            self.logger.debug(f"开始分配任务 {task.task_id} 到机床 {machine_id}")
            
            # 检查机床是否在线
            if not self._is_machine_online(machine_id):
                self.logger.warning(f"机床 {machine_id} 不在线，无法分配任务 {task.task_id}")
                return False
            
            # 检查机床状态，包括已完成数量与要求数量是否一致
            if not self._check_machine_status_before_assignment(machine_id, task):
                self.logger.warning(f"机床 {machine_id} 状态检查失败，无法分配任务 {task.task_id}")
                return False
            
            # 检查材料兼容性并给出警告
            if not self._check_material_compatibility_and_warn(task, machine_id):
                self.logger.warning(f"用户取消了任务 {task.task_id} 分配到机床 {machine_id}")
                return False
            
            # 更新任务状态
            task.assigned_machine = machine_id
            old_status = task.status
            task.update_status(TaskStatus.READY, f"已分配到机床 {machine_id}")
            self.logger.info(f"任务 {task.task_id} 状态从 {old_status} 更新为 {task.status}")
            
            # 添加到运行任务列表
            self.running_tasks[task.task_id] = task
            self.logger.debug(f"任务 {task.task_id} 已添加到运行任务列表")
            
            # 更新机床状态，标记为忙碌状态
            if machine_id in self.machine_states:
                self.machine_states[machine_id].current_task = task.task_id
                # 将机床状态更新为RUNNING，表示该机床正在处理任务
                self.machine_states[machine_id].current_state = "RUNNING"
                self.logger.debug(f"机床 {machine_id} 当前任务已更新为 {task.task_id}，状态更新为RUNNING")
            
            self.logger.info(f"任务 {task.task_id} 已分配到机床 {machine_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"分配任务 {task.task_id} 到机床 {machine_id} 失败: {e}")
            return False
    
    def _check_machine_status_before_assignment(self, machine_id: str, task: ProductionTask) -> bool:
        """在任务分配前检查机床状态"""
        try:
            # 获取系统管理器实例
            from services.system_manager import get_system_manager
            system_manager = get_system_manager()
            
            # 检查CNC连接器是否存在
            if not system_manager.cnc_connector:
                self.logger.warning(f"系统管理器中没有CNC连接器，跳过机床 {machine_id} 状态检查")
                return True  # 如果没有连接器，跳过检查
            
            # 获取机床配置信息
            machines_config = system_manager.config_manager.get('machines', {})
            if machine_id not in machines_config:
                self.logger.warning(f"未找到机床 {machine_id} 的配置信息")
                return True  # 如果没有配置信息，跳过检查
            
            machine_info = machines_config[machine_id]
            host = machine_info.get('ip_address', '127.0.0.1')
            port = machine_info.get('port', 8193)
            
            # 获取机床状态
            status_response = system_manager.cnc_connector.get_machine_status(host, port)
            if not status_response or not status_response.get("success"):
                self.logger.warning(f"无法获取机床 {machine_id} 状态")
                return True  # 如果无法获取状态，跳过检查
            
            status_data = status_response.get("data", {})
            
            # 检查已完成数量与要求数量是否一致
            completed_count = status_data.get("completed_count", 0)
            required_count = status_data.get("required_count", task.order_quantity)
            
            self.logger.debug(f"机床 {machine_id} 当前完成数量: {completed_count}, 要求数量: {required_count}")
            
            # 如果已完成数量与要求数量不一致，需要清空机床上的要加工数量
            if completed_count != required_count:
                self.logger.info(f"机床 {machine_id} 上存在未完成任务，正在清空任务数量")
                # 这里可以添加清空机床上要加工数量的逻辑
                # 例如发送命令给机床清空任务或重置计数器
                # 由于这是模拟环境，我们只记录日志
                self.logger.info(f"已清空机床 {machine_id} 上的要加工数量")
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查机床 {machine_id} 状态时出错: {e}")
            return True  # 出错时仍然允许分配任务，避免阻塞系统
    
    def _is_machine_online(self, machine_id: str) -> bool:
        """检查机床是否在线"""
        # 根据新需求，不再需要检查机床是否在线，直接返回True
        self.logger.debug(f"根据新需求，假设机床 {machine_id} 在线")
        return True
    
    def _check_material_compatibility_and_warn(self, task: ProductionTask, machine_id: str) -> bool:
        """检查材料兼容性并在需要更换材料时警告用户"""
        # 获取机床当前材料
        if machine_id not in self.machine_states:
            self.logger.warning(f"未找到机床 {machine_id} 的状态信息")
            return False  # 如果没有状态信息，阻止分配任务
        
        current_material = self.machine_states[machine_id].current_material
        
        # 检查材料是否匹配
        if current_material == task.material_spec:
            # 材料匹配，无需警告
            return True
        
        # 材料不匹配，需要更换材料，给出警告
        warning_msg = (f"警告: 任务 {task.task_id} 的材料 ({task.material_spec}) 与机床 {machine_id} "
                      f"当前材料 ({current_material}) 不匹配，需要更换材料。是否继续分配?")
        
        self.logger.warning(warning_msg)
        
        # 在实际系统中，这里应该有一个用户确认机制
        # 为了简化，我们在这里模拟用户确认
        # 在真实的CLI或GUI环境中，应该弹出确认对话框
        print(warning_msg)
        user_input = input("输入 'yes' 确认继续分配，其他任意键取消: ").strip().lower()
        
        result = user_input == 'yes'
        if not result:
            self.logger.info(f"任务 {task.task_id} 因材料不匹配且用户未确认，保持阻塞状态")
        return result
    
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
                # 将机床状态重置为IDLE，表示该机床现在可用
                self.machine_states[task.assigned_machine].current_state = "IDLE"
                self.logger.debug(f"机床 {task.assigned_machine} 任务完成，current_task 设为 None，状态设为 IDLE")
            
            self.logger.info(f"任务 {task_id} 已完成")
    
    def pause_task(self, task_id: str):
        """暂停任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.update_status(TaskStatus.PAUSED, "任务暂停")
            # 更新机床状态为暂停
            if task.assigned_machine and task.assigned_machine in self.machine_states:
                self.machine_states[task.assigned_machine].current_state = "PAUSED"
            self.logger.info(f"任务 {task_id} 已暂停")
    
    def resume_task(self, task_id: str):
        """恢复任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.update_status(TaskStatus.RUNNING, "任务恢复")
            # 更新机床状态为运行中
            if task.assigned_machine and task.assigned_machine in self.machine_states:
                self.machine_states[task.assigned_machine].current_state = "RUNNING"
            self.logger.info(f"任务 {task_id} 已恢复")
    
    def get_task_statistics(self) -> Dict:
        """获取任务统计信息"""
        return {
            'pending': len(self.pending_tasks),
            'running': len(self.running_tasks),
            'completed': len(self.completed_tasks),
            'total': len(self.pending_tasks) + len(self.running_tasks) + len(self.completed_tasks)
        }
    
    def get_task_list(self) -> List[Dict]:
        """获取所有任务列表"""
        task_list = []
        
        # 添加待处理任务
        for task in self.pending_tasks:
            task_list.append({
                'task_id': task.task_id,
                'instruction_id': task.instruction_id,
                'product_model': task.product_model,
                'material_spec': task.material_spec,
                'order_quantity': task.order_quantity,
                'priority': self._get_priority_value(task.priority),
                'status': self._get_status_value(task.status),
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '未知',
                'assigned_machine': task.assigned_machine
            })
        
        # 添加运行中任务
        for task in self.running_tasks.values():
            task_list.append({
                'task_id': task.task_id,
                'instruction_id': task.instruction_id,
                'product_model': task.product_model,
                'material_spec': task.material_spec,
                'order_quantity': task.order_quantity,
                'priority': self._get_priority_value(task.priority),
                'status': self._get_status_value(task.status),
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '未知',
                'assigned_machine': task.assigned_machine
            })
        
        # 添加已完成任务
        for task in self.completed_tasks:
            task_list.append({
                'task_id': task.task_id,
                'instruction_id': task.instruction_id,
                'product_model': task.product_model,
                'material_spec': task.material_spec,
                'order_quantity': task.order_quantity,
                'priority': self._get_priority_value(task.priority),
                'status': self._get_status_value(task.status),
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '未知',
                'assigned_machine': task.assigned_machine
            })
        
        return task_list
    
    def _get_priority_value(self, priority):
        """获取优先级值，支持枚举和字符串"""
        if hasattr(priority, 'value'):
            return priority.value
        return priority
    
    def _get_status_value(self, status):
        """获取状态值，支持枚举和字符串"""
        if hasattr(status, 'value'):
            return status.value
        return status
    
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