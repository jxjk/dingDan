# FANUC CNC 机床模拟器使用说明

## 概述

本模拟器用于模拟 FANUC CNC 机床的行为，通过 TCP/IP 协议实现类似 FOCAS2 的通信功能。该模拟器可以模拟机床的运行、停止、报警等状态，用于测试和开发 CNC 相关的应用程序。

## 文件说明

- `simulate_fanuc_cnc.py` - FANUC CNC 机床模拟器主程序（服务器端）
- `test_focas2_client.py` - FOCAS2 客户端测试程序
- `cnc_machine_connector.py` - 与订单管理下发DNC系统集成的机床连接器
- `cnc_machine_ui.py` - CNC机床图形化控制界面

## 安装和运行

### 运行环境

- Python 3.6 或更高版本
- 无需额外依赖库（仅使用Python标准库）
- 如果要使用UI界面，需要安装PyQt6: `pip install PyQt6`

### 启动模拟器

```bash
python simulate_fanuc_cnc.py
```

默认情况下，模拟器将在 `localhost:8193` 上监听客户端连接。

### 运行测试客户端

在另一个终端中运行：

```bash
python test_focas2_client.py
```

### 运行交互式控制界面

在另一个终端中运行：

```bash
python cnc_machine_connector.py
```

### 运行图形化控制界面

在另一个终端中运行：

```bash
python cnc_machine_ui.py
```

## 模拟器功能

### 支持的机床状态

1. **OFF** - 关机状态
2. **IDLE** - 空闲状态
3. **RUNNING** - 运行状态
4. **ALARM** - 报警状态
5. **STOPPED** - 停止状态
6. **PAUSED** - 暂停状态

### 支持的操作命令

1. `get_status` - 获取机床当前状态
2. `start_machine` - 启动机床
3. `stop_machine` - 停止机床
4. `pause_machine` - 暂停机床
5. `resume_machine` - 恢复机床
6. `trigger_alarm` - 触发报警
7. `clear_alarm` - 清除报警
8. `get_parameters` - 获取机床参数
9. `get_axis_data` - 获取轴数据

### 自动行为

1. 机床在运行状态下会随机完成工件加工
2. 机床在运行状态下有小概率触发报警
3. 机床状态会定期广播给所有连接的客户端

## 使用示例

### 启动机床

客户端发送命令：
```json
{
  "command": "start_machine"
}
```

### 获取状态

客户端发送命令：
```json
{
  "command": "get_status"
}
```

服务器响应：
```json
{
  "success": true,
  "data": {
    "machine_id": "FANUC-CNC-1234",
    "status": "RUNNING",
    "program_name": "PROGRAM_567",
    "spindle_speed": 3200,
    "feed_rate": 250,
    "alarm_code": 0,
    "alarm_message": "",
    "current_tool": 1,
    "workpiece_count": 5,
    "spindle_load": 45,
    "timestamp": "2023-10-20 14:30:25"
  }
}
```

### 触发报警

客户端发送命令：
```json
{
  "command": "trigger_alarm",
  "alarm_code": 1001,
  "alarm_message": "主轴温度过高"
}
```

## API 说明

### 通用响应格式

所有响应都遵循以下格式：

成功响应：
```json
{
  "success": true,
  "message": "操作描述",
  "data": { /* 具体数据 */ }
}
```

错误响应：
```json
{
  "success": false,
  "error": "错误描述"
}
```

### 命令详情

#### get_status - 获取状态
无需参数，返回机床当前详细状态。

#### start_machine - 启动机床
无需参数，将机床状态从 IDLE 设置为 RUNNING。

#### stop_machine - 停止机床
无需参数，将机床状态设置为 STOPPED。

#### pause_machine - 暂停机床
无需参数，将机床状态从 RUNNING 设置为 PAUSED。

#### resume_machine - 恢复机床
无需参数，将机床状态从 PAUSED 设置为 RUNNING。

#### trigger_alarm - 触发报警
参数：
- `alarm_code` (整数) - 报警代码
- `alarm_message` (字符串) - 报警信息

#### clear_alarm - 清除报警
无需参数，清除当前报警状态，机床状态变为 IDLE。

#### get_parameters - 获取参数
无需参数，返回机床参数信息。

