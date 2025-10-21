"""
系统测试文件
包含完整的系统功能测试
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config_manager import ConfigManager
from models.production_task import ProductionTask, TaskStatus, TaskPriority
from services.material_checker import MaterialMappingManager, EnhancedMaterialChecker
from services.task_scheduler import TaskScheduler
from services.file_monitor import FileMonitorManager, MachineStateMonitor
from services.ui_automation import AutomationManager, QRCodeScanner


class TestConfigManager(unittest.TestCase):
    """配置管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_default_config_creation(self):
        """测试默认配置创建"""
        config_manager = ConfigManager(self.config_file)
        self.assertIsNotNone(config_manager.config)
        self.assertIn('system', config_manager.config)
        self.assertIn('logging', config_manager.config)
    
    def test_config_get_set(self):
        """测试配置获取和设置"""
        config_manager = ConfigManager(self.config_file)
        
        # 测试获取配置
        system_name = config_manager.get('system.name')
        self.assertEqual(system_name, '数控车床生产管理系统')
        
        # 测试设置配置
        config_manager.set('system.name', '测试系统')
        updated_name = config_manager.get('system.name')
        self.assertEqual(updated_name, '测试系统')
    
    def test_config_validation(self):
        """测试配置验证"""
        config_manager = ConfigManager(self.config_file)
        is_valid = config_manager.validate_config()
        self.assertTrue(is_valid)


class TestProductionTask(unittest.TestCase):
    """生产任务测试"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = ProductionTask(
            task_id='TEST001',
            instruction_id='INS001',
            product_model='MODEL_A',
            material_spec='STEEL_45',
            order_quantity=100
        )
        
        self.assertEqual(task.task_id, 'TEST001')
        self.assertEqual(task.instruction_id, 'INS001')
        self.assertEqual(task.product_model, 'MODEL_A')
        self.assertEqual(task.material_spec, 'STEEL_45')
        self.assertEqual(task.order_quantity, 100)
        self.assertEqual(task.status, TaskStatus.PENDING)
    
    def test_task_status_transitions(self):
        """测试任务状态转换"""
        task = ProductionTask(
            task_id='TEST002',
            instruction_id='INS002',
            product_model='MODEL_B',
            material_spec='ALUMINUM_6061',
            order_quantity=50
        )
        
        # 测试状态转换
        task.update_status(TaskStatus.RUNNING, "开始加工")
        self.assertEqual(task.status, TaskStatus.RUNNING)
        
        task.update_status(TaskStatus.COMPLETED, "加工完成")
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        
        task.update_status(TaskStatus.ERROR, "测试错误")
        self.assertEqual(task.status, TaskStatus.ERROR)
        self.assertEqual(task.error_message, "测试错误")
    
    def test_task_to_dict(self):
        """测试任务字典转换"""
        task = ProductionTask(
            task_id='TEST003',
            instruction_id='INS003',
            product_model='MODEL_C',
            material_spec='STAINLESS_STEEL_304',
            order_quantity=200,
            priority=TaskPriority.HIGH
        )
        
        task_dict = task.to_dict()
        
        self.assertEqual(task_dict['task_id'], 'TEST003')
        self.assertEqual(task_dict['instruction_id'], 'INS003')
        self.assertEqual(task_dict['product_model'], 'MODEL_C')
        self.assertEqual(task_dict['material_spec'], 'STAINLESS_STEEL_304')
        self.assertEqual(task_dict['order_quantity'], 200)
        self.assertEqual(task_dict['priority'], 'High')


class TestMaterialChecker(unittest.TestCase):
    """材料检查器测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时材料映射文件
        self.temp_dir = tempfile.mkdtemp()
        self.mapping_file = os.path.join(self.temp_dir, 'material_mapping.csv')
        
        # 写入测试数据
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            f.write("二维码文本,标准材料代码,材料名称,材料类型,库存数量\n")
            f.write("QRCODE_STEEL_45,STEEL_45,45号钢,STEEL,1000\n")
            f.write("QRCODE_ALUMINUM_6061,ALUMINUM_6061,6061铝合金,ALUMINUM,500\n")
            f.write("QRCODE_STAINLESS_STEEL_304,STAINLESS_STEEL_304,304不锈钢,STAINLESS_STEEL,300\n")
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_material_mapping(self):
        """测试材料映射"""
        # 创建模拟配置
        config = {
            'material_mapping': {
                'csv_path': self.mapping_file
            }
        }
        mapping_manager = MaterialMappingManager(config)
        
        # 测试材料信息获取
        info = mapping_manager.get_material_info('QRCODE_STEEL_45')
        self.assertIsNotNone(info)
        self.assertEqual(info['std_code'], 'STEEL_45')
        
        # 测试库存获取
        stock = mapping_manager.get_material_stock('STEEL_45')
        self.assertEqual(stock, 1000)
    
    def test_enhanced_material_checker(self):
        """测试增强材料检查器"""
        # 创建模拟配置
        config = {
            'material_mapping': {
                'csv_path': self.mapping_file
            }
        }
        material_manager = MaterialMappingManager(config)
        material_checker = EnhancedMaterialChecker(config, material_manager)
        
        # 创建测试任务
        task = ProductionTask(
            task_id='TEST004',
            instruction_id='INS004',
            product_model='MODEL_D',
            material_spec='STEEL_45',
            order_quantity=100
        )
        
        # 测试材料兼容性检查
        result = material_checker.check_material_compatibility(
            task, 'CNC001', 'STEEL_45'
        )
        
        self.assertTrue(result.compatible)


