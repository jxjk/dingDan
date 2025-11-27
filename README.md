# 数控车床生产管理系统

订单管理助手 - 基于二维码的任务分发和机床控制系统

## 项目结构

```
订单管理下发DNC/
├── docs/                 # 文档目录
│   ├── 1.md             # 系统功能细化
│   ├── 1.puml           # 系统功能图
│   ├── *.docx           # 各种规格说明书
│   └── 用户使用说明书.md  # 用户操作手册
├── src/                  # 源代码目录
│   ├── api/             # API接口模块
│   ├── config/          # 配置管理模块
│   ├── models/          # 数据模型
│   ├── services/        # 业务服务模块
│   ├── ui/              # 用户界面模块
│   ├── utils/           # 工具函数
│   ├── tests/           # 测试代码
│   ├── main.py          # 主程序入口
│   ├── config.yaml      # 系统配置文件
│   ├── requirements.txt # 依赖包列表
│   └── *.json           # 配置文件
├── logs/                # 日志文件
├── data/                # 数据文件
├── backup/              # 备份文件
├── monitoring/          # 监控数据
└── README.md            # 项目说明
```

## 系统功能

- 二维码任务输入：扫描二维码输入任务信息
- 任务调度管理：根据机床状态和材料兼容性自动分配任务
- 机床状态监控：通过onoff.txt文件实时监控机床状态
- UI自动化控制：模拟键盘/鼠标操作与DNC软件交互
- 材料管理：检查材料兼容性，提供库存管理

## 环境要求

- Windows 7/8/10/11
- Python 3.8+
- .NET Framework 4.8（如需要）

## 快速开始

1. 安装依赖：
   ```bash
   cd src
   pip install -r requirements.txt
   ```

2. 配置系统：
   - 编辑`src/config.yaml`文件配置机床参数
   - 设置onoff.txt和macro.txt文件路径
   - 配置DNC系统窗口和控件参数

3. 启动系统：
   ```bash
   cd src
   python main.py
   ```

## 使用说明

详细使用说明请参考：`docs/用户使用说明书.md`

## 配置说明

### 主要配置文件

- `src/config.yaml`: 系统主配置文件
- `src/config/material_mapping.csv`: 材料映射表
- `C:/macro/onoff.txt`: 机床状态文件
- `C:/macro/macro.txt`: 宏变量输出文件

### 机床配置示例

```yaml
machines:
  CNC-01:
    material: "S45C"
    capabilities: ["turning", "facing"]
    ip_address: "127.0.0.1"
    port: 8193
```

## 文件监控

系统通过监控以下文件实现机床状态感知：
- `onoff.txt`: 机床运行状态（0=空闲，1=运行）
- `macro.txt`: 宏变量输出，用于任务下发

## 维护说明

- 定期备份配置文件和任务数据
- 监控日志文件以排查问题
- 检查材料库存，及时更新材料映射表

## 技术支持

如需技术支持，请联系系统管理员。