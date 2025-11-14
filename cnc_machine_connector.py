"""
CNC机床连接器
用于连接和控制模拟的FANUC CNC机床
"""

import socket
import json
import time
import threading
import logging
from typing import Optional, Dict, Any
from config.config_manager import get_config_manager


class CNCTCPClient:
    """CNC机床TCP客户端"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8193):
        self.host = host
        self.port = port
        self.socket = None
        self.is_connected = False
        self.response_received = None
        self.response_event = threading.Event()
        self.logger = logging.getLogger(__name__)
        # 控制是否显示实时状态更新
        self.show_realtime_status = False
        
    def connect(self) -> bool:
        """连接到CNC机床"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置连接超时
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            
            # 启动接收线程
            receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            receive_thread.start()
            
            # 等待线程启动
            time.sleep(0.1)
            
            # 验证连接是否正常工作 - 发送测试命令
            test_response = self.send_command("get_status")
            if test_response and test_response.get("success"):
                self.logger.info(f"✅ 成功连接到CNC机床 {self.host}:{self.port}")
                return True
            else:
                self.logger.error(f"❌ 连接验证失败: {test_response}")
                self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 连接CNC机床失败: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
            self.is_connected = False
            self.logger.info("已断开与CNC机床的连接")
    
    def _receive_loop(self):
        """接收机床消息的循环"""
        buffer = ""
        while self.is_connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    self.is_connected = False
                    break
                
                buffer += data.decode('utf-8')
                
                # 按行处理
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            response = json.loads(line)
                            # 检查是否是广播消息
                            if response.get("is_broadcast", False):
                                # 这是广播消息，记录状态更新
                                status_data = response.get("data", {})
                                status_msg = (f"[状态更新] 机床状态: {status_data.get('status', 'N/A')}, "
                                              f"程序: {status_data.get('program_name', 'N/A')}")
                                self.logger.debug(status_msg)
                                # 只有在启用时才显示实时状态更新
                                if self.show_realtime_status:
                                    print(status_msg)
                            else:
                                # 这是请求响应，设置响应事件
                                self.response_received = response
                                self.response_event.set()
                        except json.JSONDecodeError:
                            self.logger.error(f"JSON解析失败: {line}")
                            
            except socket.timeout:
                # 接收超时，继续循环
                continue
            except Exception as e:
                if self.is_connected:
                    self.logger.error(f"接收数据时出错: {e}")
                self.is_connected = False
                break
    
    def send_command(self, command: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """发送命令到机床"""
        if not self.is_connected:
            print("未连接到机床")
            return None
        
        try:
            # 清除之前的响应
            self.response_received = None
            self.response_event.clear()
            
            # 构造请求
            request = {"command": command, **kwargs}
            request_str = json.dumps(request, ensure_ascii=False) + "\n"
            
            # 发送请求
            self.socket.send(request_str.encode('utf-8'))
            
            # 等待响应
            if self.response_event.wait(timeout=5.0):
                return self.response_received
            else:
                print("接收响应超时")
                return None
                
        except Exception as e:
            print(f"发送命令时出错: {e}")
            return None


class CNCMachineManager:
    """CNC机床管理器"""
    
    def __init__(self):
        # 使用字典存储多个客户端连接
        self.clients: Dict[str, CNCTCPClient] = {}
        self.connected_machines: Dict[str, str] = {}
        # 获取配置管理器实例
        self.config_manager = get_config_manager()
        # 获取状态映射配置
        self.status_mapping = self.config_manager.get_machine_status_mapping("cnc_simulator")
        # 添加logger
        self.logger = logging.getLogger(__name__)
    
    def connect_machine(self, host: str = '127.0.0.1', port: int = 8193) -> bool:
        """连接到机床"""
        # 使用主机和端口组合作为连接标识
        machine_key = f"{host}:{port}"
        
        # 如果已经存在连接，先断开
        if machine_key in self.clients:
            self.disconnect_machine(host, port)
        
        # 创建新的客户端连接（带重试机制）
        max_retries = 3
        for attempt in range(max_retries):
            client = CNCTCPClient(host, port)
            if client.connect():
                self.clients[machine_key] = client
                self.connected_machines[machine_key] = machine_key
                print(f"✅ 已连接到机床: {machine_key}")
                return True
            else:
                print(f"连接尝试 {attempt + 1}/{max_retries} 失败")
                if attempt < max_retries - 1:
                    time.sleep(1)  # 重试前等待1秒
        
        print(f"❌ 连接机床 {machine_key} 失败，已重试 {max_retries} 次")
        return False
    
    def disconnect_machine(self, host: str = '127.0.0.1', port: int = 8193):
        """断开特定机床连接"""
        machine_key = f"{host}:{port}"
        if machine_key in self.clients:
            self.clients[machine_key].disconnect()
            del self.clients[machine_key]
            if machine_key in self.connected_machines:
                del self.connected_machines[machine_key]
    
    def disconnect_all_machines(self):
        """断开所有机床连接"""
        for machine_key in list(self.clients.keys()):
            host, port_str = machine_key.split(":")
            port = int(port_str)
            self.disconnect_machine(host, port)
    
    def get_client(self, host: str, port: int) -> Optional[CNCTCPClient]:
        """获取指定机床的客户端"""
        machine_key = f"{host}:{port}"
        return self.clients.get(machine_key)
    
    def is_machine_connected(self, host: str, port: int) -> bool:
        """检查机床是否已连接"""
        machine_key = f"{host}:{port}"
        return machine_key in self.clients and self.clients[machine_key].is_connected
    
    def get_machine_status(self, host: str = '127.0.0.1', port: int = 8193) -> Optional[Dict[Any, Any]]:
        """获取指定机床状态"""
        client = self.get_client(host, port)
        if not client:
            self.logger.debug(f"未连接到机床 {host}:{port}")
            return None
        
        try:
            response = client.send_command("get_status")
            if response and response.get("success"):
                # 映射状态到系统内部状态
                status_data = response["data"]
                raw_status = status_data.get("status", "UNKNOWN")
                mapped_status = self.status_mapping.get(raw_status, raw_status)
                status_data["status"] = mapped_status
                response["data"] = status_data
                
            return response
        except Exception as e:
            self.logger.error(f"获取机床 {host}:{port} 状态时出错: {e}")
            return None
    
    def start_machine(self, host: str = '127.0.0.1', port: int = 8193) -> Optional[Dict[Any, Any]]:
        """启动指定机床"""
        client = self.get_client(host, port)
        if not client:
            print(f"未连接到机床 {host}:{port}")
            return None
        
        return client.send_command("start_machine")
    
    def stop_machine(self, host: str = '127.0.0.1', port: int = 8193) -> Optional[Dict[Any, Any]]:
        """停止指定机床"""
        client = self.get_client(host, port)
        if not client:
            print(f"未连接到机床 {host}:{port}")
            return None
        
        return client.send_command("stop_machine")
    
    def pause_machine(self, host: str = '127.0.0.1', port: int = 8193) -> Optional[Dict[Any, Any]]:
        """暂停指定机床"""
        client = self.get_client(host, port)
        if not client:
            print(f"未连接到机床 {host}:{port}")
            return None
        
        return client.send_command("pause_machine")
    
    def resume_machine(self, host: str = '127.0.0.1', port: int = 8193) -> Optional[Dict[Any, Any]]:
        """恢复指定机床"""
        client = self.get_client(host, port)
        if not client:
            print(f"未连接到机床 {host}:{port}")
            return None
        
        return client.send_command("resume_machine")
    
    def trigger_alarm(self, host: str = '127.0.0.1', port: int = 8193, 
                     alarm_code: int = 1001, alarm_message: str = "模拟报警") -> Optional[Dict[Any, Any]]:
        """触发指定机床报警"""
        client = self.get_client(host, port)
        if not client:
            print(f"未连接到机床 {host}:{port}")
            return None
        
        return client.send_command("trigger_alarm", alarm_code=alarm_code, alarm_message=alarm_message)
    
    def clear_alarm(self, host: str = '127.0.0.1', port: int = 8193) -> Optional[Dict[Any, Any]]:
        """清除指定机床报警"""
        client = self.get_client(host, port)
        if not client:
            print(f"未连接到机床 {host}:{port}")
            return None
        
        return client.send_command("clear_alarm")
    
    def get_machine_parameters(self, host: str = '127.0.0.1', port: int = 8193) -> Optional[Dict[Any, Any]]:
        """获取指定机床参数"""
        client = self.get_client(host, port)
        if not client:
            print(f"未连接到机床 {host}:{port}")
            return None
        
        return client.send_command("get_parameters")
    
    def get_axis_data(self, host: str = '127.0.0.1', port: int = 8193) -> Optional[Dict[Any, Any]]:
        """获取指定机床轴数据"""
        client = self.get_client(host, port)
        if not client:
            print(f"未连接到机床 {host}:{port}")
            return None
        
        return client.send_command("get_axis_data")

    # 添加控制机床的统一方法，修复UI界面中的调用错误
    def control_cnc_machine(self, machine_id: str, operation: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """控制CNC机床的统一接口"""
        # 根据machine_id获取对应的主机和端口
        machines_config = self.config_manager.get('machines', {})
        if machine_id not in machines_config:
            print(f"未找到机床 {machine_id} 的配置")
            return None
            
        machine_info = machines_config[machine_id]
        host = machine_info.get('ip_address', '127.0.0.1')
        port = machine_info.get('port', 8193)
        
        # 确保已连接到该机床
        if not self.is_machine_connected(host, port):
            if not self.connect_machine(host, port):
                print(f"无法连接到机床 {machine_id} ({host}:{port})")
                return None
            
        # 根据操作类型调用相应方法
        if operation == "start":
            return self.start_machine(host, port)
        elif operation == "stop":
            return self.stop_machine(host, port)
        elif operation == "pause":
            return self.pause_machine(host, port)
        elif operation == "resume":
            return self.resume_machine(host, port)
        elif operation == "trigger_alarm":
            return self.trigger_alarm(
                host, port,
                alarm_code=kwargs.get("alarm_code", 1001),
                alarm_message=kwargs.get("alarm_message", "模拟报警")
            )
        elif operation == "clear_alarm":
            return self.clear_alarm(host, port)
        else:
            print(f"不支持的操作: {operation}")
            return None


def interactive_cnc_control():
    """交互式CNC控制界面"""
    print("=" * 60)
    print("CNC机床交互控制界面")
    print("=" * 60)
    
    manager = CNCMachineManager()
    
    # 连接到机床
    print("正在连接到CNC机床...")
    if not manager.connect_machine('127.0.0.1', 8193):
        print("连接失败，退出程序")
        return
    
    try:
        while True:
            print("\n" + "-" * 40)
            print("请选择操作:")
            print("1. 获取机床状态")
            print("2. 启动机床")
            print("3. 停止机床")
            print("4. 暂停机床")
            print("5. 恢复机床")
            print("6. 触发报警")
            print("7. 清除报警")
            print("8. 获取机床参数")
            print("9. 获取轴数据")
            print("0. 退出")
            
            choice = input("请输入选项 (0-9): ").strip()
            
            if choice == '0':
                print("退出程序")
                break
            elif choice == '1':
                response = manager.get_machine_status()
                if response and response.get("success"):
                    data = response["data"]
                    print(f"机床ID: {data['machine_id']}")
                    print(f"状态: {data['status']}")
                    print(f"程序: {data['program_name']}")
                    print(f"主轴转速: {data['spindle_speed']} RPM")
                    print(f"进给速度: {data['feed_rate']} mm/min")
                    print(f"报警代码: {data['alarm_code']}")
                    print(f"报警信息: {data['alarm_message']}")
                    print(f"完成工件数: {data['workpiece_count']}")
                    print(f"时间戳: {data['timestamp']}")
                else:
                    print(f"获取状态失败: {response.get('error', '未知错误') if response else '无响应'}")
                    
            elif choice == '2':
                response = manager.start_machine()
                if response and response.get("success"):
                    print(f"启动成功: {response['message']}")
                else:
                    error_msg = response.get('error', '未知错误') if response else '无响应'
                    print(f"启动失败: {error_msg}")
                    
            elif choice == '3':
                response = manager.stop_machine()
                if response and response.get("success"):
                    print(f"停止成功: {response['message']}")
                else:
                    error_msg = response.get('error', '未知错误') if response else '无响应'
                    print(f"停止失败: {error_msg}")
                    
            elif choice == '4':
                response = manager.pause_machine()
                if response and response.get("success"):
                    print(f"暂停成功: {response['message']}")
                else:
                    error_msg = response.get('error', '未知错误') if response else '无响应'
                    print(f"暂停失败: {error_msg}")
                    
            elif choice == '5':
                response = manager.resume_machine()
                if response and response.get("success"):
                    print(f"恢复成功: {response['message']}")
                else:
                    error_msg = response.get('error', '未知错误') if response else '无响应'
                    print(f"恢复失败: {error_msg}")
                    
            elif choice == '6':
                alarm_code = int(input("请输入报警代码 (默认1001): ") or "1001")
                alarm_message = input("请输入报警信息 (默认'模拟报警'): ") or "模拟报警"
                response = manager.trigger_alarm(alarm_code, alarm_message)
                if response and response.get("success"):
                    print(f"触发报警成功: {response['message']}")
                else:
                    error_msg = response.get('error', '未知错误') if response else '无响应'
                    print(f"触发报警失败: {error_msg}")
                    
            elif choice == '7':
                response = manager.clear_alarm()
                if response and response.get("success"):
                    print(f"清除报警成功: {response['message']}")
                else:
                    error_msg = response.get('error', '未知错误') if response else '无响应'
                    print(f"清除报警失败: {error_msg}")
                    
            elif choice == '8':
                response = manager.get_machine_parameters()
                if response and response.get("success"):
                    data = response["data"]
                    print("机床参数:")
                    for key, value in data.items():
                        print(f"  {key}: {value}")
                else:
                    error_msg = response.get('error', '未知错误') if response else '无响应'
                    print(f"获取参数失败: {error_msg}")
                    
            elif choice == '9':
                response = manager.get_axis_data()
                if response and response.get("success"):
                    data = response["data"]
                    print("轴数据:")
                    print(f"  轴位置: {data['axis_positions']}")
                    print(f"  主轴负载: {data['spindle_load']}%")
                else:
                    error_msg = response.get('error', '未知错误') if response else '无响应'
                    print(f"获取轴数据失败: {error_msg}")
                    
            else:
                print("❌ 无效选项，请重新输入")
                
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        # 断开连接
        manager.disconnect_machine()
        print("已断开与机床的连接")


if __name__ == "__main__":
    interactive_cnc_control()