class TestTaskScheduler(unittest.TestCase):
    """任务调度器测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建模拟配置
        self.config = {
            'scheduling': {
                'default_strategy': 'priority_first'
            }
        }
        
        # 创建材料管理器
        self.temp_dir = tempfile.mkdtemp()
        self.mapping_file = os.path.join(self.temp_dir, 'material_mapping.csv')
        
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            f.write("二维码文本,标准材料代码,材料名称,材料类型,库存数量\n")
            f.write("QRCODE_STEEL_45,STEEL_45,45号钢,STEEL,1000\n")
        
        material_config = {
            'material_mapping': {
                'csv_path': self.mapping_file
            }
        }
        self.material_manager = MaterialMappingManager(material_config)
        self.material_checker = EnhancedMaterialChecker(material_config, self.material_manager)
        
        self.scheduler = TaskScheduler(self.config, self.material_checker)
        
        # 添加测试任务
        self.task1 = ProductionTask(
            task_id='TASK001',
            instruction_id='INS001',
            product_model='MODEL_A',
            material_spec='STEEL_45',
            order_quantity=100,
            priority=TaskPriority.NORMAL
        )
        
        self.task2 = ProductionTask(
            task_id='TASK002',
            instruction_id='INS002',
            product_model='MODEL_B',
            material_spec='STEEL_45',  # 使用相同材料以便测试
            order_quantity=50,
            priority=TaskPriority.HIGH
        )
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_task_addition(self):
        """测试任务添加"""
        self.scheduler.add_task(self.task1)
        self.scheduler.add_task(self.task2)
        
        self.assertEqual(len(self.scheduler.pending_tasks), 2)
        self.assertIn(self.task1, self.scheduler.pending_tasks)
        self.assertIn(self.task2, self.scheduler.pending_tasks)
    
    def test_task_removal(self):
        """测试任务移除"""
        self.scheduler.add_task(self.task1)
        self.scheduler.add_task(self.task2)
        
        success = self.scheduler.remove_task('TASK001')
        self.assertTrue(success)
        self.assertEqual(len(self.scheduler.pending_tasks), 1)
        self.assertNotIn(self.task1, self.scheduler.pending_tasks)
    
    def test_scheduling_strategies(self):
        """测试调度策略"""
        # 测试材料优先策略
        self.scheduler.set_scheduling_strategy('material_first')
        self.assertEqual(self.scheduler.current_strategy, 'material_first')
        
        # 测试优先级优先策略
        self.scheduler.set_scheduling_strategy('priority_first')
        self.assertEqual(self.scheduler.current_strategy, 'priority_first')


class TestQRCodeScanner(unittest.TestCase):
    """二维码扫描器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.config = {
            'qrcode': {
                'scan_timeout': 30,
                'retry_attempts': 3
            }
        }
    
    def test_qr_code_parsing(self):
        """测试二维码解析"""
        scanner = QRCodeScanner(self.config)
        
        # 测试标准格式
        qr_content = "INSTRUCTION:INS001|MODEL:MODEL_A|MATERIAL:STEEL_45|QUANTITY:100"
        # 使用正确的公共方法
        result = scanner.simulate_scan(qr_content)
        
        self.assertTrue(result['success'])
        parsed_data = result['parsed_data']
        self.assertEqual(parsed_data.get('INSTRUCTION'), 'INS001')
        self.assertEqual(parsed_data.get('MODEL'), 'MODEL_A')
        self.assertEqual(parsed_data.get('MATERIAL'), 'STEEL_45')
        self.assertEqual(int(parsed_data.get('QUANTITY', 0)), 100)
    
    def test_invalid_qr_code(self):
        """测试无效二维码"""
        scanner = QRCodeScanner(self.config)
        
        # 测试无效格式
        qr_content = "INVALID_FORMAT"
        result = scanner.simulate_scan(qr_content)
        
        self.assertFalse(result['success'])


