"""测试 MultiDeviceWatcher 多设备监控器"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_db_devices():
    """模拟数据库中的设备列表"""
    return [
        {
            "device_name": "点胶设备",
            "log_path": "点胶设备\\上位机日志\\",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "打螺丝设备",
            "log_path": "打螺丝设备\\上位机日志\\",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "禁用设备",
            "log_path": "禁用设备\\日志\\",
            "enabled": False,  # 这个设备不应被启动
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        }
    ]


@pytest.fixture(autouse=True)
def cleanup_watcher():
    """清理 MultiDeviceWatcher 创建的资源"""
    yield
    # 清理所有可能遗留的监控线程
    import threading
    for thread in threading.enumerate():
        if thread.name.startswith('DeviceMonitor-'):
            thread.join(timeout=1.0)


class TestMultiDeviceWatcher:
    """测试 MultiDeviceWatcher 多设备监控器"""

    def test_load_devices_from_db(self, mock_db_devices):
        """测试从数据库加载设备"""
        from src.multi_device_watcher import MultiDeviceWatcher

        # Mock 数据库查询
        with patch('src.multi_device_watcher.DeviceConfig.get_all') as mock_get_all:
            mock_get_all.return_value = mock_db_devices

            # 创建 MultiDeviceWatcher
            watcher = MultiDeviceWatcher(on_alarm=MagicMock())

            # 加载设备
            devices = watcher.load_devices_from_db()

            # 验证：只返回启用的设备
            assert len(devices) == 2
            assert any(d["device_name"] == "点胶设备" for d in devices)
            assert any(d["device_name"] == "打螺丝设备" for d in devices)
            assert not any(d["device_name"] == "禁用设备" for d in devices)


    def test_start_single_device(self):
        """测试启动单个设备"""
        from src.multi_device_watcher import MultiDeviceWatcher
        from pathlib import Path

        alarm_events = []

        def on_alarm(event):
            alarm_events.append(event)

        watcher = MultiDeviceWatcher(on_alarm=on_alarm)

        device_config = {
            "device_name": "测试设备",
            "log_path": "测试\\日志\\",
            "enabled": True,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        }

        # 启动设备
        watcher.start_device(device_config)

        # 验证：设备已添加到监控列表
        assert "测试设备" in watcher.device_monitors
        assert watcher.device_monitors["测试设备"].is_running is True


    def test_stop_device(self):
        """测试停止单个设备"""
        from src.multi_device_watcher import MultiDeviceWatcher

        watcher = MultiDeviceWatcher(on_alarm=MagicMock())

        device_config = {
            "device_name": "测试设备",
            "log_path": "测试\\日志\\",
            "enabled": True,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        }

        # 先启动
        watcher.start_device(device_config)
        assert "测试设备" in watcher.device_monitors

        # 再停止
        watcher.stop_device("测试设备")

        # 验证：设备已从监控列表移除
        assert "测试设备" not in watcher.device_monitors


    def test_start_all_devices(self, mock_db_devices):
        """测试启动所有设备"""
        from src.multi_device_watcher import MultiDeviceWatcher

        with patch('src.multi_device_watcher.DeviceConfig.get_all') as mock_get_all:
            mock_get_all.return_value = mock_db_devices

            alarm_events = []

            def on_alarm(event):
                alarm_events.append(event)

            watcher = MultiDeviceWatcher(on_alarm=on_alarm)

            # 启动所有设备
            devices = watcher.load_devices_from_db()
            watcher.start_all(devices)

            # 验证：只有启用的设备被启动
            assert len(watcher.device_monitors) == 2
            assert "点胶设备" in watcher.device_monitors
            assert "打螺丝设备" in watcher.device_monitors
            assert "禁用设备" not in watcher.device_monitors


    def test_stop_all_devices(self):
        """测试停止所有设备"""
        from src.multi_device_watcher import MultiDeviceWatcher

        watcher = MultiDeviceWatcher(on_alarm=MagicMock())

        # 启动多个设备
        devices = [
            {"device_name": "设备1", "log_path": "路径1\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"},
            {"device_name": "设备2", "log_path": "路径2\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"}
        ]
        watcher.start_all(devices)

        assert len(watcher.device_monitors) == 2

        # 停止所有设备
        watcher.stop_all()

        # 验证：所有设备已停止
        assert len(watcher.device_monitors) == 0


    def test_get_active_devices(self):
        """测试获取活动设备列表"""
        from src.multi_device_watcher import MultiDeviceWatcher

        watcher = MultiDeviceWatcher(on_alarm=MagicMock())

        # 启动多个设备
        devices = [
            {"device_name": "设备1", "log_path": "路径1\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"},
            {"device_name": "设备2", "log_path": "路径2\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"}
        ]
        watcher.start_all(devices)

        # 获取活动设备
        active = watcher.get_active_devices()

        assert len(active) == 2
        assert "设备1" in active
        assert "设备2" in active


    def test_get_device_status(self):
        """测试获取单个设备状态"""
        from src.multi_device_watcher import MultiDeviceWatcher

        watcher = MultiDeviceWatcher(on_alarm=MagicMock())

        device_config = {
            "device_name": "测试设备",
            "log_path": "测试\\日志\\",
            "enabled": True,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        }

        watcher.start_device(device_config)

        # 获取设备状态
        status = watcher.get_device_status("测试设备")

        assert status["device_name"] == "测试设备"
        assert status["is_running"] is True
        assert "log_path" in status
