# CNC机床连接与使用说明

## 概述

本文档详细说明如何在订单管理下发DNC系统中连接和使用模拟的FANUC CNC机床。通过集成的CNC机床连接功能，系统可以与通过TCP/IP协议通信的CNC机床进行交互，实现任务下发、状态监控等功能。

## 系统架构

订单管理下发DNC系统支持两种方式与CNC机床通信：
1. 通过文件监控（原有的onoff.txt和macro.txt文件方式）
2. 通过TCP/IP直接连接模拟CNC机床

## 启动和配置

### 1. 启动CNC机床模拟器

首先需要启动FANUC CNC机床模拟器：

```bash
python simulate_fanuc_cnc.py
```

默认情况下，模拟器将在 `127.0.0.1:8193` 上监听连接。

### 2. 启动订单管理下发DNC系统

启动主系统：

```bash
python run_system.py production
```

或者直接运行：

```bash
python main.py
```

## CNC机床连接配置

### 在系统中连接机床

系统启动后，可以通过以下方式连接CNC机床：

```python
from main import EnhancedCNCProductionSystem

# 创建系统实例
system = EnhancedCNCProductionSystem()

# 连接到CNC机床
# 参数: 机床ID, 主机地址, 端口号
success = system.connect_cnc_machine("MACHINE_001", "127.0.0.1", 8193)

if success:
    print("机床连接成功")
else:
    print("机床连接失败")
```

### 通过配置文件连接

在系统配置文件 `config/config.yaml` 中添加CNC机床配置：

```yaml
cnc_machines:
  - id: "MACHINE_001"
    host: "127.0.0.1"
    port: 8193
    enabled: true
  - id: "MACHINE_002"
    host: "127.0.0.1"
    port: 8194
    enabled: false
```

## CNC机床操作

连接成功后，可以对CNC机床执行以下操作：

### 1. 获取机床状态

```python
# 获取机床状态
status = system.get_cnc_machine_status("MACHINE_001")
if status.get("success"):
    data = status["data"]
    print(f"机床状态: {data['status']}")
    print(f"当前程序: {data['program_name']}")
    print(f"主轴转速: {data['spindle_speed']} RPM")
```

### 2. 控制机床运行

```python
# 启动机床
result = system.control_cnc_machine("MACHINE_001", "start")
if result.get("success"):
    print("机床启动成功")

# 暂停机床
result = system.control_cnc_machine("MACHINE_001", "pause")
if result.get("success"):
    print("机床暂停成功")

# 恢复机床
result = system.control_cnc_machine("MACHINE_001", "resume")
if result.get("success"):
    print("机床恢复成功")

# 停止机床
result = system.control_cnc_machine("MACHINE_001", "stop")
if result.get("success"):
    print("机床停止成功")
```

### 3. 报警处理

```python
# 触发报警
result = system.control_cnc_machine(
    "MACHINE_001", 
    "trigger_alarm",
    alarm_code=1001,
    alarm_message="主轴温度过高"
)
if result.get("success"):
    print("报警触发成功")

# 清除报警
result = system.control_cnc_machine("MACHINE_001", "clear_alarm")
if result.get("success"):
    print("报警清除成功")
```

## 任务调度与机床集成

系统会自动将连接的CNC机床纳入任务调度范围。当机床状态变为可用（IDLE、OFF、STANDBY、READY）时，系统会自动为机床分配合适的任务。

### 手动更新机床状态

```python
# 手动更新机床状态到任务调度器
system.update_cnc_machine_state("MACHINE_001")
```

## 使用交互式控制程序

系统提供了交互式CNC机床控制程序，用户可以直接通过命令行界面控制机床：

```bash
python cnc_machine_connector.py
```

该程序提供以下功能：
- 实时显示机床状态更新
- 手动控制机床启停、暂停、恢复
- 触发和清除报警
- 查看机床参数和轴数据

## 使用图形化控制界面

为了提供更好的用户体验，系统还提供了图形化的CNC机床控制界面：

```bash
python cnc_machine_ui.py
```

图形化界面包含以下功能模块：

### 1. 连接控制面板
- 配置机床连接参数（主机地址、端口、机床ID）
- 连接/断开机床按钮
- 连接状态指示

### 2. 状态监控面板
- 实时显示机床基本信息（ID、状态、程序名等）
- 显示运行参数（主轴转速、进给速度、负载等）
- 报警信息显示（带颜色标识）

### 3. 控制操作面板
- 机床基本控制按钮（启动、停止、暂停、恢复）
- 报警控制（触发、清除）
- 参数查询（机床参数、轴数据）

### 4. 操作日志面板
- 显示所有操作日志和系统消息
- 支持日志清空和自动滚动

图形化界面具有以下优势：
- 直观的状态显示，通过颜色区分不同状态
- 一键式操作按钮，简化控制流程
- 实时日志显示，便于监控操作结果
- 响应式布局，适应不同屏幕尺寸

## API接口

如果启用了Web API服务，可以通过HTTP接口控制CNC机床：

### 获取机床状态
```
GET /api/machines/{machine_id}/status
```

### 控制机床
```
POST /api/machines/{machine_id}/control
Content-Type: application/json

{
  "operation": "start"  // 或 "stop", "pause", "resume", "trigger_alarm", "clear_alarm"
}
```

## 故障排除

### 常见问题

1. **连接失败**
   - 确保CNC机床模拟器正在运行
   - 检查主机地址和端口号是否正确
   - 确认防火墙未阻止连接

2. **操作无响应**
   - 检查机床当前状态是否允许该操作
   - 查看系统日志获取详细错误信息

3. **状态更新不及时**
   - 检查网络连接是否稳定
   - 确认机床模拟器是否正常运行

### 日志查看

系统日志保存在 `logs/` 目录下，可以查看详细的操作记录和错误信息。

## 最佳实践

1. **连接管理**
   - 系统启动时自动连接配置文件中启用的机床
   - 定期检查机床连接状态
   - 系统关闭时自动断开所有机床连接

2. **状态同步**
   - 定期更新机床状态到任务调度器
   - 根据机床状态调整任务分配策略

3. **错误处理**
   - 对所有机床操作进行异常处理
   - 记录详细的操作日志便于问题排查

## 扩展开发

开发者可以根据需要扩展CNC机床功能：

1. 添加新的机床控制命令
2. 实现更复杂的机床状态处理逻辑
3. 集成真实的FANUC CNC机床
4. 添加机床数据持久化功能

通过以上步骤，您可以在订单管理下发DNC系统中成功连接和使用模拟的CNC机床，实现更完整的生产管理系统功能。