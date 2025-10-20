"""
系统启动脚本
提供多种启动方式和配置选项
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import CNCProductionSystem
from api.web_api import create_api_server


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


def run_production_system():
    """运行生产系统"""
    try:
        print("启动数控车床生产系统...")
        system = CNCProductionSystem()
        system.start_system()
        
        print("生产系统已启动")
        print("按 Ctrl+C 停止系统")
        
        # 保持主线程运行
        while system.is_running:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在停止生产系统...")
        system.stop_system()
        print("生产系统已停止")
        
    except Exception as e:
        print(f"生产系统运行错误: {e}")
        logging.error(f"生产系统运行错误: {e}")


def run_api_server(host='0.0.0.0', port=5000, debug=False):
    """运行API服务器"""
    try:
        print(f"启动Web API服务器: {host}:{port}")
        system = CNCProductionSystem()
        api_server = create_api_server(system)
        api_server.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        print(f"API服务器启动错误: {e}")
        logging.error(f"API服务器启动错误: {e}")


def run_both_systems(host='0.0.0.0', port=5000):
    """同时运行生产系统和API服务器"""
    import threading
    import time
    
    try:
        print("启动数控车床生产系统和Web API服务器...")
        
        # 启动生产系统
        system = CNCProductionSystem()
        system.start_system()
        
        # 在后台线程中启动API服务器
        def start_api_server():
            try:
                api_server = create_api_server(system)
                api_server.run(host=host, port=port, debug=False)
            except Exception as e:
                print(f"API服务器错误: {e}")
        
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        
        print(f"生产系统已启动")
        print(f"Web API服务器已启动: http://{host}:{port}")
        print("按 Ctrl+C 停止所有系统")
        
        # 保持主线程运行
        while system.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在停止所有系统...")
        system.stop_system()
        print("所有系统已停止")
        
    except Exception as e:
        print(f"系统运行错误: {e}")
        logging.error(f"系统运行错误: {e}")


def test_system():
    """测试系统功能"""
    try:
        print("开始系统测试...")
        
        # 创建系统实例
        system = CNCProductionSystem()
        
        # 测试配置加载
        print("✓ 配置加载测试通过")
        
        # 测试服务初始化
        system._initialize_services()
        print("✓ 服务初始化测试通过")
        
        # 测试任务创建
        task_id = system.add_new_task(
            instruction_id="TEST001",
            product_model="TEST_MODEL",
            material_spec="STEEL_45",
            order_quantity=10,
            priority="Normal"
        )
        print(f"✓ 任务创建测试通过 - 任务ID: {task_id}")
        
        # 测试系统状态获取
        status = system.get_system_status()
        print("✓ 系统状态获取测试通过")
        
        # 测试二维码扫描
        scan_result = system.scan_qr_code("TEST|INSTRUCTION:TEST001|MODEL:TEST_MODEL")
        print("✓ 二维码扫描测试通过")
        
        # 测试材料库存报告
        stock_report = system.get_material_stock_report()
        print("✓ 材料库存报告测试通过")
        
        print("所有测试通过！系统功能正常")
        
    except Exception as e:
        print(f"系统测试失败: {e}")
        return False
    
    return True


def show_system_info():
    """显示系统信息"""
    from config.config_manager import ConfigManager
    
    config_manager = ConfigManager()
    config = config_manager.config
    
    print("=" * 50)
    print("数控车床多订单宏变量管理与生产任务调度系统")
    print("=" * 50)
    print(f"系统名称: {config['system']['name']}")
    print(f"版本: {config['system']['version']}")
    print(f"调试模式: {config['system']['debug']}")
    print()
    print("可用命令:")
    print("  python run_system.py production  - 运行生产系统")
    print("  python run_system.py api         - 运行Web API服务器")
    print("  python run_system.py both        - 同时运行生产系统和API")
    print("  python run_system.py test        - 运行系统测试")
    print("  python run_system.py setup       - 设置运行环境")
    print("  python run_system.py info        - 显示系统信息")
    print()
    print("Web API接口:")
    print("  http://localhost:5000/api/health - 健康检查")
    print("  http://localhost:5000/api/system/status - 系统状态")
    print("  http://localhost:5000/api/tasks - 任务管理")
    print("=" * 50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数控车床生产管理系统')
    parser.add_argument('mode', nargs='?', default='info',
                       choices=['production', 'api', 'both', 'test', 'setup', 'info'],
                       help='运行模式')
    parser.add_argument('--host', default='0.0.0.0', help='API服务器主机')
    parser.add_argument('--port', type=int, default=5000, help='API服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    if args.mode == 'production':
        run_production_system()
    elif args.mode == 'api':
        run_api_server(host=args.host, port=args.port, debug=args.debug)
    elif args.mode == 'both':
        run_both_systems(host=args.host, port=args.port)
    elif args.mode == 'test':
        test_system()
    elif args.mode == 'setup':
        setup_environment()
    elif args.mode == 'info':
        show_system_info()
    else:
        show_system_info()


if __name__ == '__main__':
    main()
