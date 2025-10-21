"""
材料一致性检查服务
实现材料兼容性检查、库存管理和材料切换成本评估
"""

import pandas as pd
import logging
from typing import Dict, List, Optional
from pathlib import Path

from models.production_task import MaterialCheckResult, ProductionTask


class MaterialMappingManager:
    """材料映射管理器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.material_df = None
        self.material_mapping = {}
        self.load_material_mapping()
    
    def load_material_mapping(self):
        """加载材料映射表"""
        try:
            csv_path = self.config['material_mapping']['csv_path']
            if Path(csv_path).exists():
                # 读取CSV文件，跳过注释行
                self.material_df = pd.read_csv(csv_path, comment='#')
                self._build_material_mapping()
                self.logger.info(f"材料映射表已加载，共 {len(self.material_df)} 条记录")
            else:
                self.logger.warning(f"材料映射表文件不存在: {csv_path}")
                self.material_df = pd.DataFrame()
        except Exception as e:
            self.logger.error(f"加载材料映射表失败: {e}")
            self.material_df = pd.DataFrame()
    
    def _build_material_mapping(self):
        """构建材料映射字典"""
        if self.material_df is not None and not self.material_df.empty:
            for _, row in self.material_df.iterrows():
                qr_text = row['二维码文本']
                std_code = row['标准材料代码']
                material_name = row['材料名称']
                material_type = row['材料类型']
                stock_quantity = row['库存数量']
                
                self.material_mapping[qr_text] = {
                    'std_code': std_code,
                    'name': material_name,
                    'type': material_type,
                    'stock': stock_quantity
                }
    
    def get_material_info(self, qr_text: str) -> Optional[Dict]:
        """根据二维码文本获取材料信息"""
        return self.material_mapping.get(qr_text)
    
    def get_std_material_code(self, qr_text: str) -> Optional[str]:
        """获取标准材料代码"""
        info = self.get_material_info(qr_text)
        return info['std_code'] if info else None
    
    def get_material_stock(self, material_spec: str) -> int:
        """获取材料库存数量"""
        # 首先尝试直接匹配
        for qr_text, info in self.material_mapping.items():
            if info['std_code'] == material_spec:
                return info['stock']
        return 0
    
    def update_material_stock(self, material_spec: str, quantity: int):
        """更新材料库存"""
        for qr_text, info in self.material_mapping.items():
            if info['std_code'] == material_spec:
                info['stock'] = max(0, info['stock'] + quantity)
                self.logger.info(f"材料 {material_spec} 库存更新为: {info['stock']}")
                break
    
    def get_compatible_materials(self, material_type: str) -> List[str]:
        """获取兼容的材料列表"""
        compatible = []
        for qr_text, info in self.material_mapping.items():
            if info['type'] == material_type:
                compatible.append(info['std_code'])
        return compatible


class EnhancedMaterialChecker:
    """增强型材料检查器"""
    
    def __init__(self, config: dict, material_manager: MaterialMappingManager):
        self.config = config
        self.material_manager = material_manager
        self.logger = logging.getLogger(__name__)
        
        # 材料更换成本配置（分钟）
        self.material_change_costs = {
            'STEEL': {'STEEL': 0, 'ALUMINUM': 30, 'STAINLESS_STEEL': 45, 'COPPER': 60},
            'ALUMINUM': {'STEEL': 30, 'ALUMINUM': 0, 'STAINLESS_STEEL': 40, 'COPPER': 35},
            'STAINLESS_STEEL': {'STEEL': 45, 'ALUMINUM': 40, 'STAINLESS_STEEL': 0, 'COPPER': 50},
            'COPPER': {'STEEL': 60, 'ALUMINUM': 35, 'STAINLESS_STEEL': 50, 'COPPER': 0}
        }
    
    def check_material_compatibility(self, task: ProductionTask, machine_id: str, 
                                   machine_material: str) -> MaterialCheckResult:
        """检查材料兼容性"""
        self.logger.info(f"检查任务 {task.task_id} 材料兼容性: {task.material_spec} vs {machine_material}")
        
        # 基础材料匹配检查
        if task.material_spec == machine_material:
            return self._check_with_same_material(task, machine_material)
        else:
            return self._check_with_different_material(task, machine_material)
    
    def _check_with_same_material(self, task: ProductionTask, machine_material: str) -> MaterialCheckResult:
        """检查相同材料的情况"""
        # 材料库存检查
        inventory_check = self._check_material_inventory(task.material_spec, task.order_quantity)
        if not inventory_check.compatible:
            return MaterialCheckResult(
                compatible=False,
                message=f"材料库存不足: 需要{task.order_quantity}, 可用{inventory_check.available}"
            )
        
        return MaterialCheckResult(
            compatible=True,
            message=f"材料匹配，库存充足"
        )
    
    def _check_with_different_material(self, task: ProductionTask, machine_material: str) -> MaterialCheckResult:
        """检查不同材料的情况"""
        # 获取材料类型
        task_material_type = self._get_material_type(task.material_spec)
        machine_material_type = self._get_material_type(machine_material)
        
        if not task_material_type or not machine_material_type:
            return MaterialCheckResult(
                compatible=False,
                message="无法识别材料类型"
            )
        
        # 检查材料库存
        inventory_check = self._check_material_inventory(task.material_spec, task.order_quantity)
        if not inventory_check.sufficient:
            return MaterialCheckResult(
                compatible=False,
                message=f"材料库存不足: 需要{task.order_quantity}, 可用{inventory_check.available}"
            )
        
        # 计算材料更换成本
        change_cost = self._calculate_material_change_cost(machine_material_type, task_material_type)
        
        return MaterialCheckResult(
            compatible=True,
            requires_change=True,
            change_cost=change_cost,
            machine_material=machine_material,
            message=f"需要更换材料，预估耗时{change_cost}分钟"
        )
    
    def _check_material_inventory(self, material_spec: str, required_quantity: int) -> MaterialCheckResult:
        """检查材料库存"""
        available_stock = self.material_manager.get_material_stock(material_spec)
        
        if available_stock >= required_quantity:
            return MaterialCheckResult(
                compatible=True,
                available=available_stock,
                message=f"库存充足: {available_stock}"
            )
        else:
            return MaterialCheckResult(
                compatible=False,
                available=available_stock,
                message=f"库存不足: 需要{required_quantity}, 可用{available_stock}"
            )
    
    def _get_material_type(self, material_spec: str) -> Optional[str]:
        """获取材料类型"""
        for qr_text, info in self.material_manager.material_mapping.items():
            if info['std_code'] == material_spec:
                return info['type']
        return None
    
    def _calculate_material_change_cost(self, from_type: str, to_type: str) -> int:
        """计算材料更换成本"""
        return self.material_change_costs.get(from_type, {}).get(to_type, 60)
    
    def requires_material_change(self, current_material: str, target_material: str) -> bool:
        """判断是否需要更换材料"""
        return current_material != target_material
    
    def get_alternative_machines(self, task: ProductionTask, machines: Dict[str, str]) -> List[str]:
        """获取材料匹配的替代机床"""
        compatible_machines = []
        for machine_id, machine_material in machines.items():
            if task.material_spec == machine_material:
                compatible_machines.append(machine_id)
        return compatible_machines
    
    def validate_qr_material(self, qr_text: str, expected_material: str) -> bool:
        """验证二维码材料与预期材料是否匹配"""
        material_info = self.material_manager.get_material_info(qr_text)
        if not material_info:
            self.logger.warning(f"无法识别的二维码材料: {qr_text}")
            return False
        
        std_code = material_info['std_code']
        match = std_code == expected_material
        
        if not match:
            self.logger.warning(f"材料不匹配: 二维码材料={std_code}, 预期材料={expected_material}")
        
        return match


class MaterialInventoryManager:
    """材料库存管理器"""
    
    def __init__(self, material_manager: MaterialMappingManager):
        self.material_manager = material_manager
        self.logger = logging.getLogger(__name__)
    
    def consume_material(self, material_spec: str, quantity: int) -> bool:
        """消耗材料库存"""
        current_stock = self.material_manager.get_material_stock(material_spec)
        if current_stock >= quantity:
            self.material_manager.update_material_stock(material_spec, -quantity)
            self.logger.info(f"消耗材料 {material_spec}: {quantity}，剩余库存: {current_stock - quantity}")
            return True
        else:
            self.logger.error(f"材料 {material_spec} 库存不足: 需要{quantity}, 可用{current_stock}")
            return False
    
    def return_material(self, material_spec: str, quantity: int):
        """退回材料库存"""
        self.material_manager.update_material_stock(material_spec, quantity)
        self.logger.info(f"退回材料 {material_spec}: {quantity}")
    
    def get_low_stock_materials(self, threshold: int = 100) -> List[Dict]:
        """获取低库存材料列表"""
        low_stock_materials = []
        for qr_text, info in self.material_manager.material_mapping.items():
            if info['stock'] <= threshold:
                low_stock_materials.append({
                    'material': info['std_code'],
                    'name': info['name'],
                    'current_stock': info['stock'],
                    'threshold': threshold
                })
        return low_stock_materials
    
    def generate_stock_report(self) -> Dict:
        """生成库存报告"""
        report = {
            'total_materials': len(self.material_manager.material_mapping),
            'low_stock_count': 0,
            'out_of_stock_count': 0,
            'materials': []
        }
        
        for qr_text, info in self.material_manager.material_mapping.items():
            material_data = {
                'code': info['std_code'],
                'name': info['name'],
                'type': info['type'],
                'stock': info['stock'],
                'status': '充足'
            }
            
            if info['stock'] == 0:
                material_data['status'] = '缺货'
                report['out_of_stock_count'] += 1
            elif info['stock'] <= 50:
                material_data['status'] = '低库存'
                report['low_stock_count'] += 1
            
            report['materials'].append(material_data)
        
        return report
