"""
多CNC设备管理器
用于同时启动和管理多台不同IP或端口的CNC设备
"""

import argparse
import sys
import json
import threading
import time
from typing import List, Dict, Any
from simulate_fanuc_cnc import FanucCNCSimulator


class MultiCNCManager:
    """多CNC设备管理器"""
    
    def __init__(self):
        self.simulators: List[FanucCNCSimulator] = []
        self.threads: List[threading.Thread] = []
        self.running = False
    
    def add_simulator(self, host: str = 'localhost', port: int = 8193) -> bool:
        """添加一个CNC模拟器"""
        try:
            simulator = FanucCNCSimulator(host, port)
            self.simulators.append(simulator)
            print(f"✅ 已添加CNC模拟器: {host}:{port}")
            return True
        except Exception as e:
            print(f"❌ 添加CNC模拟器失败 {host}:{port} - {e}")
            return False
    
    def add_simulators_from_config(self, config_file: str) -> bool:
        """从配置文件添加多个CNC模拟器"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            machines = config.get('machines', [])
            if not machines:
                print("❌ 配置文件中未找到machines配置")
                return False
            
            success_count = 0
            for machine in machines:
                host = machine.get('host', 'localhost')
                port = machine.get('port', 8193)
                if self.add_simulator(host, port):
                    success_count += 1
            
            print(f"✅ 成功添加 {success_count}/{len(machines)} 台CNC模拟器")
            return success_count > 0
            
        except FileNotFoundError:
            print(f"❌ 配置文件未找到: {config_file}")
            return False
        except json.JSONDecodeError:
            print(f"❌ 配置文件格式错误: {config_file}")
            return False
        except Exception as e:
            print(f"❌ 从配置文件添加CNC模拟器时出错: {e}")
            return False
    
    def add_simulators_from_list(self, machine_list: List[Dict[str, Any]]) -> bool:
        """从列表添加多个CNC模拟器"""
        success_count = 0
        for machine in machine_list:
            host = machine.get('host', 'localhost')
            port = machine.get('port', 8193)
            if self.add_simulator(host, port):
                success_count += 1
        
        print(f"✅ 成功添加 {success_count}/{len(machine_list)} 台CNC模拟器")
        return success_count > 0
    
    def start_all(self) -> bool:
        """启动所有CNC模拟器"""
        if not self.simulators:
            print("❌ 没有添加任何CNC模拟器")
            return False
        
        self.running = True
        started_count = 0
        
        for simulator in self.simulators:
            try:
                # 为每个模拟器创建线程
                thread = threading.Thread(
                    target=self._run_simulator, 
                    args=(simulator,), 
                    daemon=True
                )
                thread.start()
                self.threads.append(thread)
                started_count += 1
                print(f"✅ 启动CNC模拟器: {simulator.host}:{simulator.port}")
            except Exception as e:
                print(f"❌ 启动CNC模拟器失败 {simulator.host}:{simulator.port} - {e}")
        
        if started_count > 0:
            print(f"✅ 成功启动 {started_count}/{len(self.simulators)} 台CNC模拟器")
            return True
        else:
            print("❌ 所有CNC模拟器启动失败")
            return False
    
    def _run_simulator(self, simulator: FanucCNCSimulator):
        """运行单个模拟器"""
        try:
            simulator.start_server()
        except Exception as e:
            print(f"❌ CNC模拟器运行异常 {simulator.host}:{simulator.port} - {e}")
    
    def stop_all(self):
        """停止所有CNC模拟器"""
        print("🛑 正在停止所有CNC模拟器...")
        self.running = False
        
        for simulator in self.simulators:
            try:
                simulator.stop_server()
                print(f"✅ 已停止CNC模拟器: {simulator.host}:{simulator.port}")
            except Exception as e:
                print(f"❌ 停止CNC模拟器时出错 {simulator.host}:{simulator.port} - {e}")
        
        # 等待所有线程结束
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2)  # 等待最多2秒
        
        self.simulators.clear()
        self.threads.clear()
        print("✅ 所有CNC模拟器已停止")


def create_default_config():
    """创建默认配置文件"""
    default_config = {
        "machines": [
            {"host": "127.0.0.1", "port": 8193},
            {"host": "127.0.0.1", "port": 8194},
            {"host": "127.0.0.1", "port": 8195}
        ]
    }
    
    with open('multi_cnc_config.json', 'w', encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    print("✅ 已创建默认配置文件: multi_cnc_config.json")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='多CNC设备管理器')
    parser.add_argument(
        '--config', '-c', 
        help='配置文件路径 (JSON格式)',
        default=None
    )
    parser.add_argument(
        '--create-config', 
        action='store_true',
        help='创建默认配置文件'
    )
    parser.add_argument(
        '--hosts', '-H',
        help='主机地址列表，用逗号分隔',
        default=None
    )
    parser.add_argument(
        '--ports', '-p',
        help='端口列表，用逗号分隔',
        default=None
    )
    
    args = parser.parse_args()
    
    # 创建默认配置文件
    if args.create_config:
        create_default_config()
        return
    
    # 创建管理器
    manager = MultiCNCManager()
    
    # 从配置文件加载
    if args.config:
        if not manager.add_simulators_from_config(args.config):
            print("❌ 从配置文件加载失败")
            return
    # 从命令行参数加载
    elif args.hosts and args.ports:
        hosts = [h.strip() for h in args.hosts.split(',')]
        ports = [int(p.strip()) for p in args.ports.split(',')]
        
        if len(hosts) != len(ports):
            print("❌ 主机地址数量与端口数量不匹配")
            return
        
        machines = [{"host": h, "port": p} for h, p in zip(hosts, ports)]
        if not manager.add_simulators_from_list(machines):
            print("❌ 从命令行参数加载失败")
            return
    # 使用默认配置
    else:
        # 检查默认配置文件是否存在
        import os
        if os.path.exists('multi_cnc_config.json'):
            if not manager.add_simulators_from_config('multi_cnc_config.json'):
                print("❌ 从默认配置文件加载失败")
                return
        else:
            # 添加默认的3台设备
            default_machines = [
                {"host": "127.0.0.1", "port": 8193},
                {"host": "127.0.0.1", "port": 8194},
                {"host": "127.0.0.1", "port": 8195}
            ]
            manager.add_simulators_from_list(default_machines)
    
    # 启动所有模拟器
    if not manager.start_all():
        print("❌ 启动失败")
        return
    
    print("\n" + "=" * 50)
    print("多CNC设备管理器已启动")
    print("按 Ctrl+C 停止所有设备")
    print("=" * 50)
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n收到停止信号...")
    finally:
        manager.stop_all()


if __name__ == "__main__":
    main()