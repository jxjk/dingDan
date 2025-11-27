"""
UI自动化服务
实现DNC系统、日报系统和检验系统的自动化操作
"""

import logging
import time
import subprocess
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    import pywinauto
    from pywinauto.application import Application
    from pywinauto.findwindows import ElementNotFoundError
except ImportError:
    pywinauto = None

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    webdriver = None


class DNCSystemAutomation:
    """DNC系统自动化操作"""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.app = None
        self.window = None
        
    def connect_to_dnc(self) -> bool:
        """连接到DNC系统"""
        try:
            dnc_config = self.config['dnc_system']
            
            # 尝试连接到现有实例
            try:
                self.app = Application(backend="uia").connect(
                    title=dnc_config['window_title'],
                    class_name=dnc_config['class_name']
                )
                self.logger.info("已连接到运行的DNC系统实例")
            except ElementNotFoundError:
                # 启动新的DNC系统
                process_path = dnc_config['process_name']
                self.app = Application(backend="uia").start(process_path)
                self.logger.info("已启动新的DNC系统实例")
            
            # 获取主窗口
            self.window = self.app.window(title=dnc_config['window_title'])
            self.window.wait('visible', timeout=dnc_config['timeout'])
            
            self.logger.info("DNC系统连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"连接DNC系统失败: {e}")
            return False
    
    def input_model_number(self, model_number: str) -> bool:
        """输入型号编号"""
        try:
            input_controls = self.config['dnc_system']['controls']['main_input']
            
            for control_config in input_controls:
                try:
                    if control_config['method'] == 'auto_id':
                        input_field = self.window.child_window(
                            auto_id=control_config['value'])
                    elif control_config['method'] == 'name':
                        input_field = self.window.child_window(
                            title=control_config['value'])
                    
                    input_field.set_text(model_number)
                    self.logger.info(f"已输入型号编号: {model_number}")
                    return True
                    
                except Exception as e:
                    self.logger.debug(f"尝试控件 {control_config} 失败: {e}")
                    continue
            
            self.logger.error("无法找到型号输入框")
            return False
            
        except Exception as e:
            self.logger.error(f"输入型号编号失败: {e}")
            return False
    
    def submit_model(self) -> bool:
        """提交型号"""
        try:
            button_controls = self.config['dnc_system']['controls']['submit_button']
            
            for control_config in button_controls:
                try:
                    if control_config['method'] == 'auto_id':
                        submit_button = self.window.child_window(
                            auto_id=control_config['value'])
                    elif control_config['method'] == 'name':
                        submit_button = self.window.child_window(
                            title=control_config['value'])
                    
                    submit_button.click()
                    self.logger.info("已提交型号")
                    return True
                    
                except Exception as e:
                    self.logger.debug(f"尝试按钮 {control_config} 失败: {e}")
                    continue
            
            self.logger.error("无法找到提交按钮")
            return False
            
        except Exception as e:
            self.logger.error(f"提交型号失败: {e}")
            return False
    
    def process_model(self, model_number: str, task_info: Optional[Dict] = None) -> bool:
        """处理型号的完整流程，支持任务信息"""
        if not self.connect_to_dnc():
            return False
        
        # 如果提供了任务信息，可以处理更复杂的任务
        if task_info:
            # 根据任务信息生成宏变量字符串
            macro_string = self._generate_macro_string(task_info)
            self.logger.info(f"生成宏变量字符串: {macro_string}")
            
            # 如果宏变量字符串不为空，输入到DNC系统
            if macro_string:
                # 首先尝试输入宏变量字符串
                if not self._input_macro_string(macro_string):
                    # 如果输入宏变量失败，尝试输入型号
                    if not self.input_model_number(model_number):
                        return False
            else:
                # 如果没有宏变量，直接输入型号
                if not self.input_model_number(model_number):
                    return False
        else:
            # 传统模式，只输入型号
            if not self.input_model_number(model_number):
                return False
        
        if not self.submit_model():
            return False
        
        # 等待处理完成
        time.sleep(2)
        self.logger.info(f"型号 {model_number} 处理完成")
        return True
    
    def _generate_macro_string(self, task_info: Dict) -> str:
        """根据任务信息生成宏变量字符串"""
        try:
            # 根据系统构想，生成宏变量字符串
            # 例如: #100=任务ID, #101=材料类型, #110=数量等
            macro_parts = []
            
            # 任务ID (如果有的话)
            if 'task_id' in task_info:
                # 提取任务ID中的数字部分
                import re
                task_num = re.findall(r'\d+', str(task_info['task_id']))
                if task_num:
                    macro_parts.append(f"100={task_num[0]}")  # 假设任务ID数字作为#100的值
            
            # 产品型号
            if 'product_model' in task_info:
                # 为产品模型分配一个变量（这需要与DNC系统约定的变量编号一致）
                # 这里假设#101用于产品型号
                macro_parts.append(f"101={task_info['product_model']}")
            
            # 材料规格
            if 'material_spec' in task_info:
                # 为材料规格分配一个变量，例如#102
                material_mapping = {
                    'S45C': '1',
                    'AL6061': '2', 
                    'SS304': '3',
                    '黄铜': '4'
                }
                material_code = material_mapping.get(task_info['material_spec'], '0')
                macro_parts.append(f"102={material_code}")
            
            # 订单数量
            if 'order_quantity' in task_info:
                macro_parts.append(f"110={task_info['order_quantity']}")
            
            # 生成完整的宏变量字符串
            if macro_parts:
                return ','.join(macro_parts)
            else:
                return ""
            
        except Exception as e:
            self.logger.error(f"生成宏变量字符串失败: {e}")
            return ""
    
    def _input_macro_string(self, macro_string: str) -> bool:
        """输入宏变量字符串到DNC系统"""
        try:
            # 这里可以根据实际DNC系统的输入方式调整
            # 有些系统可能需要特定的输入格式或控件
            self.logger.info(f"输入宏变量字符串: {macro_string}")
            return True  # 暂时返回True，实际实现需要根据DNC系统界面调整
        except Exception as e:
            self.logger.error(f"输入宏变量字符串失败: {e}")
            return False
    
    def close_dnc(self):
        """关闭DNC系统"""
        try:
            if self.app:
                self.app.kill()
                self.logger.info("DNC系统已关闭")
        except Exception as e:
            self.logger.error(f"关闭DNC系统失败: {e}")


class BrowserAutomation:
    """浏览器系统自动化操作"""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.driver = None
        
    def setup_driver(self) -> bool:
        """设置浏览器驱动"""
        try:
            # 使用Chrome浏览器
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(10)
            
            self.logger.info("浏览器驱动设置成功")
            return True
            
        except Exception as e:
            self.logger.error(f"设置浏览器驱动失败: {e}")
            return False
    
    def input_instruction_to_daily_report(self, instruction_id: str) -> bool:
        """在日报系统中输入指示书编号"""
        try:
            system_config = self.config['browser_systems']['daily_report']
            
            # 打开日报系统
            self.driver.get(system_config['url'])
            
            # 输入指示书编号
            input_selectors = system_config['instruction_input']
            input_element = None
            
            for selector_config in input_selectors:
                try:
                    if selector_config['selector'] == 'css':
                        input_element = self.driver.find_element(
                            By.CSS_SELECTOR, selector_config['value'])
                    elif selector_config['selector'] == 'name':
                        input_element = self.driver.find_element(
                            By.NAME, selector_config['value'])
                    elif selector_config['selector'] == 'id':
                        input_element = self.driver.find_element(
                            By.ID, selector_config['value'])
                    
                    if input_element:
                        input_element.clear()
                        input_element.send_keys(instruction_id)
                        self.logger.info(f"日报系统已输入指示书编号: {instruction_id}")
                        break
                        
                except NoSuchElementException:
                    continue
            
            if not input_element:
                self.logger.error("无法找到日报系统的指示书输入框")
                return False
            
            # 提交表单
            submit_selectors = system_config['submit_button']
            submit_element = None
            
            for selector_config in submit_selectors:
                try:
                    if selector_config['selector'] == 'css':
                        submit_element = self.driver.find_element(
                            By.CSS_SELECTOR, selector_config['value'])
                    
                    if submit_element:
                        submit_element.click()
                        self.logger.info("日报系统表单已提交")
                        break
                        
                except NoSuchElementException:
                    continue
            
            # 等待处理完成
            time.sleep(3)
            return True
            
        except Exception as e:
            self.logger.error(f"日报系统操作失败: {e}")
            return False
    
    def input_instruction_to_inspection_system(self, instruction_id: str) -> bool:
        """在检验系统中输入指示书编号"""
        try:
            system_config = self.config['browser_systems']['inspection_system']
            
            # 打开检验系统
            self.driver.get(system_config['url'])
            
            # 输入指示书编号
            input_selectors = system_config['instruction_input']
            input_element = None
            
            for selector_config in input_selectors:
                try:
                    if selector_config['selector'] == 'id':
                        input_element = self.driver.find_element(
                            By.ID, selector_config['value'])
                    elif selector_config['selector'] == 'name':
                        input_element = self.driver.find_element(
                            By.NAME, selector_config['value'])
                    
                    if input_element:
                        input_element.clear()
                        input_element.send_keys(instruction_id)
                        self.logger.info(f"检验系统已输入指示书编号: {instruction_id}")
                        break
                        
                except NoSuchElementException:
                    continue
            
            if not input_element:
                self.logger.error("无法找到检验系统的指示书输入框")
                return False
            
            # 等待处理完成
            time.sleep(2)
            return True
            
        except Exception as e:
            self.logger.error(f"检验系统操作失败: {e}")
            return False
    
    def close_browser(self):
        """关闭浏览器"""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("浏览器已关闭")
        except Exception as e:
            self.logger.error(f"关闭浏览器失败: {e}")


class AutomationManager:
    """自动化管理器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.dnc_automation = DNCSystemAutomation(config)
        self.browser_automation = BrowserAutomation(config)
        
    def process_instruction(self, instruction_id: str, model_number: str, task_info: Optional[Dict] = None) -> Dict[str, bool]:
        """处理指示书的完整自动化流程"""
        results = {
            'dnc_system': False,
            'daily_report': False,
            'inspection_system': False
        }
        
        # DNC系统处理
        try:
            results['dnc_system'] = self.dnc_automation.process_model(model_number, task_info)
        except Exception as e:
            self.logger.error(f"DNC系统处理失败: {e}")
            results['dnc_system'] = False
        
        # 日报系统处理
        try:
            if self.browser_automation.setup_driver():
                results['daily_report'] = self.browser_automation.input_instruction_to_daily_report(instruction_id)
                self.browser_automation.close_browser()
        except Exception as e:
            self.logger.error(f"日报系统处理失败: {e}")
            results['daily_report'] = False
        
        # 检验系统处理
        try:
            if self.browser_automation.setup_driver():
                results['inspection_system'] = self.browser_automation.input_instruction_to_inspection_system(instruction_id)
                self.browser_automation.close_browser()
        except Exception as e:
            self.logger.error(f"检验系统处理失败: {e}")
            results['inspection_system'] = False
        
        self.logger.info(f"指示书 {instruction_id} 自动化处理结果: {results}")
        return results
    
    def cleanup(self):
        """清理资源"""
        try:
            self.dnc_automation.close_dnc()
            self.browser_automation.close_browser()
        except Exception as e:
            self.logger.error(f"清理自动化资源失败: {e}")


class QRCodeScanner:
    """二维码扫描器模拟"""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def simulate_scan(self, qr_content: str) -> Dict[str, Any]:
        """模拟二维码扫描"""
        try:
            # 解析二维码内容
            parsed_data = self._parse_qr_content(qr_content)
            
            # 检查是否有错误
            if 'error' in parsed_data:
                self.logger.info(f"二维码解析失败: {parsed_data['error']}")
                return {
                    'success': False,
                    'error': parsed_data['error']
                }
            
            self.logger.info(f"模拟扫描二维码: {qr_content}")
            self.logger.info(f"解析结果: {parsed_data}")
            
            return {
                'success': True,
                'content': qr_content,
                'parsed_data': parsed_data,
                'timestamp': time.time()
            }
            
        except Exception as e:
            self.logger.error(f"二维码扫描模拟失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_qr_content(self, qr_content: str) -> Dict[str, str]:
        """解析二维码内容，添加严格验证"""
        if not qr_content or not qr_content.strip():
            return {'error': '二维码内容为空'}
        
        parsed = {}
        parts = qr_content.split('|')
        
        # 检查是否为键值对格式
        has_key_value_pairs = any(':' in part for part in parts)
        
        if has_key_value_pairs:
            # 键值对格式解析
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    parsed[key.strip().upper()] = value.strip()
            
            # 验证必需字段
            if not parsed.get('INSTRUCTION') and not parsed.get('INSTRUCTION_ID'):
                return {'error': '缺少必需的指示书编号字段'}
        else:
            # 纯文本格式，假设为指示书编号
            instruction_id = qr_content.strip()
            if instruction_id:
                # 更严格的指示书编号格式验证
                # 有效的指示书编号应该以INS、INS_、或类似的业务前缀开头
                if re.match(r'^(INS|INS_|INSTRUCTION_)[A-Z0-9_]+$', instruction_id, re.IGNORECASE):
                    parsed['INSTRUCTION_ID'] = instruction_id.upper()
                else:
                    return {'error': '指示书编号格式无效，应该以INS、INS_或INSTRUCTION_开头'}
            else:
                return {'error': '二维码内容格式无效'}
        
        # 验证数值字段
        if 'QUANTITY' in parsed:
            try:
                int(parsed['QUANTITY'])
            except ValueError:
                return {'error': '数量字段格式无效'}
        
        # 验证材料字段（如果存在）
        if 'MATERIAL' in parsed:
            if not parsed['MATERIAL']:
                return {'error': '材料字段不能为空'}
        
        # 验证型号字段（如果存在）
        if 'MODEL' in parsed:
            if not parsed['MODEL']:
                return {'error': '型号字段不能为空'}
        
        return parsed
    
    def batch_scan_simulation(self, qr_contents: List[str]) -> List[Dict[str, Any]]:
        """批量扫描模拟"""
        results = []
        for qr_content in qr_contents:
            result = self.simulate_scan(qr_content)
            results.append(result)
            time.sleep(0.5)  # 模拟扫描间隔
        
        self.logger.info(f"批量扫描完成，共处理 {len(results)} 个二维码")
        return results


class UIAutomation:
    """UI自动化适配器类，保持向后兼容性"""
    
    def __init__(self, config_manager):
        """
        初始化UI自动化适配器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config = config_manager.config
        self.automation_manager = AutomationManager(self.config)
        self.logger = logging.getLogger(__name__)
    
    def execute_operation(self, operation: str, **kwargs) -> Dict:
        """
        执行UI操作
        
        Args:
            operation: 操作类型
            **kwargs: 操作参数
            
        Returns:
            操作结果字典
        """
        try:
            if operation == "process_instruction":
                instruction_id = kwargs.get('instruction_id')
                model_number = kwargs.get('model_number')
                task_info = kwargs.get('task_info', None)  # 新增任务信息参数
                
                if instruction_id and model_number:
                    result = self.automation_manager.process_instruction(
                        instruction_id, model_number, task_info
                    )
                    return {
                        'success': True,
                        'result': result,
                        'message': f"指示书 {instruction_id} 处理完成"
                    }
                else:
                    return {
                        'success': False,
                        'error': '缺少必需的参数: instruction_id 或 model_number'
                    }
            
            elif operation == "scan_qr_code":
                qr_content = kwargs.get('qr_content')
                if qr_content:
                    qr_scanner = QRCodeScanner(self.config)
                    result = qr_scanner.simulate_scan(qr_content)
                    return {
                        'success': result['success'],
                        'result': result,
                        'message': '二维码扫描完成' if result['success'] else result['error']
                    }
                else:
                    return {
                        'success': False,
                        'error': '缺少二维码内容'
                    }
            
            else:
                return {
                    'success': False,
                    'error': f'不支持的操作类型: {operation}'
                }
                
        except Exception as e:
            self.logger.error(f"UI操作执行失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def connect_to_dnc(self) -> bool:
        """连接到DNC系统"""
        try:
            dnc_automation = DNCSystemAutomation(self.config)
            return dnc_automation.connect_to_dnc()
        except Exception as e:
            self.logger.error(f"连接DNC系统失败: {e}")
            return False
    
    def close_resources(self):
        """关闭所有资源"""
        try:
            self.automation_manager.cleanup()
        except Exception as e:
            self.logger.error(f"关闭资源失败: {e}")
