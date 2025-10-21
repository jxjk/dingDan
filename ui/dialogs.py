"""
对话框模块
包含各种对话框实现
"""

import tkinter as tk
from tkinter import ttk, messagebox


class AddTaskDialog:
    """添加任务对话框"""
    
    def __init__(self, parent, system, log_callback):
        self.parent = parent
        self.system = system
        self.log_callback = log_callback
        self.dialog = None
    
    def show(self):
        """显示对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("添加新任务")
        self.dialog.geometry("400x300")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 对话框内容
        frame = ttk.Frame(self.dialog, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame, text="指示书编号:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.instruction_entry = ttk.Entry(frame, width=30)
        self.instruction_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        ttk.Label(frame, text="产品型号:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.model_entry = ttk.Entry(frame, width=30)
        self.model_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        ttk.Label(frame, text="材料规格:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.material_entry = ttk.Entry(frame, width=30)
        self.material_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        ttk.Label(frame, text="订单数量:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.quantity_entry = ttk.Entry(frame, width=30)
        self.quantity_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        ttk.Label(frame, text="优先级:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.priority_combo = ttk.Combobox(frame, values=["Normal", "High", "Urgent"], width=27)
        self.priority_combo.set("Normal")
        self.priority_combo.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="添加任务", command=self._submit_task).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy).grid(row=0, column=1)
        
        frame.columnconfigure(1, weight=1)
    
    def _submit_task(self):
        """提交任务"""
        try:
            instruction_id = self.instruction_entry.get().strip()
            product_model = self.model_entry.get().strip()
            material_spec = self.material_entry.get().strip()
            order_quantity = int(self.quantity_entry.get().strip())
            priority = self.priority_combo.get()
            
            if not all([instruction_id, product_model, material_spec]):
                messagebox.showerror("输入错误", "请填写所有必填字段")
                return
            
            task_id = self.system.add_new_task(
                instruction_id=instruction_id,
                product_model=product_model,
                material_spec=material_spec,
                order_quantity=order_quantity,
                priority=priority
            )
            
            self.log_callback(f"✅ 任务添加成功! 任务ID: {task_id}")
            messagebox.showinfo("成功", f"任务添加成功!\n任务ID: {task_id}")
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("输入错误", "请确保数量为有效数字")
        except Exception as e:
            messagebox.showerror("错误", f"添加任务失败: {e}")


class QRScanDialog:
    """扫描二维码对话框"""
    
    def __init__(self, parent, system, log_callback):
        self.parent = parent
        self.system = system
        self.log_callback = log_callback
        self.dialog = None
    
    def show(self):
        """显示对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("扫描二维码")
        self.dialog.geometry("400x200")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        frame = ttk.Frame(self.dialog, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame, text="请输入二维码内容:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.qr_entry = ttk.Entry(frame, width=40)
        self.qr_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, pady=20)
        
        ttk.Button(button_frame, text="扫描", command=self._submit_qr).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy).grid(row=0, column=1)
        
        frame.columnconfigure(0, weight=1)
    
    def _submit_qr(self):
        """提交二维码扫描"""
        qr_content = self.qr_entry.get().strip()
        if not qr_content:
            messagebox.showerror("输入错误", "二维码内容不能为空")
            return
        
        try:
            result = self.system.scan_qr_code(qr_content)
            
            if result['success']:
                self.log_callback("✅ 二维码扫描成功!")
                parsed_data = result['parsed_data']
                info = f"解析结果:\n"
                for key, value in parsed_data.items():
                    info += f"{key}: {value}\n"
                
                messagebox.showinfo("扫描成功", info)
                self.dialog.destroy()
            else:
                messagebox.showerror("扫描失败", f"二维码扫描失败: {result['error']}")
                
        except Exception as e:
            messagebox.showerror("错误", f"扫描二维码失败: {e}")


class StatusDialog:
    """状态显示对话框"""
    
    def __init__(self, parent, title, content):
        self.parent = parent
        self.title = title
        self.content = content
        self.dialog = None
    
    def show(self):
        """显示对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("500x400")
        self.dialog.transient(self.parent)
        
        frame = ttk.Frame(self.dialog, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        text_widget = tk.Text(frame, wrap=tk.WORD, width=60, height=20)
        text_widget.insert(tk.END, self.content)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        ttk.Button(frame, text="关闭", command=self.dialog.destroy).grid(row=1, column=0, pady=10)
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
