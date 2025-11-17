"""
命令行界面模块
提供基于命令行的系统交互界面
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
from services.system_manager import SystemManager
from config.config_manager import get_config_manager

class CLIInterface:
    """命令行界面"""
    
    def __init__(self, system_manager=None, config_manager=None):
        self.system_manager = system_manager or get_system_manager()
        self.config_manager = config_manager
        self.is_running = False
        # 初始化时默认禁用实时状态显示
        self._disable_realtime_status_display()
    
    def _disable_realtime_status_display(self):
        """禁用实时状态显示以避免干扰用户输入"""
        try:
            if self.system_manager and self.system_manager.cnc_connector:
                cnc_connector = self.system_manager.cnc_connector
                for client in cnc_connector.clients.values():
                    client.show_realtime_status = False
        except Exception as e:
            pass  # 忽略初始化时的错误
    
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
            
            # 启动系统（激活机床监控等）
            print("正在启动系统...")
            if not self.system_manager.start_system():
                print("❌ 系统启动失败")
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
        elif command == 'machines':
            self._show_machines()
        elif command == 'add_task':
            self._add_task()
        elif command == 'scan_qr':
            self._scan_qr_code()
        elif command == 'connect':
            self._connect_machines()
        elif command == 'refresh':
            self._refresh_machine_states()
        elif command == 'schedule':
            self._manual_schedule()
        elif command == 'toggle_status':
            self._toggle_realtime_status()
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
        print("  help           - 显示此帮助信息")
        print("  status         - 显示系统状态")
        print("  tasks          - 显示任务列表")
        print("  materials      - 显示材料库存")
        print("  machines       - 显示连接的机床设备状态")
        print("  connect        - 主动连接所有机床")
        print("  refresh        - 刷新机床状态")
        print("  schedule       - 手动触发任务调度")
        print("  toggle_status  - 切换实时状态显示")
        print("  add_task       - 添加新任务")
        print("  scan_qr        - 扫描二维码")
        print("  exit/quit      - 退出系统")
    
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
                
            # 显示机床状态
            machine_states = self.system_manager.task_scheduler.machine_states if self.system_manager.task_scheduler else {}
            if machine_states:
                print(f"\n机床状态 ({len(machine_states)}台):")
                print(f"{'机床ID':<15} {'状态':<15} {'当前材料':<15} {'当前任务':<20}")
                print("-" * 65)
                
                for machine_id, state in machine_states.items():
                    # 获取当前任务
                    current_task = state.current_task if state.current_task else "无"
                    print(f"{machine_id:<15} {state.current_state:<15} {state.current_material:<15} {current_task:<20}")
            else:
                print("\n机床状态: 无连接的机床设备")
                
        except Exception as e:
            print(f"❌ 获取系统状态失败: {e}")
    
    def _show_machines(self):
        """显示连接的机床设备状态"""
        try:
            # 检查系统管理器和任务调度器是否已初始化
            if not self.system_manager:
                print("❌ 系统管理器未初始化")
                return
            
            if not self.system_manager.task_scheduler:
                print("❌ 任务调度器未初始化")
                return
            
            # 获取配置中的机床列表
            machines_config = self.system_manager.config_manager.get('machines', {})
            if not machines_config:
                print("ℹ️  配置文件中未定义任何机床")
                return
            
            print(f"\n=== 配置的机床设备 ({len(machines_config)}台) ===")
            print(f"{'机床ID':<15} {'IP地址':<15} {'端口':<8} {'配置材料':<15} {'连接状态':<15}")
            print("-" * 70)
            
            # 检查CNC连接器是否存在
            cnc_connector = self.system_manager.cnc_connector
            
            for machine_id, machine_info in machines_config.items():
                host = machine_info.get('ip_address', '127.0.0.1')
                port = machine_info.get('port', 8193)
                material = machine_info.get('material', '未知')
                
                # 检查连接状态
                connection_status = "未知"
                if cnc_connector:
                    if cnc_connector.is_machine_connected(host, port):
                        connection_status = "✅ 已连接"
                    else:
                        connection_status = "❌ 未连接"
                else:
                    connection_status = "🚫 无连接器"
                
                print(f"{machine_id:<15} {host:<15} {port:<8} {material:<15} {connection_status:<15}")
            
            # 获取当前连接状态
            machine_states = self.system_manager.task_scheduler.machine_states
            if machine_states:
                print(f"\n=== 已连接的机床设备 ({len(machine_states)}台) ===")
                print(f"{'机床ID':<15} {'状态':<15} {'当前材料':<15} {'当前任务':<20} {'能力':<20}")
                print("-" * 85)
                
                for machine_id, state in machine_states.items():
                    # 获取机床能力
                    capabilities = ",".join(state.capabilities) if state.capabilities else "未知"
                    
                    # 获取当前任务
                    current_task = state.current_task if state.current_task else "无"
                    
                    print(f"{machine_id:<15} {state.current_state:<15} {state.current_material:<15} {current_task:<20} {capabilities:<20}")
            else:
                print("\n⚠️  尚未建立与任何机床的连接")
                print("提示: 确保机床模拟器正在运行，并且系统已正确启动")
                print("      可尝试使用 'connect' 命令重新连接机床")
                print("      或使用 'refresh' 命令刷新机床状态")
                
        except Exception as e:
            print(f"❌ 获取机床状态失败: {e}")
            import traceback
            traceback.print_exc()
    
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

    def _connect_machines(self):
        """主动连接所有机床"""
        try:
            print("\n=== 连接所有机床 ===")
            # 重新初始化系统以连接所有机床
            if self.system_manager.initialize_system():
                print("✅ 机床连接操作完成")
                # 重新启动系统以激活监控
                self.system_manager.start_system()
            else:
                print("❌ 机床连接操作失败")
        except Exception as e:
            print(f"❌ 连接机床时出错: {e}")

    def _refresh_machine_states(self):
        """刷新机床状态"""
        try:
            print("\n=== 刷新机床状态 ===")
            
            # 检查系统管理器和任务调度器是否已初始化
            if not self.system_manager:
                print("❌ 系统管理器未初始化")
                return
            
            if not self.system_manager.task_scheduler:
                print("❌ 任务调度器未初始化")
                return
            
            # 手动更新机床状态
            self.system_manager._update_machine_states()
            
            # 显示更新后的机床状态
            machine_states = self.system_manager.task_scheduler.machine_states
            if machine_states:
                print(f"\n=== 已连接的机床设备 ({len(machine_states)}台) ===")
                print(f"{'机床ID':<15} {'状态':<15} {'当前材料':<15} {'当前任务':<20} {'能力':<20}")
                print("-" * 85)
                
                for machine_id, state in machine_states.items():
                    # 获取机床能力
                    capabilities = ",".join(state.capabilities) if state.capabilities else "未知"
                    
                    # 获取当前任务
                    current_task = state.current_task if state.current_task else "无"
                    
                    print(f"{machine_id:<15} {state.current_state:<15} {state.current_material:<15} {current_task:<20} {capabilities:<20}")
            else:
                print("\n⚠️  尚未建立与任何机床的连接")
                
            print("✅ 机床状态刷新完成")
            
        except Exception as e:
            print(f"❌ 刷新机床状态失败: {e}")
            import traceback
            traceback.print_exc()

    def _toggle_realtime_status(self):
        """切换实时状态显示"""
        try:
            print("\n=== 切换实时状态显示 ===")
            
            # 检查CNC连接器是否存在
            cnc_connector = self.system_manager.cnc_connector
            if not cnc_connector:
                print("❌ CNC连接器未初始化")
                return
            
            # 获取当前状态
            current_status = False
            for client in cnc_connector.clients.values():
                current_status = client.show_realtime_status
                break
            
            # 切换状态
            new_status = not current_status
            
            # 更新所有客户端的状态显示设置
            updated_count = 0
            for client in cnc_connector.clients.values():
                client.show_realtime_status = new_status
                updated_count += 1
            
            status_text = "启用" if new_status else "禁用"
            print(f"✅ 已{status_text}实时状态显示 (更新了 {updated_count} 个连接)")
            print(f"   实时状态显示当前状态: {'开启' if new_status else '关闭'}")
            
        except Exception as e:
            print(f"❌ 切换实时状态显示失败: {e}")

    def _manual_schedule(self):
        """手动触发任务调度"""
        try:
            print("\n=== 手动触发任务调度 ===")
            
            # 检查系统管理器和任务调度器是否已初始化
            if not self.system_manager:
                print("❌ 系统管理器未初始化")
                return
            
            if not self.system_manager.task_scheduler:
                print("❌ 任务调度器未初始化")
                return
            
            print("正在执行任务调度...")
            
            # 执行任务调度
            assignments = self.system_manager.task_scheduler.schedule_tasks()
            
            if assignments:
                print(f"✅ 调度完成，共分配 {len(assignments)} 个任务:")
                for task, machine_id in assignments:
                    print(f"  - 任务 {task.task_id} 分配到机床 {machine_id}")
            else:
                print("ℹ️  没有任务被分配")
                pending_count = len(self.system_manager.task_scheduler.pending_tasks)
                available_machines = self.system_manager.task_scheduler.get_available_machines()
                print(f"  待处理任务数: {pending_count}")
                print(f"  可用机床数: {len(available_machines)}")
                if pending_count > 0 and len(available_machines) == 0:
                    print("  ⚠️  有任务待处理但没有可用机床，请检查机床连接状态和状态配置")
                
        except Exception as e:
            print(f"❌ 手动调度任务失败: {e}")
            import traceback
            traceback.print_exc()


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