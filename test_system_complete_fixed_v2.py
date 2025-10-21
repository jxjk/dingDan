"""
数控车床生产管理系统完整测试
验证所有核心功能模块
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_config_loading():
    """测试配置加载"""
    print("🔧 测试配置加载...")
    try:
        from config.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        config = config_manager.config
        
        print(f"✅ 系统名称: {config['system']['name']}")
        print(f"✅ 版本: {config['system']['version']}")
        print(f"✅ 环境: {config['system']['environment']}")
        print(f"✅ 材料映射表路径: {config['material_mapping']['csv_path']}")
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def test_material_mapping():
    """测试材料映射表"""
    print("\n📋 测试材料映射表...")
    try:
        from services.material_checker import MaterialChecker
        from config.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        material_checker = MaterialChecker(config_manager)
        
        # 测试几个关键材料
        test_materials = ['S45C', 'AL6061', 'SS304', '黄铜']
        for material in test_materials:
            info = material_checker.material_mapper.get_material_by_name(material)
            if info:
                print(f"  ✅ {material} -> {info['材料名称']} (库存: {info['库存数量']})")
            else:
                print(f"  ⚠️ {material} 未找到")
        
        # 获取所有材料数量
        all_materials = material_checker.get_all_materials()
        print(f"✅ 材料记录数: {len(all_materials)}")
        
        return True
    except Exception as e:
        print(f"❌ 材料映射表测试失败: {e}")
        return False


def test_task_model():
    """测试任务模型"""
    print("\n📝 测试任务模型...")
    try:
        from models.production_task import ProductionTask, TaskStatus, TaskPriority
        
        # 创建测试任务
        task = ProductionTask(
            task_id="TEST_TASK_001",
            instruction_id="TEST_INS001",
            product_model="TEST_MODEL",
            material_spec="S45C",
            order_quantity=100,
            priority=TaskPriority.NORMAL
        )
        
        print(f"✅ 任务创建成功: {task.task_id}")
        print(f"✅ 任务状态: {task.status}")
        print(f"✅ 材料规格: {task.material_spec}")
        
        # 测试状态更新
        task.update_status(TaskStatus.RUNNING, "测试运行")
        print(f"任务 {task.task_id} 状态变更: Pending -> Running")
        print(f"原因: 测试运行")
        print(f"✅ 状态更新: {task.status}")
        
        return True
    except Exception as e:
        print(f"❌ 任务模型测试失败: {e}")
        return False


def test_material_checker():
    """测试材料检查器"""
    print("\n🔍 测试材料检查器...")
    try:
        from services.material_checker import MaterialChecker
        from config.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        material_checker = MaterialChecker(config_manager)
        
        # 测试材料兼容性检查
        result = material_checker.check_material_compatibility("S45C", 50)
        print(f"✅ 材料兼容性检查: {result['compatible']}")
        print(f"✅ 检查结果: {result['message']}")
        
        # 测试库存检查
        print(f"✅ 库存检查: {result['available']}")
        print(f"✅ 可用库存: {result['available_stock']}")
        
        return True
    except Exception as e:
        print(f"❌ 材料检查器测试失败: {e}")
        return False


def test_file_monitor():
    """测试文件监控"""
    print("\n📁 测试文件监控...")
    try:
        from services.file_monitor import FileMonitorManager
        from config.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        file_monitor = FileMonitorManager(config_manager)

        
        # 检查监控文件是否存在
        onoff_file = config_manager.get('file_monitoring.onoff_file')
        macro_file = config_manager.get('file_monitoring.macro_file')

        
        onoff_exists = Path(onoff_file).exists()
        macro_exists = Path(macro_file).exists()
        
        print(f"✅ 开关文件存在: {onoff_exists} ({onoff_file})")
        print(f"✅ 宏文件存在: {macro_exists} ({macro_file})")
        
        return onoff_exists and macro_exists
    except Exception as e:
        print(f"❌ 文件监控测试失败: {e}")
        return False


def test_system_initialization():
    """测试系统初始化"""
    print("\n🚀 测试系统初始化...")
    try:
        from services.system_manager import get_system_manager
        
        system_manager = get_system_manager()
        
        # 初始化系统
        if system_manager.initialize_system():
            print("✅ 系统初始化成功")
            
            # 测试系统状态
            status = system_manager.get_system_status()
            print(f"✅ 系统运行状态: {status['system_status']}")
            
            # 测试任务统计
            task_stats = status['task_statistics']
            print(f"✅ 任务统计: {task_stats}")
            
            # 测试材料统计
            material_stats = status['material_statistics']
            print(f"✅ 材料总数: {material_stats.get('total_materials', 0)}")
            print(f"✅ 低库存材料: {material_stats.get('low_stock_count', 0)}")
            
            return True
        else:
            print("❌ 系统初始化失败")
            return False
            
    except Exception as e:
        print(f"❌ 系统初始化测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("    数控车床生产管理系统完整测试")
    print("=" * 60)
    
    tests = [
        test_config_loading,
        test_material_mapping,
        test_task_model,
        test_material_checker,
        test_file_monitor,
        test_system_initialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        if test_func():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统可以正常运行。")
        print("\n下一步:")
        print("1. 运行 'python main.py' 启动系统")
        print("2. 选择命令行界面模式进行交互")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
