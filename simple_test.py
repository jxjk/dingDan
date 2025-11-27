#!/usr/bin/env python3
"""
简化版系统集成测试
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """测试基本导入"""
    print("Testing basic imports...")
    
    try:
        from config.config_manager import get_config_manager
        print("✅ Config manager import successful")
        
        from services.system_manager import get_system_manager
        print("✅ System manager import successful")
        
        from models.production_task import ProductionTask, TaskPriority
        print("✅ Production task model import successful")
        
        from utils.system_utils import setup_logging
        print("✅ System utils import successful")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config_manager():
    """测试配置管理器"""
    print("\nTesting config manager...")
    
    try:
        config_manager = get_config_manager()
        print(f"✅ Config manager created: {config_manager.config.get('system.name', 'N/A')}")
        
        # 检查关键配置
        onoff_path = config_manager.get('file_monitoring.onoff_file')
        macro_path = config_manager.get('file_monitoring.macro_file')
        print(f"📋 onoff.txt path: {onoff_path}")
        print(f"📋 macro.txt path: {macro_path}")
        
        return True
    except Exception as e:
        print(f"❌ Config manager test failed: {e}")
        return False

def test_system_manager():
    """测试系统管理器"""
    print("\nTesting system manager...")
    
    try:
        # 获取系统管理器
        system_manager = get_system_manager()
        print("✅ System manager created")
        
        # 检查系统管理器的各组件
        components = [
            ('config_manager', system_manager.config_manager),
            ('material_checker', system_manager.material_checker),
            ('task_scheduler', system_manager.task_scheduler),
            ('task_executor', system_manager.task_executor),
            ('file_monitor', system_manager.file_monitor),
            ('ui_automation', system_manager.ui_automation)
        ]
        
        for name, component in components:
            if component:
                print(f"✅ {name} is initialized")
            else:
                print(f"⚠️  {name} is not initialized (will be initialized later)")
        
        return True
    except Exception as e:
        print(f"❌ System manager test failed: {e}")
        return False

def test_material_mapping():
    """测试材料映射"""
    print("\nTesting material mapping...")
    
    try:
        system_manager = get_system_manager()
        
        # 初始化系统
        if system_manager.initialize_system():
            print("✅ System initialized successfully")
        else:
            print("❌ System initialization failed")
            return False
        
        # 检查材料映射
        materials = system_manager.get_material_list()
        print(f"📦 Materials found: {len(materials)}")
        
        if materials:
            for material in materials[:3]:  # 显示前3个
                print(f"  - {material.get('材料名称', 'N/A')} ({material.get('材料规格', 'N/A')})")
        
        return True
    except Exception as e:
        print(f"❌ Material mapping test failed: {e}")
        return False

def main():
    print("="*50)
    print("Simplified System Integration Test")
    print("="*50)
    
    tests = [
        test_basic_imports,
        test_config_manager,
        test_system_manager,
        test_material_mapping
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"❌ Test {test.__name__} failed")
    
    print("\n"+"="*50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
