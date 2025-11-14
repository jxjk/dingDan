"""
模拟FANUC CNC机床的FOCAS2服务器端程序
用于模拟机床的运行、停止、报警等状态
通过TCP/IP协议进行通信
"""

import socket
import threading
import time
import json
import random
import argparse
from datetime import datetime
from enum import Enum


class CNCStatus(Enum):
    """CNC机床状态枚举"""
    OFF = "OFF"           # 关机
    IDLE = "IDLE"         # 空闲
    RUNNING = "RUNNING"   # 运行中
    ALARM = "ALARM"       # 报警
    STOPPED = "STOPPED"   # 停止
    PAUSED = "PAUSED"     # 暂停


class FanucCNCSimulator:
    """FANUC CNC机床模拟器"""
    
    def __init__(self, host='localhost', port=8193):
        self.host = host
        self.port = port
        self.status = CNCStatus.OFF
        self.machine_id = f"FANUC-CNC-{random.randint(1000, 9999)}"
        self.program_name = ""
        self.spindle_speed = 0
        self.feed_rate = 0
        self.alarm_code = 0
        self.alarm_message = ""
        self.is_running = False
        self.server_socket = None
        self.clients = []
        self.client_lock = threading.Lock()
        
        # 机床参数
        self.current_tool = 1
        self.workpiece_count = 0
        self.spindle_load = 0
        self.axis_positions = {"X": 0.0, "Z": 0.0}
        
        print(f"初始化FANUC CNC模拟器: {self.machine_id}")
    
    def start_server(self):
        """启动服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.is_running = True
            
            print(f"FOCAS2模拟服务器启动成功: {self.host}:{self.port}")
            print("等待客户端连接...")
            
            # 启动状态更新线程
            status_thread = threading.Thread(target=self._update_status, daemon=True)
            status_thread.start()
            
            while self.is_running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"客户端连接: {address}")
                    
                    # 添加客户端到列表
                    with self.client_lock:
                        self.clients.append(client_socket)
                    
                    # 为每个客户端创建处理线程
                    client_thread = threading.Thread(
                        target=self._handle_client, 
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.is_running:
                        print(f"接受客户端连接时出错: {e}")
                        
        except Exception as e:
            print(f"启动服务器失败: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """停止服务器"""
        print("正在停止服务器...")
        self.is_running = False
        self.status = CNCStatus.OFF
        
        # 关闭所有客户端连接
        with self.client_lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients.clear()
        
        # 关闭服务器套接字
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("服务器已停止")
    
    def _handle_client(self, client_socket, address):
        """处理客户端请求"""
        try:
            buffer = ""
            while self.is_running:
                # 接收客户端请求
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    buffer += data
                    # 按行分割处理
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            print(f"收到客户端 {address} 请求: {line}")
                            
                            # 解析请求并生成响应
                            response = self._process_request(line)
                            
                            # 发送响应
                            response_str = json.dumps(response, ensure_ascii=False) + "\n"
                            client_socket.send(response_str.encode('utf-8'))
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"处理客户端 {address} 请求时出错: {e}")
                    break
                    
        except Exception as e:
            print(f"客户端 {address} 连接异常: {e}")
        finally:
            # 移除客户端
            with self.client_lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            try:
                client_socket.close()
            except:
                pass
            print(f"客户端 {address} 连接已断开")
    
    def _process_request(self, request):
        """处理客户端请求"""
        try:
            # 解析请求
            request_data = json.loads(request)
            command = request_data.get("command", "")
            
            # 根据命令生成响应
            if command == "get_status":
                return self._get_status_response()
            elif command == "start_machine":
                return self._start_machine()
            elif command == "stop_machine":
                return self._stop_machine()
            elif command == "pause_machine":
                return self._pause_machine()
            elif command == "resume_machine":
                return self._resume_machine()
            elif command == "trigger_alarm":
                alarm_code = request_data.get("alarm_code", 1001)
                alarm_message = request_data.get("alarm_message", "模拟报警")
                return self._trigger_alarm(alarm_code, alarm_message)
            elif command == "clear_alarm":
                return self._clear_alarm()
            elif command == "get_parameters":
                return self._get_parameters()
            elif command == "get_axis_data":
                return self._get_axis_data()
            else:
                return {
                    "success": False,
                    "error": f"未知命令: {command}"
                }
                
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "无效的JSON格式"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"处理请求时出错: {str(e)}"
            }
    
    def _get_status_response(self):
        """获取状态响应"""
        return {
            "success": True,
            "data": {
                "machine_id": self.machine_id,
                "status": self.status.value,
                "program_name": self.program_name,
                "spindle_speed": self.spindle_speed,
                "feed_rate": self.feed_rate,
                "alarm_code": self.alarm_code,
                "alarm_message": self.alarm_message,
                "current_tool": self.current_tool,
                "workpiece_count": self.workpiece_count,
                "spindle_load": self.spindle_load,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    
    def _start_machine(self):
        """启动机床"""
        if self.status == CNCStatus.ALARM:
            return {
                "success": False,
                "error": "机床处于报警状态，无法启动"
            }
        
        self.status = CNCStatus.RUNNING
        self.program_name = f"PROGRAM_{random.randint(100, 999)}"
        self.spindle_speed = random.randint(1000, 6000)
        self.feed_rate = random.randint(50, 500)
        print(f"机床已启动，正在运行程序: {self.program_name}")
        
        return {
            "success": True,
            "message": "机床启动成功",
            "data": {
                "status": self.status.value,
                "program_name": self.program_name
            }
        }
    
    def _stop_machine(self):
        """停止机床"""
        old_status = self.status
        self.status = CNCStatus.STOPPED
        self.program_name = ""
        self.spindle_speed = 0
        self.feed_rate = 0
        print("机床已停止")
        
        return {
            "success": True,
            "message": "机床停止成功",
            "data": {
                "previous_status": old_status.value,
                "current_status": self.status.value
            }
        }
    
    def _pause_machine(self):
        """暂停机床"""
        if self.status == CNCStatus.RUNNING:
            self.status = CNCStatus.PAUSED
            print("机床已暂停")
            return {
                "success": True,
                "message": "机床暂停成功"
            }
        else:
            return {
                "success": False,
                "error": "机床未在运行状态，无法暂停"
            }
    
    def _resume_machine(self):
        """恢复机床"""
        if self.status == CNCStatus.PAUSED:
            self.status = CNCStatus.RUNNING
            print("机床已恢复运行")
            return {
                "success": True,
                "message": "机床恢复成功"
            }
        else:
            return {
                "success": False,
                "error": "机床未在暂停状态，无法恢复"
            }
    
    def _trigger_alarm(self, alarm_code, alarm_message):
        """触发报警"""
        old_status = self.status
        self.status = CNCStatus.ALARM
        self.alarm_code = alarm_code
        self.alarm_message = alarm_message
        self.spindle_speed = 0
        self.feed_rate = 0
        print(f"机床报警: {alarm_code} - {alarm_message}")
        
        return {
            "success": True,
            "message": "报警触发成功",
            "data": {
                "previous_status": old_status.value,
                "current_status": self.status.value,
                "alarm_code": self.alarm_code,
                "alarm_message": self.alarm_message
            }
        }
    
    def _clear_alarm(self):
        """清除报警"""
        if self.status == CNCStatus.ALARM:
            self.status = CNCStatus.IDLE
            old_alarm_code = self.alarm_code
            old_alarm_message = self.alarm_message
            self.alarm_code = 0
            self.alarm_message = ""
            print("机床报警已清除")
            
            return {
                "success": True,
                "message": "报警清除成功",
                "data": {
                    "cleared_alarm_code": old_alarm_code,
                    "cleared_alarm_message": old_alarm_message,
                    "current_status": self.status.value
                }
            }
        else:
            return {
                "success": False,
                "error": "机床未处于报警状态"
            }
    
    def _get_parameters(self):
        """获取机床参数"""
        parameters = {
            "machine_id": self.machine_id,
            "max_spindle_speed": 8000,
            "max_feed_rate": 2000,
            "tool_count": 12,
            "axis_count": 2,
            "system_version": "FANUC 31i-B",
            "controller_type": "OI-MF"
        }
        
        return {
            "success": True,
            "data": parameters
        }
    
    def _get_axis_data(self):
        """获取轴数据"""
        # 模拟轴位置变化（如果机床在运行）
        if self.status == CNCStatus.RUNNING:
            self.axis_positions["X"] += random.uniform(-0.1, 0.1)
            self.axis_positions["Z"] += random.uniform(-0.05, 0.05)
            self.spindle_load = random.randint(30, 80)
        else:
            self.spindle_load = 0
            
        return {
            "success": True,
            "data": {
                "axis_positions": self.axis_positions,
                "spindle_load": self.spindle_load
            }
        }
    
    def _update_status(self):
        """定期更新机床状态"""
        while self.is_running:
            try:
                time.sleep(2)  # 每2秒更新一次
                
                # 随机生成一些状态变化
                if self.status == CNCStatus.RUNNING:
                    # 有小概率完成一个工件
                    if random.random() < 0.05:  # 5%概率
                        self.workpiece_count += 1
                        print(f"完成工件加工，总计: {self.workpiece_count}")
                    
                    # 有很小的概率触发报警
                    if random.random() < 0.005:  # 0.5%概率
                        self._trigger_alarm(
                            random.choice([1001, 1002, 1003, 2001, 2005]),
                            random.choice([
                                "主轴温度过高",
                                "刀具磨损",
                                "润滑不足",
                                "气压异常",
                                "位置超差"
                            ])
                        )
                
                # 定期发送状态更新给所有客户端
                self._broadcast_status()
                
            except Exception as e:
                if self.is_running:
                    print(f"更新状态时出错: {e}")
    
    def _broadcast_status(self):
        """广播状态给所有客户端"""
        with self.client_lock:
            if not self.clients:
                return
                
            status_response = self._get_status_response()
            # 添加标记表明这是广播消息
            status_response["is_broadcast"] = True
            response_str = json.dumps(status_response, ensure_ascii=False) + "\n"
            disconnected_clients = []
            
            for client in self.clients:
                try:
                    client.send(response_str.encode('utf-8'))
                except:
                    disconnected_clients.append(client)
            
            # 移除断开连接的客户端
            for client in disconnected_clients:
                if client in self.clients:
                    self.clients.remove(client)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='FANUC CNC机床模拟器 (FOCAS2协议)')
    parser.add_argument('--host', default='localhost', help='监听主机地址')
    parser.add_argument('--port', type=int, default=8193, help='监听端口号')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("FANUC CNC机床模拟器 (FOCAS2协议)")
    print("=" * 50)
    
    # 创建并启动模拟器
    simulator = FanucCNCSimulator(host=args.host, port=args.port)
    
    try:
        simulator.start_server()
    except KeyboardInterrupt:
        print("\n收到停止信号...")
    except Exception as e:
        print(f"服务器运行异常: {e}")
    finally:
        simulator.stop_server()


if __name__ == "__main__":
    main()