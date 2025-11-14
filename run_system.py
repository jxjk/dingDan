"""
系统启动脚本
提供多种启动方式和配置选项
"""

import os
import sys
import argparse
import logging
import subprocess
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def setup_environment():
    """设置运行环境"""
    # 创建必要的目录
    directories = [
        'logs',
        'monitoring',
        'config',
        'data'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("环境设置完成")


def run_multi_cnc_simulators(config_file=None, hosts=None, ports=None):
    """运行多台CNC设备模拟器"""
    try:
        # 构建命令行参数
        cmd = [sys.executable, str(Path(__file__).parent / "multi_cnc_manager.py")]
        
        if config_file:
            cmd.extend(["--config", config_file])
        elif hosts and ports:
            cmd.extend(["--hosts", hosts, "--ports", ports])
        
        print("启动多台CNC设备模拟器...")
        print(f"命令: {' '.join(cmd)}")
        
        # 启动多CNC管理器进程
        process = subprocess.Popen(cmd)
        
        print("多台CNC设备模拟器已启动")
        print("按 Ctrl+C 停止所有设备")
        
        # 等待进程结束
        process.wait()
        
    except KeyboardInterrupt:
        print("\n正在停止所有CNC设备...")
        if 'process' in locals():
            process.terminate()
        print("所有CNC设备已停止")
    except Exception as e:
        print(f"运行多台CNC设备时出错: {e}")


def run_multi_cnc_uis(config_file=None):
    """运行多台CNC机床UI界面"""
    try:
        # 构建命令行参数
        cmd = [sys.executable, str(Path(__file__).parent / "multi_cnc_ui_manager.py")]
        
        if config_file:
            cmd.extend(["--config", config_file])
        
        print("启动多台CNC机床UI界面...")
        print(f"命令: {' '.join(cmd)}")
        
        # 启动多CNC UI管理器进程
        process = subprocess.Popen(cmd)
        
        print("多台CNC机床UI界面已启动")
        print("按 Ctrl+C 停止所有UI界面")
        
        # 等待进程结束
        process.wait()
        
    except KeyboardInterrupt:
        print("\n正在停止所有CNC机床UI界面...")
        if 'process' in locals():
            process.terminate()
        print("所有CNC机床UI界面已停止")
    except Exception as e:
        print(f"运行多台CNC机床UI界面时出错: {e}")


def create_multi_cnc_config():
    """创建多台CNC设备配置文件"""
    config = {
        "machines": [
            {"host": "127.0.0.1", "port": 8193},
            {"host": "127.0.0.1", "port": 8194},
            {"host": "127.0.0.1", "port": 8195}
        ]
    }
    
    with open("multi_cnc_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("已创建默认多台CNC设备配置文件: multi_cnc_config.json")


def create_multi_cnc_ui_config():
    """创建多台CNC机床UI配置文件"""
    config = {
        "machines": [
            {"machine_id": "CNC-01", "host": "127.0.0.1", "port": 8193},
            {"machine_id": "CNC-02", "host": "127.0.0.1", "port": 8194},
            {"machine_id": "CNC-03", "host": "127.0.0.1", "port": 8195}
        ]
    }
    
    with open("multi_cnc_ui_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("已创建默认多台CNC机床UI配置文件: multi_cnc_ui_config.json")


def show_system_info():
    """显示系统信息"""
    try:
        from config.config_manager import ConfigManager
        config_manager = ConfigManager()
        config = config_manager.config
        
        print("=" * 50)
        print("数控车床多订单宏变量管理与生产任务调度系统")
        print("=" * 50)
        print(f"系统名称: {config['system']['name']}")
        print(f"版本: {config['system']['version']}")
        print()
    except:
        print("=" * 50)
        print("数控车床多订单宏变量管理与生产任务调度系统")
        print("=" * 50)
    
    print("可用命令:")
    print("  python run_system.py multi-cnc      - 运行多台CNC设备模拟器")
    print("  python run_system.py multi-cnc-ui   - 运行多台CNC机床UI界面")
    print("  python run_system.py create-multi-config    - 创建多台CNC设备配置文件")
    print("  python run_system.py create-multi-ui-config - 创建多台CNC机床UI配置文件")
    print("  python run_system.py setup          - 设置运行环境")
    print("  python run_system.py info           - 显示系统信息")
    print("=" * 50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数控车床生产管理系统')
    parser.add_argument('mode', nargs='?', default='info',
                       choices=['setup', 'info', 'multi-cnc', 'multi-cnc-ui', 
                                'create-multi-config', 'create-multi-ui-config'],
                       help='运行模式')
    parser.add_argument('--config', help='多台CNC设备配置文件')
    parser.add_argument('--hosts', help='主机地址列表，用逗号分隔')
    parser.add_argument('--ports', help='端口列表，用逗号分隔')
    
    args = parser.parse_args()
    
    if args.mode == 'multi-cnc':
        run_multi_cnc_simulators(
            config_file=args.config,
            hosts=args.hosts,
            ports=args.ports
        )
    elif args.mode == 'multi-cnc-ui':
        run_multi_cnc_uis(config_file=args.config)
    elif args.mode == 'create-multi-config':
        create_multi_cnc_config()
    elif args.mode == 'create-multi-ui-config':
        create_multi_cnc_ui_config()
    elif args.mode == 'setup':
        setup_environment()
    elif args.mode == 'info':
        show_system_info()
    else:
        show_system_info()


if __name__ == '__main__':
    main()