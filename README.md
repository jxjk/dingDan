# 数控车床多订单宏变量管理与生产任务调度系统

## 系统概述

本系统是一个完整的数控车床生产管理系统，实现了多订单管理、宏变量配置、生产任务调度、材料兼容性检查、自动化操作等功能。系统采用模块化设计，支持Web API接口，便于与其他系统集成。

## 系统架构

```
数控车床生产管理系统
├── 配置管理 (config/)
├── 数据模型 (models/)
├── 核心服务 (services/)
├── Web API (api/)
├── 工具类 (utils/)
├── 测试用例 (tests/)
└── 启动脚本 (run_system.py)
```

## 主要功能

### 1. 任务管理
- 多订单任务创建和管理
- 任务状态跟踪（待处理、运行中、已完成、失败）
- 任务优先级设置
- 任务暂停、恢复、取消

### 2. 材料管理
- 材料规格映射管理
- 材料兼容性检查
- 材料库存跟踪
- 材料更换成本计算

### 3. 任务调度
- 多种调度策略（材料优先、优先级优先、负载均衡、效率优先）
- 实时任务分配
- 机床状态监控
- 自动重试机制

### 4. 自动化操作
- DNC系统自动化控制
- 浏览器系统自动化
- 二维码扫描与解析
- 文件监控与处理

### 5. 监控与日志
- 系统状态监控
- 详细的操作日志
- 性能监控
- 审计日志

## 快速开始

### 环境要求

- Python 3.8+
- Windows 10/11（支持Windows自动化）
- 推荐使用虚拟环境

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行系统

1. **设置环境**
```bash
python run_system.py setup
```

2. **运行生产系统**
```bash
python run_system.py production
```

3. **运行Web API服务器**
```bash
python run_system.py api
```

4. **同时运行生产系统和API**
```bash
python run_system.py both
```

5. **运行系统测试**
```bash
python run_system.py test
```

### 使用Web API

系统启动后，可以通过以下API接口进行管理：

- **健康检查**: `GET http://localhost:5000/api/health`
- **系统状态**: `GET http://localhost:5000/api/system/status`
- **任务管理**: `GET/POST http://localhost:5000/api/tasks`
- **机床管理**: `GET http://localhost:5000/api/machines`
- **材料管理**: `GET http://localhost:5000/api/materials/stock`
- **调度管理**: `GET/POST http://localhost:5000/api/scheduling/strategy`

## 配置说明

### 主要配置文件

- `config.yaml` - 系统主配置文件
- `config/material_mapping.csv` - 材料映射配置

### 配置示例

```yaml
system:
  name: "数控车床生产管理系统"
  version: "1.0.0"
  debug: true

logging:
  level: "INFO"
  file_path: "logs/system.log"
  max_size_mb: 10
  backup_count: 5

file_monitoring:
  onoff_file: "monitoring/onoff.txt"
  macro_file: "monitoring/macro.txt"
  poll_interval: 1.0

scheduling:
  strategy: "material_first"
  check_interval: 10
  max_retries: 3
```

## 核心模块说明

### 1. 配置管理 (config/config_manager.py)
- 统一的配置加载和管理
- 配置验证和默认值设置
- 动态配置更新

### 2. 生产任务模型 (models/production_task.py)
- 任务状态管理
- 优先级处理
- 任务数据序列化

### 3. 材料检查器 (services/material_checker.py)
- 材料兼容性验证
- 材料组映射管理
- 更换成本计算

### 4. 任务调度器 (services/task_scheduler.py)
- 多策略调度算法
- 机床状态管理
- 任务分配优化

### 5. 文件监控器 (services/file_monitor.py)
- 实时文件变化检测
- 宏变量文件处理
- 开关状态监控

### 6. UI自动化 (services/ui_automation.py)
- DNC系统自动化控制
- 浏览器自动化操作
- 二维码扫描处理

### 7. Web API (api/web_api.py)
- RESTful API接口
- 跨域支持
- 完整的系统管理接口

## 开发指南

### 添加新的调度策略

1. 在 `services/task_scheduler.py` 中添加新的策略方法
2. 在 `_schedule_material_first` 等方法后添加新方法
3. 更新 `schedule_tasks` 方法以支持新策略
4. 在配置文件中添加策略选项

### 扩展材料兼容性检查

1. 更新 `config/material_mapping.csv` 文件
2. 在 `services/material_checker.py` 中添加新的检查逻辑
3. 更新材料组映射关系

### 添加新的自动化系统

1. 在 `services/ui_automation.py` 中添加新的自动化类
2. 实现相应的自动化方法
3. 在配置文件中添加系统配置

## 测试

系统包含完整的单元测试和集成测试：

```bash
# 运行所有测试
python tests/test_system.py

# 运行特定测试类
python -m unittest tests.test_system.TestConfigManager

# 使用unittest运行测试
python -m unittest discover tests/
```

## 故障排除

### 常见问题

1. **依赖安装失败**
   - 确保使用Python 3.8+
   - 尝试使用管理员权限安装
   - 检查网络连接

2. **系统启动失败**
   - 检查配置文件格式
   - 验证必要的目录权限
   - 查看日志文件获取详细信息

3. **自动化操作失败**
   - 确保目标应用程序已启动
   - 检查UI元素定位配置
   - 验证窗口标题和类名

4. **API接口无法访问**
   - 检查端口是否被占用
   - 验证防火墙设置
   - 确认系统是否正在运行

### 日志文件

系统日志位于 `logs/system.log`，包含详细的运行信息、错误信息和调试信息。

## 部署说明

### 生产环境部署

1. 设置 `debug: false` 在配置文件中
2. 配置适当的日志级别
3. 设置系统服务或计划任务
4. 配置监控和告警

### 性能优化

- 调整文件监控轮询间隔
- 优化调度策略参数
- 配置适当的线程池大小
- 启用数据库持久化（可选）

## 许可证

本项目采用MIT许可证。

## 技术支持

如有问题或建议，请提交Issue或联系开发团队。

---

**版本**: 1.0.0  
**最后更新**: 2025-10-20  
**开发团队**: 数控车床生产管理系统开发组
