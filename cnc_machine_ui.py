"""
CNC机床控制UI界面
提供图形化界面用于连接和控制CNC机床
"""

import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QTextEdit, QGroupBox, 
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QTabWidget, QFormLayout, QSpinBox, QCheckBox,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QTextCursor

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from cnc_machine_connector import CNCMachineManager
    CNC_CONNECTOR_AVAILABLE = True
except ImportError:
    CNC_CONNECTOR_AVAILABLE = False
    print("警告: CNC机床连接器不可用")


class CNCMachineController(QObject):
    """CNC机床控制器"""
    status_updated = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.machine_manager = None
        self.is_connected = False
        self.host = "127.0.0.1"
        self.port = 8193
        self.machine_id = "MACHINE_001"
        
    def connect_machine(self, host: str, port: int, machine_id: str) -> bool:
        """连接到机床"""
        if not CNC_CONNECTOR_AVAILABLE:
            self.log_message.emit("错误: CNC机床连接器不可用")
            return False
            
        try:
            self.host = host
            self.port = port
            self.machine_id = machine_id
            
            self.machine_manager = CNCMachineManager()
            if self.machine_manager.connect_machine(host, port):
                self.is_connected = True
                self.connection_changed.emit(True)
                self.log_message.emit(f"成功连接到机床 {machine_id} ({host}:{port})")
                return True
            else:
                self.log_message.emit(f"连接机床失败: {machine_id}")
                return False
                
        except Exception as e:
            self.log_message.emit(f"连接机床时出错: {str(e)}")
            return False
    
    def disconnect_machine(self):
        """断开机床连接"""
        if self.machine_manager and self.is_connected:
            try:
                self.machine_manager.disconnect_machine()
                self.is_connected = False
                self.connection_changed.emit(False)
                self.log_message.emit("已断开机床连接")
            except Exception as e:
                self.log_message.emit(f"断开连接时出错: {str(e)}")
    
    def get_status(self) -> Optional[Dict[Any, Any]]:
        """获取机床状态"""
        if not self.is_connected or not self.machine_manager:
            self.log_message.emit("未连接到机床")
            return None
            
        try:
            status = self.machine_manager.get_machine_status(self.host, self.port)
            if status and status.get("success"):
                self.status_updated.emit(status["data"])
                return status["data"]
            else:
                error_msg = status.get("error", "未知错误") if status else "无响应"
                self.log_message.emit(f"获取状态失败: {error_msg}")
                return None
        except Exception as e:
            self.log_message.emit(f"获取状态时出错: {str(e)}")
            return None
    
    def control_machine(self, operation: str, **kwargs) -> bool:
        """控制机床"""
        if not self.is_connected or not self.machine_manager:
            self.log_message.emit("机床未连接")
            return False
            
        try:
            result = self.machine_manager.control_cnc_machine(
                self.machine_id, operation, **kwargs
            )
            
            if result and result.get("success"):
                self.log_message.emit(f"{operation.upper()} 操作成功: {result.get('message', '')}")
                return True
            else:
                error_msg = result.get("error", "未知错误") if result else "无响应"
                self.log_message.emit(f"{operation.upper()} 操作失败: {error_msg}")
                return False
                
        except Exception as e:
            self.log_message.emit(f"控制机床时出错: {str(e)}")
            return False