#### get_axis_data - 获取轴数据
无需参数，返回轴位置和负载信息。

## 开发集成

您可以基于此模拟器开发自己的客户端程序，连接到模拟器并发送命令来控制和监控虚拟机床。

### Python 客户端示例

```python
import socket
import json

# 连接到模拟器
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 8193))

# 发送获取状态命令
request = {"command": "get_status"}
sock.send(json.dumps(request).encode('utf-8'))

# 接收响应
response = json.loads(sock.recv(4096).decode('utf-8'))
print(response)

# 关闭连接
sock.close()
```

## 与订单管理下发DNC系统集成

### 集成方式

订单管理下发DNC系统可以通过 [cnc_machine_connector.py](file:///D:/Users/00596/Desktop/%E8%AE%A2%E5%8D%95%E7%AE%A1%E7%90%86%E4%B8%8B%E5%8F%91DNC/cnc_machine_connector.py) 中提供的 [CNCMachineManager](file:///D:/Users/00596/Desktop/%E8%AE%A2%E5%8D%95%E7%AE%A1%E7%90%86%E4%B8%8B%E5%8F%91DNC/cnc_machine_connector.py#L111-L189) 类与模拟的CNC机床进行通信。

### 使用方法

1. 启动FANUC CNC模拟器：
   ```bash
   python simulate_fanuc_cnc.py
   ```

2. 在订单管理下发DNC系统中集成机床连接功能：
   ```python
   from cnc_machine_connector import CNCMachineManager
   
   # 创建机床管理器实例
   machine_manager = CNCMachineManager()
   
   # 连接到模拟机床 (默认地址 127.0.0.1:8193)
   if machine_manager.connect_machine('127.0.0.1', 8193):
       # 获取机床状态
       status = machine_manager.get_machine_status()
       
       # 启动机床
       machine_manager.start_machine()
       
       # 暂停机床
       machine_manager.pause_machine()
       
       # 恢复机床
       machine_manager.resume_machine()
       
       # 停止机床
       machine_manager.stop_machine()
   ```

### 在订单管理下发DNC系统中使用交互式控制

用户可以直接运行交互式控制程序来手动控制模拟机床：

```bash
python cnc_machine_connector.py
```

这将启动一个命令行界面，允许用户手动发送各种命令来控制机床。

### 使用图形化控制界面

用户可以运行图形化界面程序来通过直观的UI控制机床：

```bash
python cnc_machine_ui.py
```

图形化界面提供了以下功能：
1. 连接/断开机床连接
2. 实时显示机床状态信息
3. 图形化按钮控制机床启停、暂停、恢复
4. 报警触发和清除功能
5. 参数查询功能
6. 操作日志显示

## 注意事项

1. 模拟器默认监听端口为 8193，可根据需要修改
2. 模拟器支持多个客户端同时连接
3. 模拟器会定期向所有客户端广播状态更新
4. 在报警状态下无法启动机床
5. 只有在运行状态下才能暂停机床
6. 只有在暂停状态下才能恢复机床

## 故障排除

### 常见问题

1. **JSON解析错误**：
   - 错误信息：`Extra data: line 1 column ...`
   - 原因：服务器可能同时发送多条消息或广播状态更新
   - 解决方法：客户端需要正确处理缓冲区和多条消息的解析

2. **连接被拒绝**：
   - 错误信息：`ConnectionRefusedError`
   - 原因：模拟器未启动或端口不正确
   - 解决方法：确保模拟器正在运行并监听正确的端口

3. **无响应**：
   - 现象：客户端发送命令后没有收到响应
   - 原因：网络问题或服务器异常
   - 解决方法：检查网络连接，重启模拟器和客户端

### 调试建议

1. 查看模拟器控制台输出，了解服务器端的运行状态
2. 使用网络调试工具（如Wireshark）检查网络通信
3. 在客户端添加详细的日志记录，跟踪请求和响应过程

## 扩展建议

如需扩展模拟器功能，可以考虑添加：

1. 更多的机床参数和状态
2. NC程序模拟执行
3. 更复杂的报警类型和处理逻辑
4. 数据持久化功能
5. 更真实的轴运动模拟
6. 与实际生产管理系统的集成