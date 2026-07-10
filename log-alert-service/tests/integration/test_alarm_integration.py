import pytest
from datetime import datetime
from src.db.mysql import get_db_session
from src.db.cache import set_device_status, get_device_status
from src.models.alarm import AlarmRecord
from src.models import AlarmEvent, AlarmLevel
from src.models.device import DeviceStatusHistory, OperationLog
import logging

logger = logging.getLogger(__name__)

def test_device_status_control():
    """测试设备状态控制"""
    # 设置设备为运行状态
    set_device_status('测试设备', 'RUNNING')

    # 检查设备是否启用
    from src.file_watcher import check_device_enabled
    assert check_device_enabled('测试设备') == True

    # 暂停设备
    set_device_status('测试设备', 'PAUSED')

    # 检查设备是否暂停
    assert check_device_enabled('测试设备') == False

    # 恢复设备状态
    set_device_status('测试设备', 'RUNNING')
    print("✓ 设备状态控制测试通过")

def test_alarm_storage():
    """测试告警存储"""
    # 模拟告警事件
    alarm_event = AlarmEvent(
        timestamp=datetime.now(),
        alarm_text='温度过高测试',
        module_name='测试设备',
        level=AlarmLevel.CRITICAL,
        source=None,
        line_number=100,
        log_file='test.log',
        raw_line='test line'
    )

    # 存储告警
    from src.alarm_dedup import store_alarm_to_db
    store_alarm_to_db(alarm_event)

    # 验证存储成功
    session = get_db_session()
    try:
        alarm = session.query(AlarmRecord).filter_by(
            device_name='测试设备',
            alarm_level='CRITICAL'
        ).first()

        assert alarm is not None
        assert '温度过高' in alarm.alarm_content

        # 清理测试数据
        session.delete(alarm)
        session.commit()
        print("✓ 告警存储测试通过")
    finally:
        session.close()

def test_cache_operations():
    """测试缓存操作"""
    # 测试设备状态设置和获取
    set_device_status('缓存设备', 'RUNNING', changed_by='test', reason='测试')
    status = get_device_status('缓存设备')
    assert status['status'] == 'RUNNING'

    # 测试告警计数
    from src.db.cache import increment_alarm_count, get_alarm_count
    count = increment_alarm_count('缓存设备')
    assert count == 1

    retrieved_count = get_alarm_count('缓存设备')
    assert retrieved_count == 1

    # 清理
    from src.db.cache import get_cache_client
    cache = get_cache_client()
    cache.delete('缓存设备')
    cache.delete('device:alarm:count:缓存设备')
    print("✓ 缓存操作测试通过")
