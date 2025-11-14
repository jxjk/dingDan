"""
多CNC机床UI管理器
用于同时启动和管理多个CNC机床UI界面
"""

import sys
import json
import argparse
import subprocess
from typing import List, Dict, Any
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QFormLayout, QLineEdit, QSpinBox, QMessageBox, QFileDialog,
    QTabWidget, QTextEdit, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from cnc_machine_ui import CNCMachineUI
    UI_AVAILABLE = True
except ImportError as e:
    UI_AVAILABLE = False
    print(f"警告: CNC机床UI不可用: {e}")


class MultiCNCUIManager(QMainWindow):
    """多CNC机床UI管理器"""
    
    def __init__(self):
        super().__init__()
        self.ui_windows: List[CNCMachineUI] = []
        self.simulator_processes: List[subprocess.Popen] = []
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("多CNC机床UI管理器")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建控制面板
        control_group = QGroupBox("控制面板")
        control_layout = QHBoxLayout(control_group)
        
        self.start_all_button = QPushButton("启动所有UI")
        self.stop_all_button = QPushButton("关闭所有UI")
        self.add_machine_button = QPushButton("添加机床")
        self.load_config_button = QPushButton("从配置文件加载")
        self.start_simulators_button = QPushButton("启动模拟器")
        self.stop_simulators_button = QPushButton("停止模拟器")
        
        control_layout.addWidget(self.start_simulators_button)
        control_layout.addWidget(self.stop_simulators_button)
        control_layout.addWidget(self.start_all_button)
        control_layout.addWidget(self.stop_all_button)
        control_layout.addWidget(self.add_machine_button)
        control_layout.addWidget(self.load_config_button)
        control_layout.addStretch()
        
        # 创建机床列表
        machine_group = QGroupBox("机床列表")
        machine_layout = QVBoxLayout(machine_group)
        
        self.machine_table = QTableWidget(0, 5)
        self.machine_table.setHorizontalHeaderLabels(["机床ID", "主机地址", "端口", "状态", "自动启动模拟器"])
        self.machine_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        machine_layout.addWidget(self.machine_table)
        
        # 创建日志面板
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMaximumHeight(150)
        
        log_layout.addWidget(self.log_text)
        
        # 添加到主布局
        main_layout.addWidget(control_group)
        main_layout.addWidget(machine_group)
        main_layout.addWidget(log_group)
        
        # 连接信号槽
        self.start_all_button.clicked.connect(self.start_all_uis)
        self.stop_all_button.clicked.connect(self.stop_all_uis)
        self.add_machine_button.clicked.connect(self.add_machine_dialog)
        self.load_config_button.clicked.connect(self.load_from_config)
        self.start_simulators_button.clicked.connect(self.start_simulators)
        self.stop_simulators_button.clicked.connect(self.stop_simulators)
        
        # 添加默认机床
        self.add_machine("CNC-01", "127.0.0.1", 8193, True)
        self.add_machine("CNC-02", "127.0.0.1", 8194, True)
        self.add_machine("CNC-03", "127.0.0.1", 8195, True)
        
        self.log_message("多CNC机床UI管理器已启动")
        
    def add_machine(self, machine_id: str, host: str, port: int, auto_start_sim: bool = False):
        """添加机床到列表"""
        row_position = self.machine_table.rowCount()
        self.machine_table.insertRow(row_position)
        
        # 创建表格项
        machine_id_item = QTableWidgetItem(machine_id)
        host_item = QTableWidgetItem(host)
        port_item = QTableWidgetItem(str(port))
        status_item = QTableWidgetItem("未启动")
        auto_start_item = QTableWidgetItem("是" if auto_start_sim else "否")
        
        # 设置项不可编辑
        machine_id_item.setFlags(machine_id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        host_item.setFlags(host_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        port_item.setFlags(port_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        auto_start_item.setFlags(auto_start_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        
        # 添加到表格
        self.machine_table.setItem(row_position, 0, machine_id_item)
        self.machine_table.setItem(row_position, 1, host_item)
        self.machine_table.setItem(row_position, 2, port_item)
        self.machine_table.setItem(row_position, 3, status_item)
        self.machine_table.setItem(row_position, 4, auto_start_item)
        
        self.log_message(f"已添加机床: {machine_id} ({host}:{port})")
        
    def start_simulators(self):
        """启动所有需要的模拟器"""
        try:
            # 关闭现有的模拟器进程
            self.stop_simulators()
            
            sim_script = str(Path(__file__).parent / "simulate_fanuc_cnc.py")
            
            # 为每个需要自动启动的机床启动模拟器
            started_count = 0
            for row in range(self.machine_table.rowCount()):
                auto_start_text = self.machine_table.item(row, 4).text()
                if auto_start_text == "是":
                    host = self.machine_table.item(row, 1).text()
                    port = int(self.machine_table.item(row, 2).text())
                    
                    # 启动模拟器进程
                    cmd = [sys.executable, sim_script, "--host", host, "--port", str(port)]
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.simulator_processes.append(process)
                    started_count += 1
                    self.log_message(f"已启动模拟器: {host}:{port}")
            
            self.log_message(f"成功启动 {started_count} 个模拟器进程")
            QMessageBox.information(self, "成功", f"已启动 {started_count} 个模拟器进程")
            
        except Exception as e:
            error_msg = f"启动模拟器时出错: {str(e)}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            
    def stop_simulators(self):
        """停止所有模拟器"""
        stopped_count = 0
        for process in self.simulator_processes:
            try:
                process.terminate()
                process.wait(timeout=3)
                stopped_count += 1
            except subprocess.TimeoutExpired:
                process.kill()
                stopped_count += 1
            except Exception as e:
                self.log_message(f"停止模拟器进程时出错: {str(e)}")
        
        self.simulator_processes.clear()
        self.log_message(f"已停止 {stopped_count} 个模拟器进程")
        
    def start_all_uis(self):
        """启动所有UI界面"""
        if not UI_AVAILABLE:
            QMessageBox.critical(self, "错误", "CNC机床UI不可用")
            return
            
        try:
            # 关闭现有的UI窗口
            self.stop_all_uis()
            
            # 为每个机床创建UI界面
            for row in range(self.machine_table.rowCount()):
                machine_id = self.machine_table.item(row, 0).text()
                host = self.machine_table.item(row, 1).text()
                port = int(self.machine_table.item(row, 2).text())
                
                # 创建新的UI窗口
                ui_window = CNCMachineUI()
                ui_window.setWindowTitle(f"CNC机床控制面板 - {machine_id}")
                
                # 设置连接信息
                ui_window.host_input.setText(host)
                ui_window.port_input.setValue(port)
                ui_window.machine_id_input.setText(machine_id)
                
                # 显示窗口
                ui_window.show()
                
                # 保存窗口引用
                self.ui_windows.append(ui_window)
                
                # 更新状态
                self.machine_table.item(row, 3).setText("已启动")
                
            self.log_message(f"成功启动 {len(self.ui_windows)} 个机床UI界面")
            
        except Exception as e:
            error_msg = f"启动UI界面时出错: {str(e)}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            
    def stop_all_uis(self):
        """关闭所有UI界面"""
        for ui_window in self.ui_windows:
            try:
                ui_window.close()
            except Exception as e:
                self.log_message(f"关闭UI窗口时出错: {str(e)}")
                
        self.ui_windows.clear()
        
        # 更新状态
        for row in range(self.machine_table.rowCount()):
            self.machine_table.item(row, 3).setText("未启动")
            
        self.log_message("已关闭所有机床UI界面")
        
    def add_machine_dialog(self):
        """显示添加机床对话框"""
        # 创建对话框部件
        dialog = QWidget()
        dialog.setWindowTitle("添加机床")
        dialog.setWindowFlags(Qt.WindowType.Dialog)
        dialog.setGeometry(200, 200, 300, 250)
        
        layout = QFormLayout(dialog)
        
        # 输入字段
        machine_id_input = QLineEdit()
        host_input = QLineEdit("127.0.0.1")
        port_input = QSpinBox()
        port_input.setRange(1, 65535)
        port_input.setValue(8193)
        auto_start_checkbox = QCheckBox("自动启动模拟器")
        auto_start_checkbox.setChecked(True)
        
        layout.addRow("机床ID:", machine_id_input)
        layout.addRow("主机地址:", host_input)
        layout.addRow("端口:", port_input)
        layout.addRow("自动启动模拟器:", auto_start_checkbox)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        add_button = QPushButton("添加")
        cancel_button = QPushButton("取消")
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(cancel_button)
        
        layout.addRow(button_layout)
        
        # 连接信号
        def add_machine_action():
            machine_id = machine_id_input.text().strip()
            host = host_input.text().strip()
            port = port_input.value()
            auto_start = auto_start_checkbox.isChecked()
            
            if not machine_id or not host:
                QMessageBox.warning(dialog, "输入错误", "请填写完整的机床信息")
                return
                
            self.add_machine(machine_id, host, port, auto_start)
            dialog.close()
            
        def cancel_action():
            dialog.close()
            
        add_button.clicked.connect(add_machine_action)
        cancel_button.clicked.connect(cancel_action)
        
        dialog.show()
        
    def load_from_config(self):
        """从配置文件加载机床列表"""
        try:
            # 打文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择配置文件", "", "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
                
            # 读取配置文件
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            machines = config.get('machines', [])
            if not machines:
                QMessageBox.warning(self, "配置错误", "配置文件中未找到机床信息")
                return
                
            # 清空现有列表
            self.machine_table.setRowCount(0)
            self.ui_windows.clear()
            
            # 添加机床
            for machine in machines:
                machine_id = machine.get('machine_id', machine.get('id', 'UNKNOWN'))
                host = machine.get('host', '127.0.0.1')
                port = machine.get('port', 8193)
                auto_start = machine.get('auto_start', True)
                self.add_machine(machine_id, host, port, auto_start)
                
            self.log_message(f"从配置文件加载了 {len(machines)} 台机床")
            
        except FileNotFoundError:
            QMessageBox.critical(self, "错误", "配置文件未找到")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "错误", "配置文件格式错误")
        except Exception as e:
            error_msg = f"加载配置文件时出错: {str(e)}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            
    def log_message(self, message: str):
        """添加日志消息"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.stop_all_uis()
        self.stop_simulators()
        event.accept()


def create_default_config():
    """创建默认配置文件"""
    config = {
        "machines": [
            {"machine_id": "CNC-01", "host": "127.0.0.1", "port": 8193, "auto_start": True},
            {"machine_id": "CNC-02", "host": "127.0.0.1", "port": 8194, "auto_start": True},
            {"machine_id": "CNC-03", "host": "127.0.0.1", "port": 8195, "auto_start": True},
            {"machine_id": "CNC-04", "host": "192.168.1.100", "port": 8193, "auto_start": False}
        ]
    }
    
    with open("multi_cnc_ui_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("已创建默认多CNC机床UI配置文件: multi_cnc_ui_config.json")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='多CNC机床UI管理器')
    parser.add_argument('--create-config', action='store_true', help='创建默认配置文件')
    
    args = parser.parse_args()
    
    if args.create_config:
        create_default_config()
        return
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    if not UI_AVAILABLE:
        QMessageBox.critical(None, "错误", "CNC机床UI不可用，请检查依赖项")
        sys.exit(1)
    
    window = MultiCNCUIManager()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()