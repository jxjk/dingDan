"""
材料检查器模块
负责材料兼容性和库存检查
"""

import logging
from typing import Dict, List, Optional, Tuple
from services.material_mapper import MaterialMapper


class MaterialChecker:
    """材料检查器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.material_mapper = MaterialMapper(config_manager)
        self.logger = logging.getLogger(__name__)
        
        # 加载材料映射表
        if not self.material_mapper.load_material_mapping():
            self.logger.error("材料映射表加载失败")
    
    def check_material_compatibility(self, material_spec: str, required_quantity: int) -> Dict:
        """检查材料兼容性和库存"""
        try:
            self.logger.info(f"检查材料兼容性: {material_spec}, 数量: {required_quantity}")
            
            # 查找材料信息
            material_info = self.material_mapper.get_material_by_name(material_spec)
            
            if not material_info:
                self.logger.warning(f"未找到材料: {material_spec}")
                return {
                    'compatible': False,
                    'available': False,
                    'available_stock': 0,
                    'required_quantity': required_quantity,
                    'material_found': False,
                    'message': f"材料 {material_spec} 未找到"
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
                'message': self._generate_stock_message(material_spec, available_stock, required_quantity)
            }
            
            self.logger.info(f"材料检查结果: 兼容={result['compatible']}, 可用={result['available']}")
            return result
            
        except Exception as e:
            self.logger.error(f"材料兼容性检查失败: {e}")
            return {
                'compatible': False,
                'available': False,
                'available_stock': 0,
                'required_quantity': required_quantity,
                'material_found': False,
                'message': f"检查失败: {str(e)}"
            }
    
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
