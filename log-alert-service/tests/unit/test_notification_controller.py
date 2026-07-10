"""通知控制器测试"""
import pytest
from datetime import datetime
from src.notification_controller import NotificationController
from src.db.device_config import DeviceConfig
from src.db.mysql import get_db_session
from src.models.alarm import AlarmRecord


@pytest.fixture
def setup_data():
    """准备测试数据"""
    # 清理
    session = get_db_session()
    session.query(AlarmRecord).filter_by(device_name="通知测试设备").delete()
    DeviceConfig.delete("通知测试设备")

    # 创建设备配置
    DeviceConfig.create(device_name="通知测试设备", log_path="路径\\")

    # 创建告警记录
    alarm = AlarmRecord(
        device_name="通知测试设备",
        alarm_level="CRITICAL",
        alarm_content="测试告警",
        log_timestamp=datetime.now(),
        notified=False
    )
    session.add(alarm)
    session.commit()

    yield {"alarm_id": alarm.id}

    # 清理
    session.query(AlarmRecord).filter_by(device_name="通知测试设备").delete()
    DeviceConfig.delete("通知测试设备")
    session.commit()
    session.close()


def test_send_notification_success(setup_data, mocker):
    """测试成功发送通知"""
    # Mock 飞书通知器
    mock_notifier = mocker.patch('src.notification_controller.FeishuNotifier')
    mock_notifier.return_value.send_alarm.return_value = True

    controller = NotificationController()
    alarm_id = setup_data["alarm_id"]

    result = controller.send_alarm_notification(alarm_id)

    assert result["success"] is True
    assert "sent_at" in result

    # 验证告警被标记为已发送
    session = get_db_session()
    alarm = session.query(AlarmRecord).filter_by(id=alarm_id).first()
    assert alarm.notified is True
    session.close()


def test_send_notification_already_sent(setup_data):
    """测试重复发送通知"""
    controller = NotificationController()
    alarm_id = setup_data["alarm_id"]

    # 第一次发送（先mock）
    import unittest.mock
    with unittest.mock.patch('src.notification_controller.FeishuNotifier') as mock_notifier:
        mock_notifier.return_value.send_alarm.return_value = True
        controller.send_alarm_notification(alarm_id)

    # 第二次发送应该失败
    with pytest.raises(ValueError, match="通知已发送"):
        controller.send_alarm_notification(alarm_id)


def test_send_notification_alarm_not_found():
    """测试发送不存在的告警"""
    controller = NotificationController()

    with pytest.raises(ValueError, match="告警记录不存在"):
        controller.send_alarm_notification(99999)
