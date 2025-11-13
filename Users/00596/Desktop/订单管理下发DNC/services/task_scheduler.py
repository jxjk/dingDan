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
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'created_at') and task.created_at else '未知',
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
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'created_at') and task.created_at else '未知',
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
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'created_at') and task.created_at else '未知',
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