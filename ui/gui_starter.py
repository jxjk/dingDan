"""
GUI启动器模块
图形界面主窗口实现
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time
import threading
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.system_manager import get_system_manager
from ui.dialogs import AddTaskDialog, QRScanDialog


class SystemStarterGUI:
    """系统启动器图形界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("数控车床生产管理系统")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 系统状态
        self.system_manager = get_system_manager()
        self.system = self.system_manager
        self.is_running = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, 
                               text="数控车床生产管理系统", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 启动模式选择
        mode_frame = ttk.LabelFrame(main_frame, text="启动模式选择", padding="10")
        mode_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        mode_frame.columnconfigure(0, weight=1)
        
        # 模式选择按钮
        self.mode_var = tk.StringVar(value="cli")
        
        mode_cli = ttk.Radiobutton(mode_frame, text="命令行界面 (推荐)", 
                                  variable=self.mode_var, value="cli")
        mode_cli.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        mode_service = ttk.Radiobutton(mode_frame, text="后台服务模式", 
                                      variable=self.mode_var, value="service")
        mode_service.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        mode_test = ttk.Radiobutton(mode_frame, text="测试模式", 
                                   variable=self.mode_var, value="test")
        mode_test.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="启动系统", 
                                      command=self.start_system)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="停止系统", 
                                     command=self.stop_system, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(button_frame, text="检查依赖", 
                  command=self.check_dependencies).grid(row=0, column=2, padx=(0, 10))
        
        ttk.Button(button_frame, text="退出", 
                  command=self.quit_app).grid(row=0, column=3)
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(main_frame, text="系统状态", padding="10")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=15, width=80)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 快速操作面板
        quick_frame = ttk.LabelFrame(main_frame, text="快速操作", padding="10")
        quick_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(quick_frame, text="查看任务", 
                  command=self.show_tasks).grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(quick_frame, text="查看材料", 
                  command=self.show_materials).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(quick_frame, text="添加任务", 
                  command=self.add_task).grid(row=0, column=2, padx=(0, 10))
        
        ttk.Button(quick_frame, text="扫描二维码", 
                  command=self.scan_qr).grid(row=0, column=3, padx=(0, 10))
        
        ttk.Button(quick_frame, text="任务调度", 
                  command=self.schedule_tasks).grid(row=0, column=4, padx=(0, 10))
    
    def log_message(self, message: str):
        """在状态区域显示消息"""
        self.status_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.status_text.see(tk.END)
        self.root.update()
    
    def check_dependencies(self):
        """检查依赖包"""
        self.log_message("正在检查依赖包...")
        
        # 这里可以添加实际的依赖检查逻辑
        # 暂时返回True表示检查通过
        try:
            import pandas
            import requests
            import pyautogui
            self.log_message("✅ 所有依赖包已安装")
            messagebox.showinfo("依赖检查", "所有依赖包已安装")
        except ImportError as e:
            self.log_message(f"❌ 缺少依赖包: {e}")
            messagebox.showerror("依赖检查", f"缺少依赖包: {e}\n请运行: pip install -r requirements.txt")
    
    def start_system(self):
        """启动系统"""
        mode = self.mode_var.get()
        
        if mode == "cli":
            self._start_cli_mode()
        elif mode == "service":
            self._start_service_mode()
        elif mode == "test":
            self._start_test_mode()
    
    def schedule_tasks(self):
        """执行任务调度"""
        if not self.system or not self.is_running:
            messagebox.showwarning("系统状态", "系统未运行，无法执行任务调度")
            return
        
        try:
            self.log_message("开始执行任务调度...")
            
            # 调用系统管理器的任务调度功能
            assignments = self.system.task_scheduler.schedule_tasks()
            
            if assignments:
                self.log_message(f"✅ 任务调度完成，成功分配 {len(assignments)} 个任务")
                # 显示分配结果
                assignment_info = "任务分配结果:\n"
                for task, machine_id in assignments:
                    assignment_info += f"  任务 {task.task_id} -> 机床 {machine_id}\n"
                
                messagebox.showinfo("任务调度", assignment_info)
            else:
                self.log_message("ℹ️ 本次调度未分配任何任务")
                messagebox.showinfo("任务调度", "本次调度未分配任何任务")
                
        except Exception as e:
            error_msg = f"任务调度失败: {e}"
            self.log_message(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
    
    def _start_cli_mode(self):
        """启动命令行界面"""
        self.log_message("启动命令行界面...")
        
        def run_cli():
            try:
                from ui.cli_interface import CLIInterface
                cli = CLIInterface()
                cli.run()
            except Exception as e:
                self.log_message(f"命令行界面启动失败: {e}")
        
        thread = threading.Thread(target=run_cli, daemon=True)
        thread.start()
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.is_running = True
    
    def _start_service_mode(self):
        """启动后台服务模式"""
        self.log_message("启动后台服务模式...")
        
        def run_service():
            try:
                # 使用系统管理器启动服务
                if not self.system_manager.is_initialized:
                    if not self.system_manager.initialize_system():
                        self.log_message("❌ 系统初始化失败")
                        return
                
                self.log_message("✅ 后台服务已启动")
                
                # 保持服务运行
                while self.is_running:
                    time.sleep(1)
                    
            except Exception as e:
                self.log_message(f"后台服务启动失败: {e}")
        
        thread = threading.Thread(target=run_service, daemon=True)
        thread.start()
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.is_running = True
    
    def _start_test_mode(self):
        """启动测试模式"""
        self.log_message("启动测试模式...")
        
        def run_tests():
            try:
                # 使用子进程运行测试，避免导入问题
                result = subprocess.run([sys.executable, "tests/test_system.py"], 
                                      capture_output=True, text=True)
                
                self.log_message("测试输出:")
                self.log_message(result.stdout)
                if result.stderr:
                    self.log_message("测试错误:")
                    self.log_message(result.stderr)
                
                if result.returncode == 0:
                    self.log_message("✅ 所有测试通过")
                    messagebox.showinfo("测试结果", "所有测试通过！")
                else:
                    self.log_message("❌ 部分测试失败")
                    messagebox.showerror("测试结果", "部分测试失败，请查看日志")
                    
            except Exception as e:
                self.log_message(f"测试模式启动失败: {e}")
                messagebox.showerror("测试错误", f"测试模式启动失败: {e}")
        
        thread = threading.Thread(target=run_tests, daemon=True)
        thread.start()
    
    def stop_system(self):
        """停止系统"""
        self.log_message("正在停止系统...")
        
        if self.system:
            self.system.stop_system()
        
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log_message("系统已停止")
    
    def show_tasks(self):
        """显示任务列表"""
        if not self.system or not self.is_running:
            messagebox.showwarning("系统状态", "系统未运行，无法查看任务")
            return
        
        try:
            # 获取详细任务列表
            task_list = self.system.get_task_list()
            
            if not task_list:
                messagebox.showinfo("任务列表", "当前没有任务")
                return
            
            # 构建任务信息
            task_info = "任务列表:\n\n"
            for task in task_list:
                task_info += f"任务ID: {task.get('task_id', '未知')}\n"
                task_info += f"  指示书编号: {task.get('instruction_id', '未知')}\n"
                task_info += f"  产品型号: {task.get('product_model', '未知')}\n"
                task_info += f"  材料规格: {task.get('material_spec', '未知')}\n"
                task_info += f"  订单数量: {task.get('order_quantity', 0)}\n"
                task_info += f"  优先级: {task.get('priority', '未知')}\n"
                task_info += f"  状态: {task.get('status', '未知')}\n"
                task_info += f"  创建时间: {task.get('created_at', '未知')}\n"
                task_info += "-" * 40 + "\n"
            
            # 创建新窗口显示任务列表
            task_window = tk.Toplevel(self.root)
            task_window.title("任务列表")
            task_window.geometry("600x400")
            
            # 创建文本框和滚动条
            text_frame = ttk.Frame(task_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.insert(tk.END, task_info)
            text_widget.config(state=tk.DISABLED)  # 只读
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
        except Exception as e:
            messagebox.showerror("错误", f"获取任务信息失败: {e}")
    
    def show_materials(self):
        """显示材料库存"""
        if not self.system or not self.is_running:
            messagebox.showwarning("系统状态", "系统未运行，无法查看材料")
            return
        
        try:
            # 获取详细材料列表
            material_list = self.system.get_material_list()
            
            if not material_list:
                messagebox.showinfo("材料库存", "没有材料数据")
                return
            
            # 构建材料信息
            material_info = "材料库存列表:\n\n"
            for material in material_list:
                material_info += f"材料名称: {material.get('材料名称', '未知')}\n"
                material_info += f"  规格: {material.get('材料规格', '未知')}\n"
                material_info += f"  库存: {material.get('库存数量', 0)} {material.get('单位', '')}\n"
                material_info += f"  供应商: {material.get('供应商', '未知')}\n"
                material_info += f"  备注: {material.get('备注', '无')}\n"
                material_info += "-" * 40 + "\n"
            
            # 创建新窗口显示材料列表
            material_window = tk.Toplevel(self.root)
            material_window.title("材料库存")
            material_window.geometry("600x400")
            
            # 创建文本框和滚动条
            text_frame = ttk.Frame(material_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.insert(tk.END, material_info)
            text_widget.config(state=tk.DISABLED)  # 只读
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
        except Exception as e:
            messagebox.showerror("错误", f"获取材料信息失败: {e}")
    
    def add_task(self):
        """添加新任务"""
        if not self.system or not self.is_running:
            messagebox.showwarning("系统状态", "系统未运行，无法添加任务")
            return
        
        dialog = AddTaskDialog(self.root, self.system, self.log_message)
        dialog.show()
    
    def scan_qr(self):
        """扫描二维码"""
        if not self.system or not self.is_running:
            messagebox.showwarning("系统状态", "系统未运行，无法扫描二维码")
            return
        
        dialog = QRScanDialog(self.root, self.system, self.log_message)
        dialog.show()
    
    def quit_app(self):
        """退出应用程序"""
        if self.is_running:
            if messagebox.askyesno("确认退出", "系统正在运行，确定要退出吗？"):
                self.stop_system()
                self.root.quit()
        else:
            self.root.quit()
    
    def run(self):
        """运行GUI应用程序"""
        # 初始化系统
        self.log_message("正在初始化系统...")
        
        # 创建必要的目录和文件
        try:
            import os
            os.makedirs("logs", exist_ok=True)
            os.makedirs("data", exist_ok=True)
            os.makedirs("config", exist_ok=True)
            self.log_message("✅ 目录结构创建成功")
        except Exception as e:
            self.log_message(f"❌ 目录创建失败: {e}")
        
        self.log_message("数控车床生产管理系统启动器已就绪")
        self.log_message("请选择启动模式并点击'启动系统'")
        
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.mainloop()


def main():
    """主函数"""
    try:
        app = SystemStarterGUI()
        app.run()
    except Exception as e:
        print(f"GUI启动失败: {e}")


if __name__ == "__main__":
    main()