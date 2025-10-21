"""
材料映射表管理器
负责材料映射表的加载、验证和修复
"""

import pandas as pd
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging


class MaterialMapper:
    """材料映射表管理器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.material_mapping: pd.DataFrame = None
        self.mapping_file_path = self.config_manager.get_material_mapping_path()
        self.logger = logging.getLogger(__name__)
    
    def load_material_mapping(self) -> bool:
        """加载材料映射表"""
        try:
            mapping_path = Path(self.mapping_file_path)
            
            if not mapping_path.exists():
                self.logger.warning(f"材料映射表文件不存在: {mapping_path}")
                return self._create_default_material_mapping()
            
            # 尝试读取CSV文件
            try:
                self.material_mapping = pd.read_csv(mapping_path, encoding='utf-8')
            except UnicodeDecodeError:
                # 尝试其他编码
                self.material_mapping = pd.read_csv(mapping_path, encoding='gbk')
            
            # 验证数据格式
            if not self._validate_mapping_format():
                self.logger.error("材料映射表格式不正确")
                return False
            
            self.logger.info(f"材料映射表加载成功，共 {len(self.material_mapping)} 条记录")
            return True
            
        except Exception as e:
            self.logger.error(f"加载材料映射表失败: {e}")
            return False
    
    def _validate_mapping_format(self) -> bool:
        """验证映射表格式"""
        if self.material_mapping is None or self.material_mapping.empty:
            return False
        
        required_columns = ['二维码文本', '材料名称', '材料规格', '库存数量']
        missing_columns = [col for col in required_columns if col not in self.material_mapping.columns]
        
        if missing_columns:
            self.logger.error(f"材料映射表缺少必需列: {missing_columns}")
            return False
        
        # 检查重复的二维码文本
        duplicates = self.material_mapping['二维码文本'].duplicated()
        if duplicates.any():
            self.logger.warning(f"发现重复的二维码文本: {self.material_mapping[duplicates]['二维码文本'].tolist()}")
        
        return True
    
    def _create_default_material_mapping(self) -> bool:
        """创建默认材料映射表"""
        try:
            default_data = {
                '二维码文本': ['MAT_S45C_001', 'MAT_AL6061_001', 'MAT_SS304_001', 'MAT_BRASS_001'],
                '材料名称': ['S45C', 'AL6061', 'SS304', '黄铜'],
                '材料规格': ['S45C-Φ50', 'AL6061-T6', 'SS304-L', '黄铜-H62'],
                '库存数量': [100, 50, 80, 30],
                '单位': ['kg', 'kg', 'kg', 'kg'],
                '供应商': ['默认供应商A', '默认供应商B', '默认供应商C', '默认供应商D'],
                '备注': ['常用碳钢', '铝合金', '不锈钢', '铜合金']
            }
            
            self.material_mapping = pd.DataFrame(default_data)
            
            # 确保目录存在
            mapping_path = Path(self.mapping_file_path)
            mapping_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存默认映射表
            self.material_mapping.to_csv(mapping_path, index=False, encoding='utf-8')
            
            self.logger.info(f"已创建默认材料映射表: {mapping_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建默认材料映射表失败: {e}")
            return False
    
    def get_material_by_qr(self, qr_text: str) -> Optional[Dict]:
        """根据二维码文本获取材料信息"""
        if self.material_mapping is None:
            self.logger.error("材料映射表未加载")
            return None
        
        try:
            match = self.material_mapping[self.material_mapping['二维码文本'] == qr_text]
            
            if match.empty:
                self.logger.warning(f"未找到匹配的材料: {qr_text}")
                return None
            
            material = match.iloc[0].to_dict()
            self.logger.info(f"找到材料: {material['材料名称']} ({material['材料规格']})")
            return material
            
        except Exception as e:
            self.logger.error(f"获取材料信息失败: {e}")
            return None
    
    def get_material_by_name(self, material_name: str) -> Optional[Dict]:
        """根据材料名称获取材料信息"""
        if self.material_mapping is None:
            self.logger.error("材料映射表未加载")
            return None
        
        try:
            # 首先在材料名称列中搜索
            match = self.material_mapping[self.material_mapping['材料名称'] == material_name]
            
            if match.empty:
                # 如果在材料名称列中没找到，尝试在材料规格列中搜索
                match = self.material_mapping[self.material_mapping['材料规格'] == material_name]
            
            if match.empty:
                self.logger.warning(f"未找到匹配的材料: {material_name}")
                return None
            
            material = match.iloc[0].to_dict()
            return material
            
        except Exception as e:
            self.logger.error(f"获取材料信息失败: {e}")
            return None
    
    def update_material_stock(self, qr_text: str, new_stock: int) -> bool:
        """更新材料库存"""
        if self.material_mapping is None:
            self.logger.error("材料映射表未加载")
            return False
        
        try:
            # 查找匹配的记录
            mask = self.material_mapping['二维码文本'] == qr_text
            
            if not mask.any():
                self.logger.error(f"未找到材料: {qr_text}")
                return False
            
            # 更新库存
            old_stock = self.material_mapping.loc[mask, '库存数量'].iloc[0]
            self.material_mapping.loc[mask, '库存数量'] = new_stock
            
            # 保存更改
            mapping_path = Path(self.mapping_file_path)
            self.material_mapping.to_csv(mapping_path, index=False, encoding='utf-8')
            
            self.logger.info(f"材料库存更新: {qr_text} {old_stock} -> {new_stock}")
            return True
            
        except Exception as e:
            self.logger.error(f"更新材料库存失败: {e}")
            return False
    
    def add_material(self, material_data: Dict) -> bool:
        """添加新材料"""
        if self.material_mapping is None:
            self.logger.error("材料映射表未加载")
            return False
        
        try:
            # 检查二维码文本是否已存在
            if material_data['二维码文本'] in self.material_mapping['二维码文本'].values:
                self.logger.error(f"材料已存在: {material_data['二维码文本']}")
                return False
            
            # 添加新行
            new_row = pd.DataFrame([material_data])
            self.material_mapping = pd.concat([self.material_mapping, new_row], ignore_index=True)
            
            # 保存更改
            mapping_path = Path(self.mapping_file_path)
            self.material_mapping.to_csv(mapping_path, index=False, encoding='utf-8')
            
            self.logger.info(f"新材料添加成功: {material_data['材料名称']}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加材料失败: {e}")
            return False
    
    def get_all_materials(self) -> List[Dict]:
        """获取所有材料信息"""
        if self.material_mapping is None:
            return []
        
        return self.material_mapping.to_dict('records')
    
    def get_low_stock_materials(self) -> List[Dict]:
        """获取低库存材料"""
        if self.material_mapping is None:
            return []
        
        low_threshold = self.config_manager.get_low_stock_threshold()
        critical_threshold = self.config_manager.get_critical_stock_threshold()
        
        low_stock = self.material_mapping[
            self.material_mapping['库存数量'] <= low_threshold
        ]
        
        # 添加库存状态
        materials = low_stock.to_dict('records')
        for material in materials:
            stock = material['库存数量']
            if stock <= critical_threshold:
                material['stock_status'] = 'critical'
            else:
                material['stock_status'] = 'low'
        
        return materials
    
    def get_material_statistics(self) -> Dict:
        """获取材料统计信息"""
        if self.material_mapping is None:
            return {
                'total_materials': 0,
                'total_stock': 0,
                'low_stock_count': 0,
                'critical_stock_count': 0,
                'out_of_stock_count': 0
            }
        
        low_threshold = self.config_manager.get_low_stock_threshold()
        critical_threshold = self.config_manager.get_critical_stock_threshold()
        
        total_materials = len(self.material_mapping)
        total_stock = self.material_mapping['库存数量'].sum()
        low_stock_count = len(self.material_mapping[self.material_mapping['库存数量'] <= low_threshold])
        critical_stock_count = len(self.material_mapping[self.material_mapping['库存数量'] <= critical_threshold])
        out_of_stock_count = len(self.material_mapping[self.material_mapping['库存数量'] <= 0])
        
        return {
            'total_materials': total_materials,
            'total_stock': total_stock,
            'low_stock_count': low_stock_count,
            'critical_stock_count': critical_stock_count,
            'out_of_stock_count': out_of_stock_count
        }
    
    def search_materials(self, search_term: str) -> List[Dict]:
        """搜索材料"""
        if self.material_mapping is None:
            return []
        
        try:
            # 在多个列中搜索
            mask = (
                self.material_mapping['二维码文本'].str.contains(search_term, case=False, na=False) |
                self.material_mapping['材料名称'].str.contains(search_term, case=False, na=False) |
                self.material_mapping['材料规格'].str.contains(search_term, case=False, na=False) |
                self.material_mapping['供应商'].str.contains(search_term, case=False, na=False)
            )
            
            results = self.material_mapping[mask].to_dict('records')
            return results
            
        except Exception as e:
            self.logger.error(f"搜索材料失败: {e}")
            return []
