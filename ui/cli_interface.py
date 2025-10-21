"""
数控车床生产管理系统命令行界面
提供用户交互功能
"""

import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.system_manager import get_system_manager, SystemStatus


class CLIInterface:
    """命令行界面"""
    
    def __init__(self, system_manager=None, config_manager=None):
        self.system_manager = system_manager or get_system_manager()
        self.config_manager = config_manager
        self.is_running = False
    
    def run(self):
        """运行命令行界面"""
        print("=" * 50)
        print("   数控车床生产管理系统")
        print("=" * 50)
        
        try:
            # 初始化系统
            print("正在初始化系统...")
            if not self.system_manager.initialize_system():
                print("❌ 系统初始化失败")
                return
            
            # 检查系统是否已初始化
            if not self.system_manager.is_initialized:
                print("❌ 系统未初始化")
                return
            
            self.is_running = True
            
            print("✅ 系统启动成功！")
            print("输入 'help' 查看可用命令")
            
            # 启动命令处理线程
            self._start_command_processor()
            
            # 保持主线程运行
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n正在停止系统...")
            self.stop()
        except Exception as e:
            print(f"系统启动失败: {e}")
    
    def stop(self):
        """停止系统"""
        self.is_running = False
        print("系统已停止")
    
    def _start_command_processor(self):
        """启动命令处理线程"""
        def command_worker():
            while self.is_running:
                try:
                    command = input("\n请输入命令: ").strip().lower()
                    self._process_command(command)
                except EOFError:
                    break
                except Exception as e:
                    print(f"命令处理错误: {e}")
        
        command_thread = threading.Thread(target=command_worker, daemon=True)
        command_thread.start()
    
    def _process_command(self, command: str):
        """处理用户命令"""
        if command == 'help':
            self._show_help()
        elif command == 'status':
            self._show_system_status()
        elif command == 'tasks':
            self._show_tasks()
        elif command == 'materials':
            self._show_materials()
        elif command == 'add_task':
            self._add_task()
        elif command == 'scan_qr':
            self._scan_qr_code()
        elif command == 'exit' or command == 'quit':
            print("正在退出系统...")
            self.stop()
        elif command == '':
            pass
        else:
            print(f"未知命令: {command}")
            print("输入 'help' 查看可用命令")
    
    def _show_help(self):
        """显示帮助信息"""
        print("\n可用命令:")
        print("  help      - 显示此帮助信息")
        print("  status    - 显示系统状态")
        print("  tasks     - 显示任务列表")
        print("  materials - 显示材料库存")
        print("  add_task  - 添加新任务")
        print("  scan_qr   - 扫描二维码")
        print("  exit/quit - 退出系统")
    
    def _show_system_status(self):
        """显示系统状态"""
        try:
            status = self.system_manager.get_system_status()
            print("\n=== 系统状态 ===")
            print(f"系统状态: {status['system_status']}")
            print(f"运行时间: {status['uptime']:.1f}秒")
            print(f"错误计数: {status['error_count']}")
            
            task_stats = status['task_statistics']
            if task_stats:
                print(f"\n任务统计:")
                print(f"  待处理: {task_stats.get('pending', 0)}")
                print(f"  运行中: {task_stats.get('running', 0)}")
                print(f"  已完成: {task_stats.get('completed', 0)}")
                print(f"  总计: {task_stats.get('total', 0)}")
            
            material_stats = status['material_statistics']
            if material_stats:
                print(f"\n材料统计:")
                print(f"  材料总数: {material_stats.get('total_materials', 0)}")
                print(f"  总库存: {material_stats.get('total_stock', 0)}")
                print(f"  低库存: {material_stats.get('low_stock_count', 0)}")
                print(f"  严重库存: {material_stats.get('critical_stock_count', 0)}")
                
        except Exception as e:
            print(f"❌ 获取系统状态失败: {e}")
    
    def _show_tasks(self):
        """显示任务列表"""
        try:
            status = self.system_manager.get_system_status()
            task_stats = status['task_statistics']
            print(f"\n=== 任务列表 ===")
            print(f"总计: {task_stats.get('total', 0)} 个任务")
            print(f"待处理: {task_stats.get('pending', 0)}")
            print(f"运行中: {task_stats.get('running', 0)}")
            print(f"已完成: {task_stats.get('completed', 0)}")
            
            # 这里可以扩展显示具体任务详情
            print("(任务详情功能待实现)")
            
        except Exception as e:
            print(f"❌ 获取任务列表失败: {e}")
    
    def _show_materials(self):
        """显示材料库存"""
        try:
            material_stats = self.system_manager.get_system_status()['material_statistics']
            print(f"\n=== 材料库存报告 ===")
            print(f"材料总数: {material_stats.get('total_materials', 0)}")
            print(f"低库存材料: {material_stats.get('low_stock_count', 0)}")
            print(f"严重库存: {material_stats.get('critical_stock_count', 0)}")
            
            # 这里可以扩展显示具体材料详情
            print("(材料详情功能待实现)")
            
        except Exception as e:
            print(f"❌ 获取材料库存失败: {e}")
    
    def _add_task(self):
        """添加新任务"""
        try:
            print("\n=== 添加新任务 ===")
            instruction_id = input("指示书编号: ").strip()
            product_model = input("产品型号: ").strip()
            material_spec = input("材料规格: ").strip()
            order_quantity = int(input("订单数量: ").strip())
            priority = input("优先级 (Normal/High/Urgent) [默认: Normal]: ").strip() or "Normal"
            
            # 使用系统管理器添加任务
            task_id = self.system_manager.add_new_task(
                instruction_id, product_model, material_spec, order_quantity, priority
            )
            
            if task_id:
                print(f"✅ 任务添加成功! 任务ID: {task_id}")
            else:
                print("❌ 任务添加失败")
            
        except ValueError:
            print("❌ 输入格式错误，请确保数量为数字")
        except Exception as e:
            print(f"❌ 添加任务失败: {e}")
    
    def _scan_qr_code(self):
        """扫描二维码"""
        try:
            print("\n=== 扫描二维码 ===")
            qr_content = input("请输入二维码内容: ").strip()
            
            if not qr_content:
                print("❌ 二维码内容不能为空")
                return
            
            result = self.system_manager.scan_qr_code(qr_content)
            
            if result['success']:
                print("✅ 二维码扫描成功!")
                parsed_data = result['parsed_data']
                print(f"材料名称: {parsed_data.get('material_name', '未知')}")
                print(f"材料规格: {parsed_data.get('material_spec', '未知')}")
                print(f"当前库存: {parsed_data.get('current_stock', '未知')}")
                print(f"供应商: {parsed_data.get('supplier', '未知')}")
            else:
                print(f"❌ 二维码扫描失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 扫描二维码失败: {e}")


def main():
    """主函数"""
    try:
        cli = CLIInterface()
        cli.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行错误: {e}")


if __name__ == "__main__":
    main()