class CNCMachineUI(QMainWindow):
    """CNC机床控制主界面"""
    
    def __init__(self):
        super().__init__()
        self.controller = CNCMachineController()
        self.init_ui()
        self.setup_connections()
        self.setup_timers()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("CNC机床控制面板")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建连接控制标签页
        self.create_connection_tab()
        
        # 创建状态监控标签页
        self.create_status_tab()
        
        # 创建控制操作标签页
        self.create_control_tab()
        
        # 创建日志标签页
        self.create_log_tab()
        
        # 创建状态栏
        self.status_bar = self.statusBar()
        self.connection_label = QLabel("未连接")
        self.status_bar.addPermanentWidget(self.connection_label)
        
    def create_connection_tab(self):
        """创建连接控制标签页"""
        connection_tab = QWidget()
        layout = QVBoxLayout(connection_tab)
        
        # 连接设置组
        connection_group = QGroupBox("连接设置")
        connection_layout = QFormLayout(connection_group)
        
        self.host_input = QLineEdit("127.0.0.1")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(8193)
        self.machine_id_input = QLineEdit("MACHINE_001")
        
        connection_layout.addRow("主机地址:", self.host_input)
        connection_layout.addRow("端口:", self.port_input)
        connection_layout.addRow("机床ID:", self.machine_id_input)
        
        # 连接按钮
        button_layout = QHBoxLayout()
        self.connect_button = QPushButton("连接机床")
        self.disconnect_button = QPushButton("断开连接")
        self.disconnect_button.setEnabled(False)
        
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)
        button_layout.addStretch()
        
        layout.addWidget(connection_group)
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.tab_widget.addTab(connection_tab, "连接控制")
        
    def create_status_tab(self):
        """创建状态监控标签页"""
        status_tab = QWidget()
        layout = QVBoxLayout(status_tab)
        
        # 机床基本信息
        info_group = QGroupBox("机床基本信息")
        info_layout = QFormLayout(info_group)
        
        self.machine_id_label = QLabel("-")
        self.status_label = QLabel("-")
        self.program_label = QLabel("-")
        self.timestamp_label = QLabel("-")
        
        # 设置状态标签的样式
        self.status_label.setStyleSheet("font-weight: bold;")
        
        info_layout.addRow("机床ID:", self.machine_id_label)
        info_layout.addRow("状态:", self.status_label)
        info_layout.addRow("当前程序:", self.program_label)
        info_layout.addRow("更新时间:", self.timestamp_label)
        
        # 运行参数
        params_group = QGroupBox("运行参数")
        params_layout = QFormLayout(params_group)
        
        self.spindle_speed_label = QLabel("-")
        self.feed_rate_label = QLabel("-")
        self.spindle_load_label = QLabel("-")
        self.workpiece_count_label = QLabel("-")
        
        params_layout.addRow("主轴转速:", self.spindle_speed_label)
        params_layout.addRow("进给速度:", self.feed_rate_label)
        params_layout.addRow("主轴负载:", self.spindle_load_label)
        params_layout.addRow("完成工件数:", self.workpiece_count_label)
        
        # 报警信息
        alarm_group = QGroupBox("报警信息")
        alarm_layout = QVBoxLayout(alarm_group)
        
        self.alarm_code_label = QLabel("报警代码: -")
        self.alarm_message_label = QLabel("报警信息: -")
        self.alarm_message_label.setWordWrap(True)
        
        alarm_layout.addWidget(self.alarm_code_label)
        alarm_layout.addWidget(self.alarm_message_label)
        
        layout.addWidget(info_group)
        layout.addWidget(params_group)
        layout.addWidget(alarm_group)
        layout.addStretch()
        
        self.tab_widget.addTab(status_tab, "状态监控")
        
    def create_control_tab(self):
        """创建控制操作标签页"""
        control_tab = QWidget()
        layout = QVBoxLayout(control_tab)
        
        # 基本控制按钮
        basic_control_group = QGroupBox("基本控制")
        basic_control_layout = QHBoxLayout(basic_control_group)
        
        self.start_button = QPushButton("启动")
        self.stop_button = QPushButton("停止")
        self.pause_button = QPushButton("暂停")
        self.resume_button = QPushButton("恢复")
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                font-size: 14px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:enabled {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        
        self.start_button.setStyleSheet(button_style)
        self.stop_button.setStyleSheet(button_style.replace("#4CAF50", "#f44336"))
        self.pause_button.setStyleSheet(button_style.replace("#4CAF50", "#ff9800"))
        self.resume_button.setStyleSheet(button_style.replace("#4CAF50", "#2196F3"))
        
        basic_control_layout.addWidget(self.start_button)
        basic_control_layout.addWidget(self.stop_button)
        basic_control_layout.addWidget(self.pause_button)
        basic_control_layout.addWidget(self.resume_button)
        basic_control_layout.addStretch()
        
        # 报警控制
        alarm_control_group = QGroupBox("报警控制")
        alarm_control_layout = QHBoxLayout(alarm_control_group)
        
        self.trigger_alarm_button = QPushButton("触发报警")
        self.clear_alarm_button = QPushButton("清除报警")
        
        self.trigger_alarm_button.setStyleSheet(button_style.replace("#4CAF50", "#f44336"))
        self.clear_alarm_button.setStyleSheet(button_style.replace("#4CAF50", "#2196F3"))
        
        # 报警设置
        alarm_settings_layout = QHBoxLayout()
        self.alarm_code_input = QSpinBox()
        self.alarm_code_input.setRange(1, 9999)
        self.alarm_code_input.setValue(1001)
        self.alarm_message_input = QLineEdit("模拟报警")
        
        alarm_settings_layout.addWidget(QLabel("报警代码:"))
        alarm_settings_layout.addWidget(self.alarm_code_input)
        alarm_settings_layout.addWidget(QLabel("报警信息:"))
        alarm_settings_layout.addWidget(self.alarm_message_input)
        
        alarm_control_layout.addLayout(alarm_settings_layout)
        alarm_control_layout.addWidget(self.trigger_alarm_button)
        alarm_control_layout.addWidget(self.clear_alarm_button)
        alarm_control_layout.addStretch()
        
        # 参数查询
        query_group = QGroupBox("参数查询")
        query_layout = QHBoxLayout(query_group)
        
        self.get_parameters_button = QPushButton("获取机床参数")
        self.get_axis_data_button = QPushButton("获取轴数据")
        
        query_layout.addWidget(self.get_parameters_button)
        query_layout.addWidget(self.get_axis_data_button)
        query_layout.addStretch()
        
        layout.addWidget(basic_control_group)
        layout.addWidget(alarm_control_group)
        layout.addWidget(query_group)
        layout.addStretch()
        
        self.tab_widget.addTab(control_tab, "控制操作")
        
    def create_log_tab(self):
        """创建日志标签页"""
        log_tab = QWidget()
        layout = QVBoxLayout(log_tab)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        
        # 日志控制
        log_control_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("清空日志")
        self.auto_scroll_checkbox = QCheckBox("自动滚动")
        self.auto_scroll_checkbox.setChecked(True)
        
        log_control_layout.addWidget(self.clear_log_button)
        log_control_layout.addWidget(self.auto_scroll_checkbox)
        log_control_layout.addStretch()
        
        layout.addLayout(log_control_layout)
        layout.addWidget(self.log_text)
        
        self.tab_widget.addTab(log_tab, "操作日志")
        
    def setup_connections(self):
        """设置信号槽连接"""
        # 连接控制按钮
        self.connect_button.clicked.connect(self.connect_machine)
        self.disconnect_button.clicked.connect(self.disconnect_machine)
        
        # 机床控制按钮
        self.start_button.clicked.connect(lambda: self.control_machine("start"))
        self.stop_button.clicked.connect(lambda: self.control_machine("stop"))
        self.pause_button.clicked.connect(lambda: self.control_machine("pause"))
        self.resume_button.clicked.connect(lambda: self.control_machine("resume"))
        self.trigger_alarm_button.clicked.connect(self.trigger_alarm)
        self.clear_alarm_button.clicked.connect(lambda: self.control_machine("clear_alarm"))
        
        # 参数查询按钮
        self.get_parameters_button.clicked.connect(self.get_machine_parameters)
        self.get_axis_data_button.clicked.connect(self.get_axis_data)
        
        # 日志控制按钮
        self.clear_log_button.clicked.connect(self.clear_log)
        
        # 控制器信号连接
        self.controller.connection_changed.connect(self.on_connection_changed)
        self.controller.status_updated.connect(self.on_status_updated)
        self.controller.log_message.connect(self.add_log_message)
        
    def setup_timers(self):
        """设置定时器"""
        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_machine_status)
        self.status_timer.setInterval(2000)  # 每2秒更新一次
        
    def connect_machine(self):
        """连接机床"""
        host = self.host_input.text().strip()
        port = self.port_input.value()
        machine_id = self.machine_id_input.text().strip()
        
        if not host or not machine_id:
            QMessageBox.warning(self, "输入错误", "请填写完整的连接信息")
            return
            
        if self.controller.connect_machine(host, port, machine_id):
            # 启动状态更新定时器
            self.status_timer.start()
            self.add_log_message("开始定期更新机床状态")
        else:
            QMessageBox.critical(self, "连接失败", "无法连接到机床，请检查连接设置")
            
    def disconnect_machine(self):
        """断开机床连接"""
        self.controller.disconnect_machine()
        # 停止状态更新定时器
        self.status_timer.stop()
        
    def on_connection_changed(self, connected: bool):
        """连接状态改变处理"""
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        
        # 控制操作按钮状态
        control_enabled = connected
        self.start_button.setEnabled(control_enabled)
        self.stop_button.setEnabled(control_enabled)
        self.pause_button.setEnabled(control_enabled)
        self.resume_button.setEnabled(control_enabled)
        self.trigger_alarm_button.setEnabled(control_enabled)
        self.clear_alarm_button.setEnabled(control_enabled)
        self.get_parameters_button.setEnabled(control_enabled)
        self.get_axis_data_button.setEnabled(control_enabled)
        
        # 更新状态栏
        status_text = "已连接" if connected else "未连接"
        self.connection_label.setText(status_text)
        self.connection_label.setStyleSheet(
            "color: green;" if connected else "color: red;"
        )
        
    def update_machine_status(self):
        """更新机床状态"""
        if self.controller and self.controller.is_connected:
            self.controller.get_status()
            
    def on_status_updated(self, status_data: dict):
        """状态更新处理"""
        # 更新基本信息
        self.machine_id_label.setText(status_data.get("machine_id", "-"))
        self.program_label.setText(status_data.get("program_name", "-"))
        self.timestamp_label.setText(status_data.get("timestamp", "-"))
        
        # 更新状态（带颜色）
        status = status_data.get("status", "-")
        self.status_label.setText(status)
        
        # 根据状态设置颜色
        status_colors = {
            "OFF": "gray",
            "IDLE": "blue",
            "RUNNING": "green",
            "ALARM": "red",
            "STOPPED": "orange",
            "PAUSED": "purple"
        }
        color = status_colors.get(status, "black")
        self.status_label.setStyleSheet(f"font-weight: bold; color: {color};")
        
        # 更新运行参数
        self.spindle_speed_label.setText(f"{status_data.get('spindle_speed', '-')} RPM")
        self.feed_rate_label.setText(f"{status_data.get('feed_rate', '-')} mm/min")
        self.spindle_load_label.setText(f"{status_data.get('spindle_load', '-')}%")
        self.workpiece_count_label.setText(str(status_data.get('workpiece_count', '-')))
        
        # 更新报警信息
        alarm_code = status_data.get('alarm_code', '-')
        alarm_message = status_data.get('alarm_message', '-')
        self.alarm_code_label.setText(f"报警代码: {alarm_code}")
        self.alarm_message_label.setText(f"报警信息: {alarm_message}")
        
        # 根据是否有报警设置颜色
        if alarm_code != 0 and alarm_code != '-':
            self.alarm_code_label.setStyleSheet("color: red; font-weight: bold;")
            self.alarm_message_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.alarm_code_label.setStyleSheet("color: black; font-weight: normal;")
            self.alarm_message_label.setStyleSheet("color: black; font-weight: normal;")
            
    def control_machine(self, operation: str):
        """控制机床"""
        self.controller.control_machine(operation)
        
    def trigger_alarm(self):
        """触发报警"""
        alarm_code = self.alarm_code_input.value()
        alarm_message = self.alarm_message_input.text().strip()
        
        self.controller.control_machine(
            "trigger_alarm", 
            alarm_code=alarm_code, 
            alarm_message=alarm_message
        )
        
    def get_machine_parameters(self):
        """获取机床参数"""
        if not self.controller.is_connected or not self.controller.machine_manager:
            self.add_log_message("机床未连接")
            return
            
        try:
            params = self.controller.machine_manager.get_machine_parameters()
            
            if params and params.get("success"):
                data = params["data"]
                message = (
                    f"机床参数:\n"
                    f"  机床ID: {data.get('machine_id', '-')}\n"
                    f"  系统版本: {data.get('system_version', '-')}\n"
                    f"  控制器类型: {data.get('controller_type', '-')}\n"
                    f"  最大主轴转速: {data.get('max_spindle_speed', '-')} RPM\n"
                    f"  最大进给速度: {data.get('max_feed_rate', '-')} mm/min\n"
                    f"  刀具数量: {data.get('tool_count', '-')}\n"
                    f"  轴数: {data.get('axis_count', '-')}"
                )
                self.add_log_message(message)
            else:
                error_msg = params.get("error", "未知错误") if params else "无响应"
                self.add_log_message(f"获取参数失败: {error_msg}")
                
        except Exception as e:
            self.add_log_message(f"获取参数时出错: {str(e)}")
            
    def get_axis_data(self):
        """获取轴数据"""
        if not self.controller.is_connected or not self.controller.machine_manager:
            self.add_log_message("机床未连接")
            return
            
        try:
            axis_data = self.controller.machine_manager.get_axis_data()
            
            if axis_data and axis_data.get("success"):
                data = axis_data["data"]
                message = (
                    f"轴数据:\n"
                    f"  轴位置: {data.get('axis_positions', '-')}\n"
                    f"  主轴负载: {data.get('spindle_load', '-')}%"
                )
                self.add_log_message(message)
            else:
                error_msg = axis_data.get("error", "未知错误") if axis_data else "无响应"
                self.add_log_message(f"获取轴数据失败: {error_msg}")
                
        except Exception as e:
            self.add_log_message(f"获取轴数据时出错: {str(e)}")
            
    def add_log_message(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_text.append(formatted_message)
        
        # 自动滚动到最新日志
        if self.auto_scroll_checkbox.isChecked():
            self.log_text.moveCursor(QTextCursor.MoveOperation.End)
            
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 断开机床连接
        if self.controller.is_connected:
            self.controller.disconnect_machine()
            
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = CNCMachineUI()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()