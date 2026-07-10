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
    from src.web.app import current_app
    socketio = current_app.extensions.get('socketio')
    if socketio:
        socketio.emit('alarm', {
            'type': 'alarm',
            'data': alarm_data
        }, broadcast=True)

def broadcast_device_status_change(device_name, old_status, new_status, changed_by):
    """广播设备状态变更事件"""
    from src.web.app import current_app
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
