"""
日志工具
提供统一的日志配置和管理功能
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any


def setup_logging(config: Dict[str, Any]):
    """设置日志配置"""
    log_config = config.get('logging', {})
    
    # 日志级别
    log_level = getattr(logging, log_config.get('level', 'INFO').upper())
    
    # 日志文件路径
    log_file = log_config.get('file_path', 'logs/system.log')
    log_path = Path(log_file)
    
    # 确保日志目录存在
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器 - 使用轮转文件
    max_size_mb = log_config.get('max_size_mb', 10)
    backup_count = log_config.get('backup_count', 5)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_size_mb * 1024 * 1024,  # 转换为字节
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 设置特定模块的日志级别
    _configure_module_log_levels()
    
    logging.info(f"日志系统已初始化，级别: {log_level}, 文件: {log_file}")


def _configure_module_log_levels():
    """配置特定模块的日志级别"""
    # 降低某些库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('pywinauto').setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器"""
    return logging.getLogger(name)


class ProductionLogger:
    """生产系统专用日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def task_created(self, task_id: str, instruction_id: str, product_model: str):
        """记录任务创建"""
        self.logger.info(f"任务创建 - ID: {task_id}, 指示书: {instruction_id}, 型号: {product_model}")
    
    def task_assigned(self, task_id: str, machine_id: str):
        """记录任务分配"""
        self.logger.info(f"任务分配 - 任务: {task_id}, 机床: {machine_id}")
    
    def task_started(self, task_id: str, machine_id: str):
        """记录任务开始"""
        self.logger.info(f"任务开始 - 任务: {task_id}, 机床: {machine_id}")
    
    def task_completed(self, task_id: str, machine_id: str):
        """记录任务完成"""
        self.logger.info(f"任务完成 - 任务: {task_id}, 机床: {machine_id}")
    
    def task_failed(self, task_id: str, machine_id: str, error: str):
        """记录任务失败"""
        self.logger.error(f"任务失败 - 任务: {task_id}, 机床: {machine_id}, 错误: {error}")
    
    def machine_state_change(self, machine_id: str, old_state: str, new_state: str):
        """记录机床状态变化"""
        self.logger.info(f"机床状态变化 - 机床: {machine_id}, 状态: {old_state} -> {new_state}")
    
    def material_check(self, task_id: str, material_spec: str, machine_material: str, compatible: bool):
        """记录材料检查"""
        status = "兼容" if compatible else "不兼容"
        self.logger.info(f"材料检查 - 任务: {task_id}, 材料: {material_spec}, 机床材料: {machine_material}, 结果: {status}")
    
    def automation_success(self, system: str, instruction_id: str):
        """记录自动化成功"""
        self.logger.info(f"自动化成功 - 系统: {system}, 指示书: {instruction_id}")
    
    def automation_failed(self, system: str, instruction_id: str, error: str):
        """记录自动化失败"""
        self.logger.error(f"自动化失败 - 系统: {system}, 指示书: {instruction_id}, 错误: {error}")
    
    def scheduling_decision(self, strategy: str, task_count: int, machine_count: int):
        """记录调度决策"""
        self.logger.info(f"调度决策 - 策略: {strategy}, 任务数: {task_count}, 可用机床数: {machine_count}")
    
    def qr_scan(self, qr_content: str, success: bool):
        """记录二维码扫描"""
        status = "成功" if success else "失败"
        self.logger.info(f"二维码扫描 - 内容: {qr_content}, 状态: {status}")


class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"performance.{name}")
    
    def start_timing(self, operation: str):
        """开始计时"""
        import time
        return {
            'operation': operation,
            'start_time': time.time()
        }
    
    def end_timing(self, timing_info: dict):
        """结束计时并记录"""
        import time
        duration = time.time() - timing_info['start_time']
        self.logger.info(f"性能计时 - 操作: {timing_info['operation']}, 耗时: {duration:.3f}秒")
        return duration
    
    def log_memory_usage(self, context: str = ""):
        """记录内存使用情况"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        self.logger.info(f"内存使用 - {context} - RSS: {memory_info.rss / 1024 / 1024:.2f} MB, "
                        f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
    
    def log_cpu_usage(self, context: str = ""):
        """记录CPU使用情况"""
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        self.logger.info(f"CPU使用 - {context} - 使用率: {cpu_percent:.1f}%")


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"audit.{name}")
    
    def user_action(self, user: str, action: str, target: str, details: str = ""):
        """记录用户操作"""
        self.logger.info(f"用户操作 - 用户: {user}, 操作: {action}, 目标: {target}, 详情: {details}")
    
    def system_change(self, component: str, change_type: str, old_value: str, new_value: str):
        """记录系统变更"""
        self.logger.info(f"系统变更 - 组件: {component}, 类型: {change_type}, 旧值: {old_value}, 新值: {new_value}")
    
    def configuration_change(self, config_key: str, old_value: str, new_value: str, user: str = "system"):
        """记录配置变更"""
        self.logger.info(f"配置变更 - 用户: {user}, 配置项: {config_key}, 旧值: {old_value}, 新值: {new_value}")
    
    def security_event(self, event_type: str, severity: str, details: str):
        """记录安全事件"""
        self.logger.warning(f"安全事件 - 类型: {event_type}, 严重性: {severity}, 详情: {details}")


def create_log_analyzer(log_file: str):
    """创建日志分析器"""
    class LogAnalyzer:
        def __init__(self, log_file: str):
            self.log_file = log_file
        
        def count_errors(self) -> int:
            """统计错误数量"""
            error_count = 0
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if 'ERROR' in line:
                            error_count += 1
            except FileNotFoundError:
                pass
            return error_count
        
        def get_recent_activities(self, count: int = 10) -> list:
            """获取最近的活动"""
            activities = []
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    activities = lines[-count:] if len(lines) >= count else lines
            except FileNotFoundError:
                pass
            return activities
        
        def analyze_performance(self) -> dict:
            """分析性能数据"""
            performance_data = {
                'total_operations': 0,
                'average_duration': 0,
                'slow_operations': []
            }
            
            try:
                durations = []
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '性能计时' in line:
                            performance_data['total_operations'] += 1
                            # 提取耗时信息
                            if '耗时:' in line:
                                try:
                                    duration_str = line.split('耗时:')[1].split('秒')[0].strip()
                                    duration = float(duration_str)
                                    durations.append(duration)
                                    if duration > 1.0:  # 超过1秒认为是慢操作
                                        performance_data['slow_operations'].append(line.strip())
                                except (ValueError, IndexError):
                                    pass
                
                if durations:
                    performance_data['average_duration'] = sum(durations) / len(durations)
                    
            except FileNotFoundError:
                pass
            
            return performance_data
    
    return LogAnalyzer(log_file)
