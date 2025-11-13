def get_task_list(self) -> List[Dict]:
    """获取任务列表"""
    if not self.task_scheduler:
        return []
    
    task_list = []
    
    # 添加待处理任务
    for task in self.task_scheduler.pending_tasks:
        task_list.append({
            'task_id': task.task_id,
            'instruction_id': task.instruction_id,
            'product_model': task.product_model,
            'material_spec': task.material_spec,
            'order_quantity': task.order_quantity,
            'priority': task.priority.value,  # 确保 priority 是字符串
            'status': task.status.value,  # 确保 status 是字符串
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'created_at') and task.created_at else '未知',
            'assigned_machine': task.assigned_machine
        })
    
    # 添加运行中任务
    for task in self.task_scheduler.running_tasks.values():
        task_list.append({
            'task_id': task.task_id,
            'instruction_id': task.instruction_id,
            'product_model': task.product_model,
            'material_spec': task.material_spec,
            'order_quantity': task.order_quantity,
            'priority': task.priority.value,  # 确保 priority 是字符串
            'status': task.status.value,  # 确保 status 是字符串
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'created_at') and task.created_at else '未知',
            'assigned_machine': task.assigned_machine
        })
    
    # 添加已完成任务
    for task in self.task_scheduler.completed_tasks:
        task_list.append({
            'task_id': task.task_id,
            'instruction_id': task.instruction_id,
            'product_model': task.product_model,
            'material_spec': task.material_spec,
            'order_quantity': task.order_quantity,
            'priority': task.priority.value,  # 确保 priority 是字符串
            'status': task.status.value,  # 确保 status 是字符串
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(task, 'created_at') and task.created_at else '未知',
            'assigned_machine': task.assigned_machine
        })
    
    return task_list