"""
FOCAS2客户端测试程序
用于测试FANUC CNC模拟器的功能
"""

import socket
import json
import time
import threading


class FOCAS2Client:
    """FOCAS2客户端"""
    
    def __init__(self, host='localhost', port=8193):
        self.host = host
        self.port = port
        self.socket = None
        self.is_connected = False
        self.response_received = None
        self.response_event = threading.Event()
        
    def connect(self):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            print(f"成功连接到 {self.host}:{self.port}")
            
            # 启动接收线程
            receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            receive_thread.start()
            
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
            self.is_connected = False
            print("连接已断开")
    
    def _receive_loop(self):
        """接收服务器消息的循环"""
        buffer = ""
        while self.is_connected:
            try:
                data = self.socket.recv(4096)
                if not data:
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
                                # 这是广播消息，可以选择处理或忽略
                                print(f"收到广播消息: {response.get('data', {}).get('status', 'N/A')}")
                            else:
                                # 这是请求响应，设置响应事件
                                self.response_received = response
                                self.response_event.set()
                        except json.JSONDecodeError:
                            print(f"JSON解析失败: {line}")
                            
            except Exception as e:
                if self.is_connected:
                    print(f"接收数据时出错: {e}")
                break
    
    def send_command(self, command, **kwargs):
        """发送命令"""
        if not self.is_connected:
            print("未连接到服务器")
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


def test_cnc_operations():
    """测试CNC操作"""
    client = FOCAS2Client()
    
    if not client.connect():
        return
    
    try:
        # 获取初始状态
        print("\n1. 获取初始状态:")
        response = client.send_command("get_status")
        if response and response.get("success"):
            status_data = response["data"]
            print(f"   机床ID: {status_data['machine_id']}")
            print(f"   状态: {status_data['status']}")
        else:
            error_msg = response.get('error', '未知错误') if response else '无响应'
            print(f"   获取状态失败: {error_msg}")
        
        # 启动机床
        print("\n2. 启动机床:")
        response = client.send_command("start_machine")
        if response and response.get("success"):
            print(f"   启动成功: {response['message']}")
        else:
            error_msg = response.get('error', '未知错误') if response else '无响应'
            print(f"   启动失败: {error_msg}")
        
        # 获取运行状态
        print("\n3. 获取运行状态:")
        response = client.send_command("get_status")
        if response and response.get("success"):
            status_data = response["data"]
            print(f"   状态: {status_data['status']}")
            print(f"   当前程序: {status_data['program_name']}")
            print(f"   主轴转速: {status_data['spindle_speed']} RPM")
            print(f"   进给速度: {status_data['feed_rate']} mm/min")
        else:
            error_msg = response.get('error', '未知错误') if response else '无响应'
            print(f"   获取状态失败: {error_msg}")
        
        # 等待一段时间观察运行
        print("\n4. 观察运行状态 (5秒)...")
        time.sleep(5)
        
        # 暂停机床
        print("\n5. 暂停机床:")
        response = client.send_command("pause_machine")
        if response:
            if response.get("success"):
                print(f"   暂停成功: {response['message']}")
            else:
                print(f"   暂停失败: {response.get('error', '未知错误')}")
        else:
            print("   暂停失败: 无响应")
        
        # 获取暂停状态
        print("\n6. 获取暂停状态:")
        response = client.send_command("get_status")
        if response and response.get("success"):
            status_data = response["data"]
            print(f"   状态: {status_data['status']}")
        else:
            error_msg = response.get('error', '未知错误') if response else '无响应'
            print(f"   获取状态失败: {error_msg}")
        
        # 恢复机床
        print("\n7. 恢复机床:")
        response = client.send_command("resume_machine")
        if response:
            if response.get("success"):
                print(f"   恢复成功: {response['message']}")
            else:
                print(f"   恢复失败: {response.get('error', '未知错误')}")
        else:
            print("   恢复失败: 无响应")
        
        # 等待一段时间观察运行
        print("\n8. 观察运行状态 (3秒)...")
        time.sleep(3)
        
        # 触发报警
        print("\n9. 触发报警:")
        response = client.send_command(
            "trigger_alarm", 
            alarm_code=1001, 
            alarm_message="模拟报警测试"
        )
        if response:
            if response.get("success"):
                print(f"   报警触发成功: {response['message']}")
            else:
                print(f"   报警触发失败: {response.get('error', '未知错误')}")
        else:
            print("   报警触发失败: 无响应")
        
        # 获取报警状态
        print("\n10. 获取报警状态:")
        response = client.send_command("get_status")
        if response and response.get("success"):
            status_data = response["data"]
            print(f"   状态: {status_data['status']}")
            print(f"   报警代码: {status_data['alarm_code']}")
            print(f"   报警信息: {status_data['alarm_message']}")
        else:
            error_msg = response.get('error', '未知错误') if response else '无响应'
            print(f"   获取状态失败: {error_msg}")
        
        # 清除报警
        print("\n11. 清除报警:")
        response = client.send_command("clear_alarm")
        if response:
            if response.get("success"):
                print(f"   报警清除成功: {response['message']}")
            else:
                print(f"   报警清除失败: {response.get('error', '未知错误')}")
        else:
            print("   报警清除失败: 无响应")
        
        # 停止机床
        print("\n12. 停止机床:")
        response = client.send_command("stop_machine")
        if response:
            if response.get("success"):
                print(f"   停止成功: {response['message']}")
            else:
                print(f"   停止失败: {response.get('error', '未知错误')}")
        else:
            print("   停止失败: 无响应")
        
        # 获取最终状态
        print("\n13. 获取最终状态:")
        response = client.send_command("get_status")
        if response and response.get("success"):
            status_data = response["data"]
            print(f"   状态: {status_data['status']}")
            print(f"   完成工件数: {status_data['workpiece_count']}")
        else:
            error_msg = response.get('error', '未知错误') if response else '无响应'
            print(f"   获取状态失败: {error_msg}")
        
        # 获取机床参数
        print("\n14. 获取机床参数:")
        response = client.send_command("get_parameters")
        if response and response.get("success"):
            params = response["data"]
            print(f"   系统版本: {params['system_version']}")
            print(f"   控制器类型: {params['controller_type']}")
            print(f"   最大主轴转速: {params['max_spindle_speed']} RPM")
        else:
            error_msg = response.get('error', '未知错误') if response else '无响应'
            print(f"   获取参数失败: {error_msg}")
        
        # 获取轴数据
        print("\n15. 获取轴数据:")
        response = client.send_command("get_axis_data")
        if response and response.get("success"):
            axis_data = response["data"]
            print(f"   轴位置: {axis_data['axis_positions']}")
            print(f"   主轴负载: {axis_data['spindle_load']}%")
        else:
            error_msg = response.get('error', '未知错误') if response else '无响应'
            print(f"   获取轴数据失败: {error_msg}")
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        client.disconnect()


def main():
    """主函数"""
    print("=" * 50)
    print("FOCAS2客户端测试程序")
    print("=" * 50)
    print("请确保先运行 simulate_fanuc_cnc.py")
    print()
    
    choice = input("是否开始测试? (y/n): ").strip().lower()
    if choice == 'y' or choice == 'yes':
        test_cnc_operations()
    else:
        print("测试已取消")


if __name__ == "__main__":
    main()