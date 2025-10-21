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
    
    def process_model(self, model_number: str) -> bool:
        """处理型号的完整流程"""
        if not self.connect_to_dnc():
            return False
        
        if not self.input_model_number(model_number):
            return False
        
        if not self.submit_model():
            return False
        
        # 等待处理完成
        time.sleep(2)
        self.logger.info(f"型号 {model_number} 处理完成")
        return True
    
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
        
    def process_instruction(self, instruction_id: str, model_number: str) -> Dict[str, bool]:
        """处理指示书的完整自动化流程"""
        results = {
            'dnc_system': False,
            'daily_report': False,
            'inspection_system': False
        }
        
        # DNC系统处理
        try:
            results['dnc_system'] = self.dnc_automation.process_model(model_number)
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
