"""
数控车床生产管理系统主程序
订单管理助手 - 版本 1.0.0
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config_manager import get_config_manager
from services.system_manager import get_system_manager, SystemStatus
from utils.system_utils import setup_logging, get_system_info
from ui.cli_interface import CLIInterface
from ui.gui_starter import start_gui


def main():
    """主程序入口"""
    try:
        print("=" * 60)
        print("    数控车床生产管理系统 - 订单管理助手")
        print("=" * 60)
        
        # 获取系统信息
        system_info = get_system_info()
        print(f"系统平台: {system_info['platform']}")
        print(f"Python版本: {system_info['python_version']}")
        print(f"工作目录: {system_info['working_directory']}")
        print(f"当前时间: {system_info['current_time']}")
        print("-" * 60)
        
        # 初始化配置管理器
        print("🔧 初始化配置管理器...")
        config_manager = get_config_manager()
        
        # 设置日志系统
        print("📝 设置日志系统...")
        logger = setup_logging(config_manager.config)
        
        # 初始化系统管理器
        print("🚀 初始化系统管理器...")
        system_manager = get_system_manager()
        
        # 初始化系统
        print("🔄 初始化系统组件...")
        if not system_manager.initialize_system():
            print("❌ 系统初始化失败")
            return 1
        
        print("✅ 系统初始化完成")
        
        # 显示配置摘要
        config_manager.print_config_summary()
        
        # 选择界面模式
        print("\n🎯 选择界面模式:")
        print("1. 命令行界面 (CLI)")
        print("2. 图形界面 (GUI)")
        print("3. 退出系统")
        
        while True:
            try:
                choice = input("\n请选择模式 (1-3): ").strip()
                
                if choice == "1":
                    print("\n启动命令行界面...")
                    cli = CLIInterface(system_manager, config_manager)
                    cli.run()
                    break
                elif choice == "2":
                    print("\n启动图形界面...")
                    start_gui(system_manager, config_manager)
                    break
                elif choice == "3":
                    print("\n👋 退出系统")
                    return 0
                else:
                    print("❌ 无效选择，请重新输入")
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户中断，退出系统")
                return 0
            except Exception as e:
                print(f"❌ 发生错误: {e}")
                return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        logging.error(f"系统启动失败: {e}")
        return 1


def run_system_test():
    """运行系统测试"""
    try:
        print("\n🧪 运行系统测试...")
        
        # 导入测试模块
        from tests.test_system import SystemTester
        
        # 创建测试器
        tester = SystemTester()
        
        # 运行测试
        test_results = tester.run_all_tests()
        
        # 显示测试结果
        print("\n📊 测试结果:")
        print(f"  总测试数: {test_results['total_tests']}")
        print(f"  通过: {test_results['passed_tests']}")
        print(f"  失败: {test_results['failed_tests']}")
        print(f"  成功率: {test_results['success_rate']:.1f}%")
        
        if test_results['failed_tests'] > 0:
            print("\n❌ 失败的测试:")
            for test_name, error in test_results['failed_details'].items():
                print(f"  - {test_name}: {error}")
        
        return test_results['success_rate'] == 100.0
        
    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        return False


def show_system_status():
    """显示系统状态"""
    try:
        system_manager = get_system_manager()
        status = system_manager.get_system_status()
        
        print("\n📊 系统状态:")
        print(f"  系统状态: {status['system_status']}")
        print(f"  运行时间: {status['uptime']:.1f}秒")
        print(f"  错误计数: {status['error_count']}")
        
        # 任务统计
        task_stats = status['task_statistics']
        if task_stats:
            print(f"  任务统计:")
            print(f"    - 待处理: {task_stats.get('pending', 0)}")
            print(f"    - 运行中: {task_stats.get('running', 0)}")
            print(f"    - 已完成: {task_stats.get('completed', 0)}")
            print(f"    - 总计: {task_stats.get('total', 0)}")
        
        # 材料统计
        material_stats = status['material_statistics']
        if material_stats:
            print(f"  材料统计:")
            print(f"    - 材料总数: {material_stats.get('total_materials', 0)}")
            print(f"    - 总库存: {material_stats.get('total_stock', 0)}")
            print(f"    - 低库存: {material_stats.get('low_stock_count', 0)}")
            print(f"    - 严重库存: {material_stats.get('critical_stock_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取系统状态失败: {e}")
        return False


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # 运行测试模式
            success = run_system_test()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "status":
            # 显示状态模式
            show_system_status()
            sys.exit(0)
        elif sys.argv[1] == "gui":
            # 直接启动GUI模式
            config_manager = get_config_manager()
            system_manager = get_system_manager()
            if system_manager.initialize_system():
                start_gui(system_manager, config_manager)
            else:
                print("❌ 系统初始化失败")
                sys.exit(1)
        elif sys.argv[1] == "cli":
            # 直接启动CLI模式
            config_manager = get_config_manager()
            system_manager = get_system_manager()
            if system_manager.initialize_system():
                cli = CLIInterface(system_manager, config_manager)
                cli.run()
            else:
                print("❌ 系统初始化失败")
                sys.exit(1)
        else:
            print(f"❌ 未知参数: {sys.argv[1]}")
            print("可用参数: test, status, gui, cli")
            sys.exit(1)
    else:
        # 正常启动模式
        exit_code = main()
        sys.exit(exit_code)
