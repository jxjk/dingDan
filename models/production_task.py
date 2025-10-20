"""
生产任务数据模型
定义数控车床生产任务的核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "Pending"        # 等待中
    READY = "Ready"           # 就绪
    RUNNING = "Running"       # 加工中
    COMPLETED = "Completed"   # 已完成
    ERROR = "Error"           # 错误
    PAUSED = "Paused"         # 暂停
    WAITING_FOR_MATERIAL = "WaitingForMaterial"  # 等待材料


class TaskPriority(Enum):
    """任务优先级枚举"""
    HIGH = "High"
    NORMAL = "Normal"
    URGENT = "Urgent"


@dataclass
class ProductionTask:
    """生产任务数据类"""
    
    # 基础信息
    task_id: str                      # 系统生成唯一标识
    instruction_id: str               # 指示书编号
    product_model: str                # 产品型号
    material_spec: str                # 材料规格
    order_quantity: int               # 订单数量
    
    # 状态信息
    completed_quantity: int = 0       # 已完成数量
    priority: TaskPriority = TaskPriority.NORMAL  # 优先级
    status: TaskStatus = TaskStatus.PENDING  # 状态
    assigned_machine: Optional[str] = None  # 分配机床
    
    # 时间信息
    create_time: datetime = field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.now)
    
    # 生产信息
    estimated_duration: int = 0       # 预估加工时间(分钟)
    material_check: bool = False      # 材料检查结果
    program_available: bool = False   # 程序可用性
    
    # 扩展信息
    qr_code: Optional[str] = None     # 二维码内容
    program_name: Optional[str] = None  # 程序名称
    notes: Optional[str] = None       # 备注信息
    
    # 错误信息
    error_message: Optional[str] = None  # 错误信息
    retry_count: int = 0              # 重试次数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "instruction_id": self.instruction_id,
            "product_model": self.product_model,
            "material_spec": self.material_spec,
            "order_quantity": self.order_quantity,
            "completed_quantity": self.completed_quantity,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_machine": self.assigned_machine,
            "create_time": self.create_time.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "last_state_change": self.last_state_change.isoformat(),
            "estimated_duration": self.estimated_duration,
            "material_check": self.material_check,
            "program_available": self.program_available,
            "qr_code": self.qr_code,
            "program_name": self.program_name,
            "notes": self.notes,
            "error_message": self.error_message,
            "retry_count": self.retry_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductionTask':
        """从字典创建实例"""
        task = cls(
            task_id=data["task_id"],
            instruction_id=data["instruction_id"],
            product_model=data["product_model"],
            material_spec=data["material_spec"],
            order_quantity=data["order_quantity"],
            completed_quantity=data.get("completed_quantity", 0),
            priority=TaskPriority(data.get("priority", "Normal")),
            status=TaskStatus(data.get("status", "Pending")),
            assigned_machine=data.get("assigned_machine"),
            estimated_duration=data.get("estimated_duration", 0),
            material_check=data.get("material_check", False),
            program_available=data.get("program_available", False),
            qr_code=data.get("qr_code"),
            program_name=data.get("program_name"),
            notes=data.get("notes"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0)
        )
        
        # 处理时间字段
        if data.get("create_time"):
            task.create_time = datetime.fromisoformat(data["create_time"])
        if data.get("start_time"):
            task.start_time = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            task.end_time = datetime.fromisoformat(data["end_time"])
        if data.get("last_state_change"):
            task.last_state_change = datetime.fromisoformat(data["last_state_change"])
        
        return task
    
    @property
    def progress(self) -> float:
        """计算任务进度百分比"""
        if self.order_quantity == 0:
            return 0.0
        return (self.completed_quantity / self.order_quantity) * 100
    
    @property
    def remaining_quantity(self) -> int:
        """计算剩余数量"""
        return self.order_quantity - self.completed_quantity
    
    @property
    def is_completed(self) -> bool:
        """检查任务是否完成"""
        return self.status == TaskStatus.COMPLETED
    
    @property
    def is_running(self) -> bool:
        """检查任务是否正在运行"""
        return self.status == TaskStatus.RUNNING
    
    @property
    def can_start(self) -> bool:
        """检查任务是否可以开始"""
        return (self.status in [TaskStatus.PENDING, TaskStatus.READY] and
                self.material_check and self.program_available)
    
    def update_status(self, new_status: TaskStatus, reason: str = "") -> None:
        """更新任务状态"""
        old_status = self.status
        self.status = new_status
        self.last_state_change = datetime.now()
        
        # 设置错误消息（当状态为ERROR时）
        if new_status == TaskStatus.ERROR and reason:
            self.error_message = reason
        
        # 记录状态转移
        if new_status == TaskStatus.RUNNING and not self.start_time:
            self.start_time = datetime.now()
        elif new_status == TaskStatus.COMPLETED and not self.end_time:
            self.end_time = datetime.now()
            self.completed_quantity = self.order_quantity
        
        # 记录状态转移日志
        print(f"任务 {self.task_id} 状态变更: {old_status.value} -> {new_status.value}")
        if reason:
            print(f"原因: {reason}")

@dataclass
class MaterialCheckResult:
    """材料检查结果"""
    compatible: bool                    # 是否兼容
    requires_change: bool = False       # 是否需要更换材料
    change_cost: int = 0                # 更换材料成本(分钟)
    message: str = ""                   # 检查结果消息
    available: int = 0                  # 可用库存数量
    machine_material: Optional[str] = None  # 机床当前材料


@dataclass
class MachineState:
    """机床状态数据类"""
    machine_id: str                    # 机床ID
    current_state: str                 # 当前状态
    current_material: str              # 当前材料
    current_task: Optional[str] = None  # 当前任务ID
    program_name: Optional[str] = None  # 当前程序名称
    last_update: datetime = field(default_factory=datetime.now)
    capabilities: list = field(default_factory=list)  # 机床能力
    ip_address: Optional[str] = None   # IP地址
    
    @property
    def is_available(self) -> bool:
        """检查机床是否可用"""
        return self.current_state.upper() in ['OFF', 'IDLE', 'STANDBY', 'READY']
    
    @property
    def is_running(self) -> bool:
        """检查机床是否正在运行"""
        return self.current_state.upper() in ['ON', 'RUNNING', 'BUSY']


class InvalidStateTransitionError(Exception):
    """无效状态转移异常"""
    pass
