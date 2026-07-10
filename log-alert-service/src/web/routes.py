from flask import Blueprint, request, jsonify
from src.db.mysql import get_db_session
from src.db.cache import (
    set_device_status, get_device_status,
    increment_alarm_count, get_alarm_count
)
from src.models.alarm import AlarmRecord
from src.models.device import DeviceStatusHistory, OperationLog
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/devices', methods=['GET'])
def get_devices():
    """获取所有设备状态"""
    from src.config_manager import ConfigManager

    config_manager = ConfigManager('config.yaml')
    devices_config = config_manager.get('devices', [])
    devices = []

    for device in devices_config:
        device_name = device.get('name')
        status_data = get_device_status(device_name)

        devices.append({
            'name': device_name,
            'status': status_data.get('status', 'RUNNING'),
            'last_heartbeat': status_data.get('last_heartbeat'),
            'last_alarm_time': status_data.get('last_alarm_time'),
            'today_alarm_count': get_alarm_count(device_name),
            'enabled': device.get('enabled', True)
        })

    return jsonify({'devices': devices})

@api_bp.route('/devices/<device_name>/start', methods=['POST'])
def start_device(device_name):
    """启动设备监控"""
    data = request.get_json() or {}
    reason = data.get('reason', '手动启动')

    # 获取当前状态
    status_data = get_device_status(device_name)
    old_status = status_data.get('status', 'RUNNING')

    # 更新缓存状态
    set_device_status(device_name, 'RUNNING', changed_by='user', reason=reason)

    # 记录到MySQL
    session = get_db_session()
    try:
        history = DeviceStatusHistory(
            device_name=device_name,
            old_status=old_status,
            new_status='RUNNING',
            changed_by='user',
            reason=reason
        )
        session.add(history)
        session.commit()
    except Exception as e:
        logger.error(f"记录设备状态失败: {e}")
        session.rollback()
    finally:
        session.close()

    # 记录操作日志
    session = get_db_session()
    try:
        log = OperationLog(
            user_id='user',
            operation='START_DEVICE',
            target_device=device_name,
            details={'reason': reason}
        )
        session.add(log)
        session.commit()
    except Exception as e:
        logger.error(f"记录操作日志失败: {e}")
        session.rollback()
    finally:
        session.close()

    # 通过WebSocket推送
    push_device_status_change(device_name, old_status, 'RUNNING', 'user')

    return jsonify({'success': True, 'message': '设备监控已启动'})

@api_bp.route('/devices/<device_name>/pause', methods=['POST'])
def pause_device(device_name):
    """暂停设备监控"""
    data = request.get_json() or {}
    reason = data.get('reason', '手动暂停')

    # 获取当前状态
    status_data = get_device_status(device_name)
    old_status = status_data.get('status', 'RUNNING')

    # 更新缓存状态
    set_device_status(device_name, 'PAUSED', changed_by='user', reason=reason)

    # 记录到MySQL
    session = get_db_session()
    try:
        history = DeviceStatusHistory(
            device_name=device_name,
            old_status=old_status,
            new_status='PAUSED',
            changed_by='user',
            reason=reason
        )
        session.add(history)
        session.commit()
    except Exception as e:
        logger.error(f"记录设备状态失败: {e}")
        session.rollback()
    finally:
        session.close()

    # 记录操作日志
    session = get_db_session()
    try:
        log = OperationLog(
            user_id='user',
            operation='PAUSE_DEVICE',
            target_device=device_name,
            details={'reason': reason}
        )
        session.add(log)
        session.commit()
    except Exception as e:
        logger.error(f"记录操作日志失败: {e}")
        session.rollback()
    finally:
        session.close()

    # 通过WebSocket推送
    push_device_status_change(device_name, old_status, 'PAUSED', 'user')

    return jsonify({'success': True, 'message': '设备监控已暂停'})

@api_bp.route('/alarms', methods=['GET'])
def get_alarms():
    """获取告警列表"""
    device = request.args.get('device')
    level = request.args.get('level')
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))

    session = get_db_session()
    try:
        query = session.query(AlarmRecord)

        if device:
            query = query.filter(AlarmRecord.device_name == device)
        if level:
            query = query.filter(AlarmRecord.alarm_level == level)

        total = query.count()
        alarms = query.order_by(AlarmRecord.log_timestamp.desc()) \
                     .offset(offset).limit(limit).all()

        return jsonify({
            'total': total,
            'alarms': [alarm.to_dict() for alarm in alarms]
        })
    except Exception as e:
        logger.error(f"查询告警失败: {e}")
        return jsonify({'total': 0, 'alarms': [], 'error': str(e)}), 500
    finally:
        session.close()

@api_bp.route('/alarms/summary', methods=['GET'])
def get_alarm_summary():
    """获取告警统计汇总"""
    device = request.args.get('device')
    date_str = request.args.get('date')

    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # 解析日期范围
    try:
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    session = get_db_session()
    try:
        query = session.query(AlarmRecord).filter(
            AlarmRecord.log_timestamp >= start_date,
            AlarmRecord.log_timestamp < end_date
        )

        if device:
            query = query.filter(AlarmRecord.device_name == device)

        alarms = query.all()

        # 统计
        total = len(alarms)
        by_level = {}
        hour_counts = {}

        for alarm in alarms:
            level = alarm.alarm_level
            by_level[level] = by_level.get(level, 0) + 1

            hour = alarm.log_timestamp.hour
            hour_key = f"{hour:02d}:00-{hour:02d}:59"
            hour_counts[hour_key] = hour_counts.get(hour_key, 0) + 1

        # 找出峰值时段
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None

        return jsonify({
            'date': date_str,
            'device': device or '全部',
            'total': total,
            'by_level': by_level,
            'peak_hour': peak_hour
        })
    except Exception as e:
        logger.error(f"统计告警失败: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

def push_device_status_change(device_name, old_status, new_status, changed_by):
    """推送设备状态变更（WebSocket）"""
    try:
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
    except Exception as e:
        logger.error(f"WebSocket推送失败: {e}")
