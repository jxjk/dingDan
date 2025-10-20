"""
系统验证脚本
用于验证数控车床生产管理系统的基本功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def verify_imports():
    """验证所有模块导入是否正常"""
    print("=" * 60)
    print("验证系统模块导入...")
    print("=" * 60)
    
    modules_to_test = [
        ("config.config_manager", "ConfigManager"),
        ("models.production_task", "ProductionTask"),
        ("services.material_checker", "MaterialMappingManager"),
        ("services.task_scheduler", "TaskScheduler"),
        ("services.file_monitor", "FileMonitorManager"),
        ("services.ui_automation", "QRCodeScanner"),
        ("utils.logger", "setup_logging"),
        ("api.web_api", "create_api_server"),
        ("main", "CNCProductionSystem")
    ]
    
    all_imports_successful = True
    
    for module_path, class_name in modules_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            if hasattr(module, class_name):
                print(f"✓ {module_path}.{class_name} - 导入成功")
            else:
                print(f"✗ {module_path}.{class_name} - 类不存在")
                all_imports_successful = False
        except ImportError as e:
            print(f"✗ {module_path}.{class_name} - 导入失败: {e}")
            all_imports_successful = False
        except Exception as e:
            print(f"✗ {module_path}.{class_name} - 错误: {e}")
            all_imports_successful = False
    
    return all_imports_successful

def verify_config():
    """验证配置文件"""
    print("\n" + "=" * 60)
    print("验证配置文件...")
    print("=" * 60)
    
    try:
        from config.config_manager import ConfigManager
        config_manager = ConfigManager()
        config = config_manager.config
        
        required_sections = ['system', 'logging', 'file_monitoring', 'scheduling']
        for section in required_sections:
            if section in config:
                print(f"✓ 配置段 '{section}' - 存在")
            else:
                print(f"✗ 配置段 '{section}' - 缺失")
                return False
        
        print("✓ 配置文件验证通过")
        return True
        
    except Exception as e:
        print(f"✗ 配置文件验证失败: {e}")
        return False

def verify_basic_functionality():
    """验证基本功能"""
    print("\n" + "=" * 60)
    print("验证基本功能...")
    print("=" * 60)
    
    try:
        # 测试任务创建
        from models.production_task import ProductionTask, TaskStatus
        task = ProductionTask(
            task_id="VERIFY001",
            instruction_id="INS001",
            product_model="TEST_MODEL",
            material_spec="STEEL_45",
            order_quantity=10
        )
        print("✓ 任务创建 - 成功")
        
        # 测试任务状态转换
        task.update_status(TaskStatus.RUNNING, "测试状态转换")
        if task.status == TaskStatus.RUNNING:
            print("✓ 任务状态转换 - 成功")
        else:
            print("✗ 任务状态转换 - 失败")
            return False
        
        # 测试任务序列化
        task_dict = task.to_dict()
        if isinstance(task_dict, dict) and 'task_id' in task_dict:
            print("✓ 任务序列化 - 成功")
        else:
            print("✗ 任务序列化 - 失败")
            return False
        
        # 测试二维码解析
        from services.ui_automation import QRCodeScanner
        scanner = QRCodeScanner()
        test_qr = "INSTRUCTION:INS001|MODEL:MODEL_A|MATERIAL:STEEL_45|QUANTITY:100"
        result = scanner.simulate_scan(test_qr)
        if result['success']:
            print("✓ 二维码解析 - 成功")
        else:
            print("✗ 二维码解析 - 失败")
            return False
        
        print("✓ 基本功能验证通过")
        return True
        
    except Exception as e:
        print(f"✗ 基本功能验证失败: {e}")
        return False

def verify_system_creation():
    """验证系统创建"""
    print("\n" + "=" * 60)
    print("验证系统创建...")
    print("=" * 60)
    
    try:
        from main import CNCProductionSystem
        system = CNCProductionSystem()
        
        # 检查系统组件
        components = [
            ('配置管理器', system.config_manager),
            ('任务调度器', system.task_scheduler),
            ('材料检查器', system.material_checker),
            ('文件监控器', system.file_monitor),
            ('自动化管理器', system.automation_manager)
        ]
        
        for name, component in components:
            if component is not None:
                print(f"✓ {name} - 初始化成功")
            else:
                print(f"✗ {name} - 初始化失败")
                return False
        
        # 测试任务添加
        task_id = system.add_new_task(
            instruction_id="VERIFY002",
            product_model="TEST_MODEL",
            material_spec="STEEL_45",
            order_quantity=5
        )
        if task_id:
            print(f"✓ 任务添加 - 成功 (任务ID: {task_id})")
        else:
            print("✗ 任务添加 - 失败")
            return False
        
        # 测试系统状态获取
        status = system.get_system_status()
        if isinstance(status, dict) and 'total_tasks' in status:
            print("✓ 系统状态获取 - 成功")
        else:
            print("✗ 系统状态获取 - 失败")
            return False
        
        print("✓ 系统创建验证通过")
        return True
        
    except Exception as e:
        print(f"✗ 系统创建验证失败: {e}")
        return False

def main():
    """主验证函数"""
    print("数控车床生产管理系统验证")
    print("=" * 60)
    
    results = []
    
    # 执行各项验证
    results.append(("模块导入", verify_imports()))
    results.append(("配置文件", verify_config()))
    results.append(("基本功能", verify_basic_functionality()))
    results.append(("系统创建", verify_system_creation()))
    
    # 输出验证结果
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有验证通过！系统功能正常。")
        return 0
    else:
        print("❌ 部分验证失败，请检查系统配置。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
