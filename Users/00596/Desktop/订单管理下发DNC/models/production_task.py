class ProductionTask:
    """生产任务类"""
    
    def __init__(self, task_id: str, instruction_id: str, product_model: str,
                 material_spec: str, order_quantity: int, priority: str = "Normal"):
        self.task_id = task_id
        self.instruction_id = instruction_id
        self.product_model = product_model
        self.material_spec = material_spec
        self.order_quantity = order_quantity
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.assigned_machine = None
        self.created_at = datetime.now()  # 添加 created_at 属性
        self.updated_at = None