class TestFileMonitor(unittest.TestCase):
    """文件监控测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.onoff_file = os.path.join(self.temp_dir, 'onoff.txt')
        self.macro_file = os.path.join(self.temp_dir, 'macro.txt')
        
        # 初始化监控管理器 - 使用正确的配置格式
        self.config = {
            'file_monitoring': {
                'onoff_file': self.onoff_file,
                'macro_file': self.macro_file,
                'poll_interval': 0.1
            }
        }
        
        self.monitor_manager = FileMonitorManager(self.config)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_file_monitor_manager_initialization(self):
        """测试文件监控管理器初始化"""
        # 检查配置是否正确加载
        self.assertEqual(self.monitor_manager.onoff_file_path, self.onoff_file)
        self.assertEqual(self.monitor_manager.macro_file_path, self.macro_file)
    
    def test_machine_state_monitor_initialization(self):
        """测试机器状态监控初始化"""
        state_monitor = MachineStateMonitor(self.monitor_manager)
        
        # 检查配置是否正确加载
        self.assertEqual(state_monitor.file_monitor.onoff_file_path, self.onoff_file)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_system_integration(self):
        """测试系统集成"""
        from main import CNCProductionSystem
        
        # 创建系统实例
        system = CNCProductionSystem()
        
        # 测试系统初始化
        self.assertIsNotNone(system.config_manager)
        self.assertIsNotNone(system.task_scheduler)
        self.assertIsNotNone(system.material_checker)
        
        # 测试任务添加
        task_id = system.add_new_task(
            instruction_id="INTEGRATION_TEST",
            product_model="TEST_MODEL",
            material_spec="STEEL_45",
            order_quantity=10
        )
        
        self.assertIsNotNone(task_id)
        
        # 测试系统状态获取
        status = system.get_system_status()
        # 更新断言以匹配实际返回的数据结构
        self.assertIn('task_statistics', status)
        task_stats = status['task_statistics']
        self.assertIn('total', task_stats)
        self.assertIn('pending', task_stats)
        self.assertIn('running', task_stats)
        
        # 测试材料库存报告
        stock_report = system.get_material_stock_report()
        self.assertIsInstance(stock_report, dict)


def run_all_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestProductionTask))
    suite.addTests(loader.loadTestsFromTestCase(TestMaterialChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskScheduler))
    suite.addTests(loader.loadTestsFromTestCase(TestQRCodeScanner))
    suite.addTests(loader.loadTestsFromTestCase(TestFileMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("开始运行数控车床生产管理系统测试...")
    print("=" * 60)
    
    success = run_all_tests()
    
    print("=" * 60)
    if success:
        print("所有测试通过！系统功能正常。")
    else:
        print("部分测试失败，请检查系统功能。")
    
    sys.exit(0 if success else 1)