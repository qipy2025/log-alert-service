"""测试 DeviceMonitorInfo 设备监控信息类"""
import pytest
import threading
from unittest.mock import MagicMock
from datetime import datetime


@pytest.fixture(autouse=True)
def cleanup_threads():
    """清理测试中创建的线程"""
    yield
    # 清理所有遗留的守护线程
    for thread in threading.enumerate():
        if thread.name.startswith('DeviceMonitor-'):
            # 等待线程结束
            thread.join(timeout=1.0)


class TestDeviceMonitorInfo:
    def test_device_monitor_info_creation(self):
        """测试创建 DeviceMonitorInfo"""
        from src.device_monitor_info import DeviceMonitorInfo

        # 创建模拟的 LogWatcher
        mock_watcher = MagicMock()

        # 创建设备配置
        device_config = {
            "device_name": "测试设备",
            "log_path": "测试路径\\日志\\",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        }

        # 创建 DeviceMonitorInfo
        monitor_info = DeviceMonitorInfo(device_config, mock_watcher)

        # 验证属性
        assert monitor_info.device_config == device_config
        assert monitor_info.watcher == mock_watcher
        assert monitor_info.is_running is False
        assert monitor_info.thread is None
        assert monitor_info.last_heartbeat is None
        assert monitor_info.alarm_count == 0

    def test_device_monitor_info_start(self):
        """测试启动设备监控"""
        from src.device_monitor_info import DeviceMonitorInfo

        # 创建模拟的 LogWatcher
        mock_watcher = MagicMock()

        device_config = {
            "device_name": "测试设备",
            "log_path": "测试路径\\日志\\",
            "enabled": True
        }

        monitor_info = DeviceMonitorInfo(device_config, mock_watcher)

        # 启动监控
        monitor_info.start()

        # 验证状态
        assert monitor_info.is_running is True
        assert monitor_info.thread is not None
        assert monitor_info.last_heartbeat is not None
        assert isinstance(monitor_info.thread, threading.Thread)

        # 验证 watcher 被启动
        mock_watcher.start.assert_called_once()

    def test_device_monitor_info_stop(self):
        """测试停止设备监控"""
        from src.device_monitor_info import DeviceMonitorInfo

        # 创建模拟的 LogWatcher
        mock_watcher = MagicMock()

        device_config = {
            "device_name": "测试设备",
            "log_path": "测试路径\\日志\\",
            "enabled": True
        }

        monitor_info = DeviceMonitorInfo(device_config, mock_watcher)

        # 先启动
        monitor_info.start()
        assert monitor_info.is_running is True

        # 再停止
        monitor_info.stop()

        # 验证状态
        assert monitor_info.is_running is False
        assert monitor_info.thread is None

        # 验证 watcher 被停止
        mock_watcher.stop.assert_called_once()

    def test_device_monitor_info_increment_alarm(self):
        """测试告警计数"""
        from src.device_monitor_info import DeviceMonitorInfo

        mock_watcher = MagicMock()
        device_config = {"device_name": "测试设备", "log_path": "路径\\"}

        monitor_info = DeviceMonitorInfo(device_config, mock_watcher)

        # 初始计数为 0
        assert monitor_info.alarm_count == 0

        # 增加告警计数
        monitor_info.increment_alarm_count()
        assert monitor_info.alarm_count == 1

        monitor_info.increment_alarm_count()
        assert monitor_info.alarm_count == 2

        # 重置计数
        monitor_info.reset_alarm_count()
        assert monitor_info.alarm_count == 0

    def test_device_monitor_info_status(self):
        """测试获取设备状态"""
        from src.device_monitor_info import DeviceMonitorInfo

        mock_watcher = MagicMock()
        device_config = {
            "device_name": "测试设备",
            "log_path": "路径\\",
            "enabled": True
        }

        monitor_info = DeviceMonitorInfo(device_config, mock_watcher)

        # 未启动状态
        status = monitor_info.get_status()
        assert status["device_name"] == "测试设备"
        assert status["is_running"] is False
        assert status["alarm_count"] == 0
        assert "last_heartbeat" in status

        # 启动后状态
        monitor_info.start()
        monitor_info.increment_alarm_count()

        status = monitor_info.get_status()
        assert status["is_running"] is True
        assert status["alarm_count"] == 1
