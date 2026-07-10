from flask import request
from flask_socketio import emit, disconnect
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def register_socketio_events(socketio):
    """注册SocketIO事件处理器"""

    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        logger.info(f"客户端连接: {request.sid}")
        emit('connected', {'message': '连接成功'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开连接"""
        logger.info(f"客户端断开: {request.sid}")

    @socketio.on('ping')
    def handle_ping():
        """心跳测试"""
        emit('pong', {'timestamp': datetime.now().isoformat()})

    logger.info("SocketIO事件处理器注册完成")

def broadcast_alarm(alarm_data):
    """广播告警事件到所有连接的客户端"""
    try:
        from flask import current_app
        socketio = current_app.extensions.get('socketio')
        if socketio:
            socketio.emit('alarm', {
                'type': 'alarm',
                'data': alarm_data
            }, broadcast=True)
    except RuntimeError as e:
        # 当没有Flask应用上下文时，记录警告但不抛出异常
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"无法广播告警（Flask应用未运行）: {e}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"广播告警失败: {e}")

def broadcast_device_status_change(device_name, old_status, new_status, changed_by):
    """广播设备状态变更事件"""
    try:
        from flask import current_app
        socketio = current_app.extensions.get('socketio')
        if socketio:
            socketio.emit('device_status_changed', {
                'type': 'device_status_changed',
                'data': {
                    'device_name': device_name,
                    'old_status': old_status,
                    'new_status': new_status,
                    'changed_by': changed_by,
                    'timestamp': datetime.now().isoformat()
                }
            }, broadcast=True)
    except RuntimeError as e:
        # 当没有Flask应用上下文时，记录警告但不抛出异常
        logger.warning(f"无法广播状态变更（Flask应用未运行）: {e}")
    except Exception as e:
        logger.error(f"广播状态变更失败: {e}")


def broadcast_config_update(config):
    """广播通知配置更新事件

    当通知配置被更新时，向所有连接的 WebSocket 客户端广播更新

    Args:
        config: 配置字典，包含 'enabled' 和 'allowed_levels'
    """
    try:
        from flask import current_app
        socketio = current_app.extensions.get('socketio')
        if socketio:
            socketio.emit('notification_config_updated', {
                'type': 'notification_config_updated',
                'data': config
            }, broadcast=True)
            logger.info(f"通知配置更新已广播: enabled={config['enabled']}, levels={config['allowed_levels']}")
    except RuntimeError as e:
        # 当没有Flask应用上下文时，记录警告但不抛出异常
        logger.warning(f"无法广播配置更新（Flask应用未运行）: {e}")
    except Exception as e:
        logger.error(f"广播配置更新失败: {e}")
