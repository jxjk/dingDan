"""
数控车床生产管理系统启动脚本
精简版主启动器 - 模块化架构
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_tkinter_available():
    """检查Tkinter是否可用"""
    try:
        import tkinter as tk
        return True
    except ImportError:
        return False


def main():
    """主启动函数"""
    print("=" * 60)
    print("    数控车床生产管理系统启动器")
    print("=" * 60)
    
    # 检查Tkinter可用性
    if check_tkinter_available():
        print("检测到图形界面支持，启动GUI模式...")
        try:
            from ui.gui_starter import SystemStarterGUI
            app = SystemStarterGUI()
            app.run()
            return
        except ImportError as e:
            print(f"GUI模块加载失败: {e}")
            print("将使用命令行模式...")
    
    # 使用命令行模式
    print("启动命令行模式...")
    try:
        from services.system_manager import SystemManager
        manager = SystemManager()
        manager.run_cli_mode()
    except ImportError as e:
        print(f"系统管理器加载失败: {e}")
        print("请检查依赖包安装: pip install -r requirements.txt")
        input("按回车键退出...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"启动失败: {e}")
        input("按回车键退出...")
