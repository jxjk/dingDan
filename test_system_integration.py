#!/usr/bin/env python3
"""
系统集成测试脚本
用于验证数控车床生产管理系统各组件是否协调工作
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config_manager import get_config_manager
from services.system_manager import get_system_manager, SystemStatus
from models.production_task import ProductionTask, TaskPriority
from utils.system_utils import setup_logging


def test_system_initialization():
    """测试系统初始化"""
    print("🔧 测试系统初始化...")
    
    # 获取配置管理器
    config_manager = get_config_manager()
    print(f"✅ 配置管理器获取成功: {config_manager.config.get('system.name')}")
    
    # 设置日志
    logger = setup_logging(config_manager.config)
    print("✅ 日志系统设置成功")
    
    # 获取系统管理器
    system_manager = get_system_manager()
    print("✅ 系统管理器获取成功")
    
    # 初始化系统
    if system_manager.initialize_system():
        print("✅ 系统初始化成功")
    else:
        print("❌ 系统初始化失败")
        return False
    
    return True


def test_file_monitoring():
    """测试文件监控功能"""
    print("\n🔍 测试文件监控功能...")
    
    system_manager = get_system_manager()
    
    # 检查配置中的文件路径
    onoff_path = system_manager.config_manager.get('file_monitoring.onoff_file')
    macro_path = system_manager.config_manager.get('file_monitoring.macro_file')
    
    print(f"📋 onoff.txt 路径: {onoff_path}")
    print(f"📋 macro.txt 路径: {macro_path}")
    
    # 检查文件是否存在，如果不存在则创建
    def ensure_file_exists(file_path, default_content=""):
        """确保文件存在"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(default_content, encoding='utf-8')
            print(f"📝 已创建文件: {file_path}")
        else:
            print(f"✅ 文件已存在: {file_path}")
    
    # 创建默认的onoff.txt文件
    ensure_file_exists(onoff_path, "CNC-01=0\nCNC-02=0\nCNC-03=1\n")
    
    # 创建默认的macro.txt文件
    ensure_file_exists(macro_path, "500=1\n502=2000\n")
    
    # 检查文件状态
    file_status = system_manager.check_file_status()
    print(f"📊 文件状态: {file_status}")
    
    return True


def test_machine_states():
    """测试机床状态监控"""
    print("\n🏭 测试机床状态监控...")
    
    system_manager = get_system_manager()
    
    # 获取当前机床状态
    try:
        # 手动触发机床状态更新
        system_manager._update_machine_states()
        print("✅ 机床状态更新成功")
        
        # 检查可用机床
        available_machines = system_manager.task_scheduler.get_available_machines()
        print(f"✅ 可用机床: {available_machines}")
        
        # 检查所有机床状态
        for machine_id, state in system_manager.task_scheduler.machine_states.items():
            print(f"  机床 {machine_id}: {state.current_state}")
        
        return True
    except Exception as e:
        print(f"❌ 机床状态监控测试失败: {e}")
        return False


def test_material_system():
    """测试材料系统"""
    print("\n🧱 测试材料系统...")
    
    system_manager = get_system_manager()
    
    try:
        # 检查材料映射表
        materials = system_manager.get_material_list()
        print(f"📦 材料数量: {len(materials)}")
        
        if materials:
            print("📋 材料列表:")
            for material in materials[:5]:  # 只显示前5个
                print(f"  - {material.get('材料名称', 'N/A')} ({material.get('材料规格', 'N/A')})")
        
        # 检查材料库存报告
        material_stats = system_manager.material_checker.get_material_stock_report()
        print(f"📊 材料统计: {material_stats}")
        
        return True
    except Exception as e:
        print(f"❌ 材料系统测试失败: {e}")
        return False


def test_task_management():
    """测试任务管理"""
    print("\n📋 测试任务管理...")
    
    system_manager = get_system_manager()
    
    try:
        # 添加一个测试任务
        task_id = system_manager.add_new_task(
            instruction_id="TEST-001",
            product_model="TEST-001",
            material_spec="S45C",
            order_quantity=10,
            priority="Normal"
        )
        
        if task_id:
            print(f"✅ 任务创建成功: {task_id}")
        else:
            print("❌ 任务创建失败")
            return False
        
        # 获取任务列表
        tasks = system_manager.get_task_list()
        print(f"📊 任务总数: {len(tasks)}")
        
        # 显示任务信息
        for task in tasks[:3]:  # 只显示前3个
            print(f"  - {task['task_id']}: {task['status']} ({task['material_spec']})")
        
        return True
    except Exception as e:
        print(f"❌ 任务管理测试失败: {e}")
        return False


def test_system_status():
    """测试系统状态"""
    print("\n📡 测试系统状态...")
    
    system_manager = get_system_manager()
    
    try:
        # 获取系统状态
        status = system_manager.get_system_status()
        print(f"📊 系统状态: {status['system_status']}")
        print(f"📊 任务统计: {status['task_statistics']}")
        print(f"📊 材料统计: {status['material_statistics']}")
        
        return True
    except Exception as e:
        print(f"❌ 系统状态测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("    数控车床生产管理系统 - 集成测试")
    print("=" * 60)
    
    # 执行各项测试
    tests = [
        test_system_initialization,
        test_file_monitoring,
        test_machine_states,
        test_material_system,
        test_task_management,
        test_system_status
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed_tests += 1
            else:
                print(f"❌ 测试失败: {test_func.__name__}")
        except Exception as e:
            print(f"❌ 测试异常: {test_func.__name__} - {e}")
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！系统各组件协调工作正常。")
    else:
        print("⚠️  部分测试失败，请检查系统配置。")
    
    print("=" * 60)
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
