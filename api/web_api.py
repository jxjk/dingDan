"""
Web API接口
提供RESTful API供前端和其他系统调用
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    Flask = None
    jsonify = None
    CORS = None

from config.config_manager import ConfigManager
from models.production_task import ProductionTask, TaskStatus, TaskPriority
from services.task_scheduler import TaskScheduler
from services.material_checker import MaterialMappingManager, EnhancedMaterialChecker
from services.ui_automation import AutomationManager, QRCodeScanner


class CNCWebAPI:
    """数控车床生产系统Web API"""
    
    def __init__(self, production_system):
        self.production_system = production_system
        self.config_manager = production_system.config_manager
        self.config = production_system.config
        self.logger = logging.getLogger(__name__)
        
        if Flask is None:
            raise ImportError("Flask未安装，无法启动Web API")
        
        self.app = Flask(__name__)
        CORS(self.app)  # 启用跨域请求
        
        self._setup_routes()
    
    def _setup_routes(self):
        """设置API路由"""
        
        # 系统状态
        @self.app.route('/api/system/status', methods=['GET'])
        def get_system_status():
            """获取系统状态"""
            try:
                status = self.production_system.get_system_status()
                return jsonify({
                    'success': True,
                    'data': status
                })
            except Exception as e:
                self.logger.error(f"获取系统状态失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # 任务管理
        @self.app.route('/api/tasks', methods=['GET'])
        def get_tasks():
            """获取所有任务"""
            try:
                pending_tasks = [task.to_dict() for task in self.production_system.task_scheduler.pending_tasks]
                running_tasks = [task.to_dict() for task in self.production_system.task_scheduler.running_tasks.values()]
                completed_tasks = [task.to_dict() for task in self.production_system.task_scheduler.completed_tasks]
                
                return jsonify({
                    'success': True,
                    'data': {
                        'pending': pending_tasks,
                        'running': running_tasks,
                        'completed': completed_tasks
                    }
                })
            except Exception as e:
                self.logger.error(f"获取任务列表失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/tasks', methods=['POST'])
        def create_task():
            """创建新任务"""
            try:
                data = request.get_json()
                
                required_fields = ['instruction_id', 'product_model', 'material_spec', 'order_quantity']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'success': False,
                            'error': f'缺少必需字段: {field}'
                        }), 400
                
                task_id = self.production_system.add_new_task(
                    instruction_id=data['instruction_id'],
                    product_model=data['product_model'],
                    material_spec=data['material_spec'],
                    order_quantity=data['order_quantity'],
                    priority=data.get('priority', 'Normal')
                )
                
                return jsonify({
                    'success': True,
                    'data': {
                        'task_id': task_id,
                        'message': '任务创建成功'
                    }
                })
                
            except Exception as e:
                self.logger.error(f"创建任务失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/tasks/<task_id>', methods=['GET'])
        def get_task(task_id):
            """获取任务详情"""
            try:
                task_details = self.production_system.get_task_details(task_id)
                if task_details:
                    return jsonify({
                        'success': True,
                        'data': task_details
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': '任务不存在'
                    }), 404
                    
            except Exception as e:
                self.logger.error(f"获取任务详情失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/tasks/<task_id>/pause', methods=['POST'])
        def pause_task(task_id):
            """暂停任务"""
            try:
                self.production_system.task_scheduler.pause_task(task_id)
                return jsonify({
                    'success': True,
                    'message': '任务已暂停'
                })
            except Exception as e:
                self.logger.error(f"暂停任务失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/tasks/<task_id>/resume', methods=['POST'])
        def resume_task(task_id):
            """恢复任务"""
            try:
                self.production_system.task_scheduler.resume_task(task_id)
                return jsonify({
                    'success': True,
                    'message': '任务已恢复'
                })
            except Exception as e:
                self.logger.error(f"恢复任务失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
        def cancel_task(task_id):
            """取消任务"""
            try:
                success = self.production_system.task_scheduler.remove_task(task_id)
                if success:
                    return jsonify({
                        'success': True,
                        'message': '任务已取消'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': '任务不存在或无法取消'
                    }), 404
                    
            except Exception as e:
                self.logger.error(f"取消任务失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # 机床管理
        @self.app.route('/api/machines', methods=['GET'])
        def get_machines():
            """获取机床列表"""
            try:
                available_machines = self.production_system.machine_monitor.get_available_machines()
                busy_machines = self.production_system.machine_monitor.get_busy_machines()
                
                machines = []
                for machine_id in set(available_machines + busy_machines):
                    machine_config = self.config_manager.get_machine_config(machine_id)
                    machines.append({
                        'machine_id': machine_id,
                        'status': 'available' if machine_id in available_machines else 'busy',
                        'material': machine_config['material'],
                        'capabilities': machine_config['capabilities'],
                        'ip_address': machine_config['ip_address']
                    })
                
                return jsonify({
                    'success': True,
                    'data': machines
                })
                
            except Exception as e:
                self.logger.error(f"获取机床列表失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/machines/<machine_id>/status', methods=['GET'])
        def get_machine_status(machine_id):
            """获取机床状态"""
            try:
                machine_state = self.production_system.task_scheduler.machine_states.get(machine_id)
                if machine_state:
                    return jsonify({
                        'success': True,
                        'data': {
                            'machine_id': machine_state.machine_id,
                            'current_state': machine_state.current_state,
                            'current_material': machine_state.current_material,
                            'current_task': machine_state.current_task,
                            'last_update': machine_state.last_update.isoformat(),
                            'is_available': machine_state.is_available
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': '机床不存在'
                    }), 404
                    
            except Exception as e:
                self.logger.error(f"获取机床状态失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # 材料管理
        @self.app.route('/api/materials/stock', methods=['GET'])
        def get_material_stock():
            """获取材料库存"""
            try:
                stock_report = self.production_system.get_material_stock_report()
                return jsonify({
                    'success': True,
                    'data': stock_report
                })
            except Exception as e:
                self.logger.error(f"获取材料库存失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/materials/check', methods=['POST'])
        def check_material_compatibility():
            """检查材料兼容性"""
            try:
                data = request.get_json()
                
                required_fields = ['material_spec', 'machine_id']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'success': False,
                            'error': f'缺少必需字段: {field}'
                        }), 400
                
                machine_state = self.production_system.task_scheduler.machine_states.get(data['machine_id'])
                if not machine_state:
                    return jsonify({
                        'success': False,
                        'error': '机床不存在'
                    }), 404
                
                # 创建临时任务进行材料检查
                temp_task = ProductionTask(
                    task_id='temp_check',
                    instruction_id='temp',
                    product_model='temp',
                    material_spec=data['material_spec'],
                    order_quantity=1
                )
                
                check_result = self.production_system.material_checker.check_material_compatibility(
                    temp_task, data['machine_id'], machine_state.current_material
                )
                
                return jsonify({
                    'success': True,
                    'data': {
                        'compatible': check_result.compatible,
                        'requires_change': check_result.requires_change,
                        'change_cost': check_result.change_cost,
                        'recommendation': check_result.recommendation
                    }
                })
                
            except Exception as e:
                self.logger.error(f"检查材料兼容性失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # 调度管理
        @self.app.route('/api/scheduling/strategy', methods=['GET'])
        def get_scheduling_strategy():
            """获取调度策略"""
            try:
                strategy = self.config_manager.get_scheduling_strategy()
                return jsonify({
                    'success': True,
                    'data': {
                        'current_strategy': strategy,
                        'available_strategies': ['material_first', 'priority_first', 'load_balance', 'efficiency']
                    }
                })
            except Exception as e:
                self.logger.error(f"获取调度策略失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/scheduling/strategy', methods=['POST'])
        def set_scheduling_strategy():
            """设置调度策略"""
            try:
                data = request.get_json()
                
                if 'strategy' not in data:
                    return jsonify({
                        'success': False,
                        'error': '缺少strategy字段'
                    }), 400
                
                available_strategies = ['material_first', 'priority_first', 'load_balance', 'efficiency']
                if data['strategy'] not in available_strategies:
                    return jsonify({
                        'success': False,
                        'error': f'无效的调度策略，可选值: {available_strategies}'
                    }), 400
                
                self.config_manager.set_scheduling_strategy(data['strategy'])
                self.production_system.task_scheduler.set_scheduling_strategy(data['strategy'])
                
                return jsonify({
                    'success': True,
                    'message': f'调度策略已设置为: {data["strategy"]}'
                })
                
            except Exception as e:
                self.logger.error(f"设置调度策略失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/scheduling/execute', methods=['POST'])
        def execute_scheduling():
            """手动执行调度"""
            try:
                assignments = self.production_system.task_scheduler.schedule_tasks()
                
                assignment_details = []
                for task, machine_id in assignments:
                    assignment_details.append({
                        'task_id': task.task_id,
                        'machine_id': machine_id,
                        'instruction_id': task.instruction_id,
                        'product_model': task.product_model
                    })
                
                return jsonify({
                    'success': True,
                    'data': {
                        'assignments': assignment_details,
                        'total_assigned': len(assignments)
                    }
                })
                
            except Exception as e:
                self.logger.error(f"执行调度失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # 二维码扫描
        @self.app.route('/api/qr/scan', methods=['POST'])
        def scan_qr_code():
            """扫描二维码"""
            try:
                data = request.get_json()
                
                if 'content' not in data:
                    return jsonify({
                        'success': False,
                        'error': '缺少content字段'
                    }), 400
                
                scan_result = self.production_system.scan_qr_code(data['content'])
                
                return jsonify({
                    'success': True,
                    'data': scan_result
                })
                
            except Exception as e:
                self.logger.error(f"扫描二维码失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # 系统控制
        @self.app.route('/api/system/start', methods=['POST'])
        def start_system():
            """启动系统"""
            try:
                if self.production_system.is_running:
                    return jsonify({
                        'success': False,
                        'error': '系统已在运行中'
                    }), 400
                
                self.production_system.start_system()
                
                return jsonify({
                    'success': True,
                    'message': '系统已启动'
                })
                
            except Exception as e:
                self.logger.error(f"启动系统失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/system/stop', methods=['POST'])
        def stop_system():
            """停止系统"""
            try:
                if not self.production_system.is_running:
                    return jsonify({
                        'success': False,
                        'error': '系统未在运行'
                    }), 400
                
                self.production_system.stop_system()
                
                return jsonify({
                    'success': True,
                    'message': '系统已停止'
                })
                
            except Exception as e:
                self.logger.error(f"停止系统失败: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # 健康检查
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                'success': True,
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'system_running': self.production_system.is_running
            })
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """运行Web API服务器"""
        self.logger.info(f"启动Web API服务器: {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


def create_api_server(production_system):
    """创建API服务器实例"""
    return CNCWebAPI(production_system)


if __name__ == '__main__':
    # 独立运行API服务器
    from main import CNCProductionSystem
    
    system = CNCProductionSystem()
    api_server = create_api_server(system)
    api_server.run(debug=True)
