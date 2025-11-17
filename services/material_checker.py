"""
材料检查服务
提供材料兼容性检查和材料库存管理功能
"""

import logging
import time
from typing import Dict, List, Any, Tuple
from models.production_task import ProductionTask
from services.material_mapper import MaterialMapper
from config.config_manager import get_config_manager


class MaterialChecker:
    """材料检查器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.material_mapper = MaterialMapper(config_manager)
        self.logger = logging.getLogger(__name__)
        
        # 加载材料映射表
        if not self.material_mapper.load_material_mapping():
            self.logger.error("材料映射表加载失败")
    
    def check_material_compatibility(self, task: ProductionTask, 
                                   machine_id: str, current_material: str) -> Dict:
        """检查材料兼容性"""
        self.logger.debug(f"检查材料兼容性: 任务={task.task_id}, 机床={machine_id}, 当前材料='{current_material}', 任务材料={task.material_spec}")
        
        # 检查材料是否匹配
        requires_change = current_material != task.material_spec
        self.logger.debug(f"是否需要更换材料: {requires_change}")
        
        # 计算更换成本（如果需要）
        change_cost = 0
        if requires_change:
            change_cost = self._calculate_change_cost(current_material, task.material_spec)
            self.logger.debug(f"材料更换成本: {change_cost}")
        
        # 判断是否兼容 - 总是返回True，但会在调度时考虑更换成本
        compatible = True
        self.logger.debug(f"材料兼容性检查结果: {compatible}")
        
        result = {
            'compatible': compatible,
            'requires_change': requires_change,
            'change_cost': change_cost,
            'current_material': current_material,
            'task_material': task.material_spec
        }
        
        self.logger.info(f"材料兼容性检查结果: {result}")
        return result
    
    def _generate_stock_message(self, material_spec: str, available: int, required: int) -> str:
        """生成库存消息"""
        if available >= required:
            return f"材料 {material_spec} 库存充足: {available}/{required}"
        else:
            return f"材料 {material_spec} 库存不足: 需要{required}, 可用{available}"
    
    def check_qr_material(self, qr_text: str, required_quantity: int) -> Dict:
        """根据二维码检查材料"""
        try:
            self.logger.info(f"检查二维码材料: {qr_text}, 数量: {required_quantity}")
            
            # 根据二维码获取材料信息
            material_info = self.material_mapper.get_material_by_qr(qr_text)
            
            if not material_info:
                self.logger.warning(f"未找到二维码对应的材料: {qr_text}")
                return {
                    'compatible': False,
                    'available': False,
                    'available_stock': 0,
                    'required_quantity': required_quantity,
                    'material_found': False,
                    'message': f"二维码 {qr_text} 未找到对应材料"
                }
            
            # 检查库存
            available_stock = material_info['库存数量']
            has_sufficient_stock = available_stock >= required_quantity
            
            result = {
                'compatible': True,
                'available': has_sufficient_stock,
                'available_stock': available_stock,
                'required_quantity': required_quantity,
                'material_found': True,
                'material_info': material_info,
                'message': self._generate_stock_message(material_info['材料名称'], available_stock, required_quantity)
            }
            
            self.logger.info(f"二维码材料检查结果: 兼容={result['compatible']}, 可用={result['available']}")
            return result
            
        except Exception as e:
            self.logger.error(f"二维码材料检查失败: {e}")
            return {
                'compatible': False,
                'available': False,
                'available_stock': 0,
                'required_quantity': required_quantity,
                'material_found': False,
                'message': f"二维码检查失败: {str(e)}"
            }
    
    def update_material_stock(self, material_spec: str, consumed_quantity: int) -> bool:
        """更新材料库存"""
        try:
            self.logger.info(f"更新材料库存: {material_spec}, 消耗: {consumed_quantity}")
            
            # 查找材料信息
            material_info = self.material_mapper.get_material_by_name(material_spec)
            
            if not material_info:
                self.logger.error(f"未找到材料: {material_spec}")
                return False
            
            # 计算新库存
            current_stock = material_info['库存数量']
            new_stock = current_stock - consumed_quantity
            
            if new_stock < 0:
                self.logger.warning(f"库存不足: {material_spec} 当前{current_stock}, 消耗{consumed_quantity}")
                new_stock = 0
            
            # 更新库存
            success = self.material_mapper.update_material_stock(
                material_info['二维码文本'], 
                new_stock
            )
            
            if success:
                self.logger.info(f"材料库存更新成功: {material_spec} {current_stock} -> {new_stock}")
            else:
                self.logger.error(f"材料库存更新失败: {material_spec}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"更新材料库存失败: {e}")
            return False
    
    def get_material_stock_report(self) -> Dict:
        """获取材料库存报告"""
        try:
            stats = self.material_mapper.get_material_statistics()
            
            # 获取低库存材料
            low_stock_materials = self.material_mapper.get_low_stock_materials()
            
            report = {
                'total_materials': stats['total_materials'],
                'total_stock': stats['total_stock'],
                'low_stock_count': stats['low_stock_count'],
                'critical_stock_count': stats['critical_stock_count'],
                'out_of_stock_count': stats['out_of_stock_count'],
                'low_stock_materials': low_stock_materials,
                'status': 'healthy' if stats['critical_stock_count'] == 0 else 'warning'
            }
            
            self.logger.info(f"材料库存报告: 总计{stats['total_materials']}种材料, 低库存{stats['low_stock_count']}种")
            return report
            
        except Exception as e:
            self.logger.error(f"获取材料库存报告失败: {e}")
            return {
                'total_materials': 0,
                'total_stock': 0,
                'low_stock_count': 0,
                'critical_stock_count': 0,
                'out_of_stock_count': 0,
                'low_stock_materials': [],
                'status': 'error'
            }
    
    def search_materials(self, search_term: str) -> List[Dict]:
        """搜索材料"""
        try:
            results = self.material_mapper.search_materials(search_term)
            self.logger.info(f"材料搜索: '{search_term}' 找到 {len(results)} 个结果")
            return results
        except Exception as e:
            self.logger.error(f"材料搜索失败: {e}")
            return []
    
    def add_new_material(self, material_data: Dict) -> bool:
        """添加新材料"""
        try:
            # 验证必需字段
            required_fields = ['二维码文本', '材料名称', '材料规格', '库存数量']
            for field in required_fields:
                if field not in material_data:
                    self.logger.error(f"缺少必需字段: {field}")
                    return False
            
            success = self.material_mapper.add_material(material_data)
            
            if success:
                self.logger.info(f"新材料添加成功: {material_data['材料名称']}")
            else:
                self.logger.error(f"新材料添加失败: {material_data['材料名称']}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"添加新材料失败: {e}")
            return False
    
    def get_all_materials(self) -> List[Dict]:
        """获取所有材料"""
        try:
            materials = self.material_mapper.get_all_materials()
            self.logger.info(f"获取所有材料: 共 {len(materials)} 种")
            return materials
        except Exception as e:
            self.logger.error(f"获取所有材料失败: {e}")
            return []
    
    def _is_material_compatible(self, current_material: str, task_material: str) -> bool:
        """
        检查材料是否兼容
        
        Args:
            current_material: 当前机床材料
            task_material: 任务所需材料
            
        Returns:
            bool: 材料是否兼容
        """
        # 处理空字符串的情况 - 允许添加任务，但会在调度时考虑更换成本
        if not current_material:
            self.logger.debug("当前机床材料为空，返回兼容")
            return True
            
        # 材料相同则兼容
        if current_material == task_material:
            self.logger.debug(f"材料相同，兼容: {current_material} == {task_material}")
            return True
            
        # 对于不同的材料，也认为是兼容的，但需要更换材料
        # 实际的兼容性将在调度时通过更换成本来体现
        self.logger.debug(f"材料不同但兼容: {current_material} != {task_material}，需要更换")
        return True
    
    def _calculate_change_cost(self, current_material: str, task_material: str) -> int:
        """
        计算材料更换成本（以分钟为单位）
        
        Args:
            current_material: 当前机床材料
            task_material: 任务所需材料
            
        Returns:
            int: 更换成本（分钟）
        """
        # 如果材料相同或当前材料为空，则无需更换，成本为0
        if current_material == task_material or not current_material:
            return 0
        
        # 获取材料信息
        current_mat_info = self.material_mapper.get_material_by_name(current_material)
        task_mat_info = self.material_mapper.get_material_by_name(task_material)
        
        # 默认更换成本为10分钟
        base_cost = 10
        
        # 如果能获取到材料信息，可以根据材料类型计算更精确的成本
        if current_mat_info and task_mat_info:
            # 示例：根据材料类型差异增加成本
            # 这里只是一个简单的示例实现，实际情况可能会更加复杂
            current_type = current_mat_info.get('材料规格', '').split('-')[0] if '-' in current_mat_info.get('材料规格', '') else ''
            task_type = task_mat_info.get('材料规格', '').split('-')[0] if '-' in task_mat_info.get('材料规格', '') else ''
            
            # 如果材料类型不同，增加更换成本
            if current_type != task_type:
                base_cost += 5
        
        return base_cost
