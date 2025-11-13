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
from ui.gui_starter import main as start_gui


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
                    start_gui()
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
        print("=" * 60)
        print("    数控车床生产管理系统 - 系统测试")
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
        
        # 运行系统测试
        print("\n🚀 运行系统测试...")
        if not system_manager.run_tests():
            print("❌ 系统测试失败")
            return 1
        
        print("✅ 系统测试完成")
        
        return 0
        
    except Exception as e:
        print(f"❌ 系统测试失败: {e}")
        logging.error(f"系统测试失败: {e}")
        return 1


if __name__ == "__main__":
    main()
