"""
系统工具模块
包含通用工具函数
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """设置日志系统"""
    log_level = config.get('logging', {}).get('level', 'INFO')
    log_file = config.get('logging', {}).get('file', 'logs/system.log')
    
    # 确保日志目录存在
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def create_directory_structure(base_path: str, structure: Dict[str, Any]) -> bool:
    """创建目录结构"""
    try:
        base_dir = Path(base_path)
        base_dir.mkdir(parents=True, exist_ok=True)
        
        for name, content in structure.items():
            if isinstance(content, dict):
                # 递归创建子目录
                create_directory_structure(str(base_dir / name), content)
            else:
                # 创建文件
                file_path = base_dir / name
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(content))
        
        return True
    except Exception as e:
        logging.error(f"创建目录结构失败: {e}")
        return False


def check_file_permissions(file_path: str) -> Dict[str, Any]:
    """检查文件权限"""
    path = Path(file_path)
    result = {
        'exists': path.exists(),
        'is_file': path.is_file(),
        'is_dir': path.is_dir(),
        'readable': False,
        'writable': False,
        'executable': False
    }
    
    if result['exists']:
        try:
            result['readable'] = os.access(file_path, os.R_OK)
            result['writable'] = os.access(file_path, os.W_OK)
            result['executable'] = os.access(file_path, os.X_OK)
        except Exception:
            pass
    
    return result


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"


def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    import platform
    
    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'processor': platform.processor(),
        'architecture': platform.architecture()[0],
        'current_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'working_directory': str(Path.cwd())
    }


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证配置"""
    errors = []
    warnings = []
    
    # 检查必需配置
    required_fields = ['system']
    for field in required_fields:
        if field not in config:
            errors.append(f"缺少必需配置字段: {field}")
    
    # 检查系统配置
    if 'system' in config:
        system_config = config['system']
        system_required = ['name', 'version', 'environment']
        for field in system_required:
            if field not in system_config:
                errors.append(f"缺少系统配置字段: system.{field}")
    
    # 检查材料映射配置
    if 'material_mapping' in config:
        material_config = config['material_mapping']
        if 'csv_path' not in material_config:
            warnings.append("缺少材料映射表路径配置")
    
    # 检查文件监控配置
    if 'file_monitoring' in config:
        file_config = config['file_monitoring']
        file_required = ['onoff_file', 'macro_file']
        for field in file_required:
            if field not in file_config:
                warnings.append(f"缺少文件监控配置: file_monitoring.{field}")
    
    # 检查DNC系统配置
    if 'dnc_system' in config:
        dnc_config = config['dnc_system']
        dnc_required = ['window_title', 'process_name', 'class_name']
        for field in dnc_required:
            if field not in dnc_config:
                warnings.append(f"缺少DNC系统配置: dnc_system.{field}")
    
    # 检查数值配置
    if 'performance' in config:
        perf_config = config['performance']
        numeric_fields = ['ui_automation_timeout', 'file_monitoring_timeout', 
                         'task_scheduling_timeout', 'material_check_timeout']
        for field in numeric_fields:
            if field in perf_config and not isinstance(perf_config[field], (int, float)):
                warnings.append(f"{field} 应该是数字类型")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


def backup_file(file_path: str, backup_dir: str = "backup") -> Optional[str]:
    """备份文件"""
    try:
        source_path = Path(file_path)
        if not source_path.exists():
            return None
        
        # 创建备份目录
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # 生成备份文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"{source_path.stem}_{timestamp}{source_path.suffix}"
        
        # 复制文件
        import shutil
        shutil.copy2(source_path, backup_file)
        
        return str(backup_file)
    except Exception as e:
        logging.error(f"备份文件失败: {e}")
        return None


def cleanup_old_backups(backup_dir: str = "backup", max_backups: int = 10) -> int:
    """清理旧的备份文件"""
    try:
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return 0
        
        # 获取所有备份文件并按修改时间排序
        backup_files = list(backup_path.glob("*"))
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # 删除超出数量的旧备份
        deleted_count = 0
        for backup_file in backup_files[max_backups:]:
            try:
                backup_file.unlink()
                deleted_count += 1
            except Exception as e:
                logging.warning(f"删除备份文件失败 {backup_file}: {e}")
        
        return deleted_count
    except Exception as e:
        logging.error(f"清理备份文件失败: {e}")
        return 0


def format_duration(seconds: float) -> str:
    """格式化时间间隔"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}小时"
    else:
        days = seconds / 86400
        return f"{days:.1f}天"


def safe_execute(func, *args, **kwargs):
    """安全执行函数，捕获异常"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"函数执行失败 {func.__name__}: {e}")
        return None
