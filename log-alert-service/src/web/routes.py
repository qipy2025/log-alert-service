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

# 通知配置相关导入
from src.db.notification_config_db import get_notification_config, update_notification_config
from src.web.socketio import broadcast_config_update

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
        from src.web.socketio import broadcast_device_status_change
        broadcast_device_status_change(device_name, old_status, new_status, changed_by)
    except Exception as e:
        logger.error(f"WebSocket推送失败: {e}")


@api_bp.route('/notification-config', methods=['GET'])
def get_notification_config_api():
    """获取通知配置

    返回当前的通知配置，包括总开关状态和允许的告警级别
    """
    try:
        config = get_notification_config()
        if not config:
            # 返回默认配置
            return jsonify({
                'enabled': False,
                'allowed_levels': []
            })
        return jsonify({
            'enabled': config.enabled,
            'allowed_levels': config.allowed_levels
        })
    except Exception as e:
        logger.error(f"获取通知配置失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/notification-config', methods=['PUT'])
def update_notification_config_api():
    """更新通知配置

    Request Body:
        enabled: boolean - 是否启用通知
        allowed_levels: array of string - 允许的告警级别列表

    Returns:
        更新后的配置信息
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        enabled = data.get('enabled', False)
        allowed_levels = data.get('allowed_levels', [])

        # 验证 allowed_levels 必须是列表
        if not isinstance(allowed_levels, list):
            return jsonify({'error': 'allowed_levels must be an array'}), 400

        # 验证告警级别的有效性
        valid_levels = {'CRITICAL', 'WARNING', 'INFO'}
        for level in allowed_levels:
            if level not in valid_levels:
                return jsonify({'error': f'Invalid alarm level: {level}. Valid levels are: CRITICAL, WARNING, INFO'}), 400

        # 更新配置
        config = update_notification_config(enabled, allowed_levels)

        # 广播配置更新到所有 WebSocket 客户端
        broadcast_config_update({
            'enabled': config.enabled,
            'allowed_levels': config.allowed_levels
        })

        return jsonify({
            'success': True,
            'config': {
                'enabled': config.enabled,
                'allowed_levels': config.allowed_levels
            }
        })
    except Exception as e:
        logger.error(f"更新通知配置失败: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== 设备管理 API ====================

@api_bp.route('/devices/config', methods=['GET'])
def get_devices_config():
    """获取设备配置列表"""
    from src.device_manager import DeviceManager

    try:
        device_manager = DeviceManager()
        devices = device_manager.get_all_devices()
        return jsonify({'devices': devices})
    except Exception as e:
        logger.error(f"获取设备配置失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/devices', methods=['POST'])
def add_device():
    """添加新设备"""
    from src.device_manager import DeviceManager

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # 验证必填字段
        required_fields = ['device_name', 'log_path']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        device_name = data['device_name']
        log_path = data['log_path']
        enabled = data.get('enabled', True)

        # 添加设备
        device_manager = DeviceManager()
        device = device_manager.add_device({
            'device_name': device_name,
            'log_path': log_path,
            'enabled': enabled
        })

        return jsonify({
            'success': True,
            'device': device
        }), 201

    except ValueError as e:
        # 业务逻辑错误（如设备名称已存在）
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        logger.error(f"添加设备失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/devices/<device_name>', methods=['PUT'])
def update_device(device_name):
    """更新设备配置"""
    from src.device_manager import DeviceManager

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        device_manager = DeviceManager()
        device = device_manager.update_device(device_name, data)

        return jsonify({
            'success': True,
            'device': device
        })

    except ValueError as e:
        # 业务逻辑错误（如设备不存在）
        error_msg = str(e)
        if '设备不存在' in error_msg:
            return jsonify({'error': error_msg}), 404
        else:
            return jsonify({'error': error_msg}), 400
    except Exception as e:
        logger.error(f"更新设备失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/devices/<device_name>', methods=['DELETE'])
def delete_device(device_name):
    """删除设备"""
    from src.device_manager import DeviceManager

    try:
        device_manager = DeviceManager()
        device_manager.delete_device(device_name)

        return jsonify({
            'success': True,
            'message': '设备已删除'
        })

    except ValueError as e:
        # 设备不存在
        return jsonify({'error': str(e)}), 404
    except RuntimeError as e:
        # 设备正在运行
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        logger.error(f"删除设备失败: {e}")
        return jsonify({'error': str(e)}), 500
