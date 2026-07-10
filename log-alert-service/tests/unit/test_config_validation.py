"""测试配置验证和错误处理功能"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from main import AlertService


class TestConfigValidation(unittest.TestCase):
    """测试配置验证功能"""

    def setUp(self):
        """测试前准备"""
        self.service = AlertService(config_path="config.yaml", enable_web=False)

    def test_validate_device_config_valid(self):
        """测试验证有效的设备配置"""
        valid_config = {
            "device_name": "设备1",
            "log_path": "C:\\Logs\\Device1",
            "encoding": "utf-8-sig",
            "polling_interval": 2
        }

        is_valid, error = self.service._validate_device_config(valid_config)

        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validate_device_config_missing_name(self):
        """测试缺少设备名称"""
        invalid_config = {
            "log_path": "C:\\Logs\\Device1",
            "encoding": "utf-8-sig",
            "polling_interval": 2
        }

        is_valid, error = self.service._validate_device_config(invalid_config)

        self.assertFalse(is_valid)
        self.assertIn("device_name", error)

    def test_validate_device_config_missing_log_path(self):
        """测试缺少日志路径"""
        invalid_config = {
            "device_name": "设备1",
            "encoding": "utf-8-sig",
            "polling_interval": 2
        }

        is_valid, error = self.service._validate_device_config(invalid_config)

        self.assertFalse(is_valid)
        self.assertIn("log_path", error)

    def test_validate_device_config_missing_encoding(self):
        """测试缺少编码"""
        invalid_config = {
            "device_name": "设备1",
            "log_path": "C:\\Logs\\Device1",
            "polling_interval": 2
        }

        is_valid, error = self.service._validate_device_config(invalid_config)

        self.assertFalse(is_valid)
        self.assertIn("encoding", error)

    def test_validate_device_config_missing_polling_interval(self):
        """测试缺少轮询间隔"""
        invalid_config = {
            "device_name": "设备1",
            "log_path": "C:\\Logs\\Device1",
            "encoding": "utf-8-sig"
        }

        is_valid, error = self.service._validate_device_config(invalid_config)

        self.assertFalse(is_valid)
        self.assertIn("polling_interval", error)

    def test_validate_device_config_invalid_interval(self):
        """测试无效的轮询间隔"""
        # 负数
        invalid_config = {
            "device_name": "设备1",
            "log_path": "C:\\Logs\\Device1",
            "encoding": "utf-8-sig",
            "polling_interval": -1
        }

        is_valid, error = self.service._validate_device_config(invalid_config)

        self.assertFalse(is_valid)
        self.assertIn("正整数", error)

        # 零
        invalid_config["polling_interval"] = 0
        is_valid, error = self.service._validate_device_config(invalid_config)

        self.assertFalse(is_valid)
        self.assertIn("正整数", error)

        # 非整数
        invalid_config["polling_interval"] = 2.5
        is_valid, error = self.service._validate_device_config(invalid_config)

        self.assertFalse(is_valid)
        self.assertIn("正整数", error)

    def test_validate_device_config_invalid_device_name(self):
        """测试无效的设备名称"""
        invalid_config = {
            "device_name": "设备@#",  # 包含非法字符
            "log_path": "C:\\Logs\\Device1",
            "encoding": "utf-8-sig",
            "polling_interval": 2
        }

        is_valid, error = self.service._validate_device_config(invalid_config)

        self.assertFalse(is_valid)
        self.assertIn("格式", error)

    def test_validate_device_config_invalid_log_path(self):
        """测试无效的日志路径"""
        invalid_config = {
            "device_name": "设备1",
            "log_path": "invalid<>path",  # 包含非法字符
            "encoding": "utf-8-sig",
            "polling_interval": 2
        }

        is_valid, error = self.service._validate_device_config(invalid_config)

        self.assertFalse(is_valid)
        self.assertIn("路径", error)


class TestErrorHandling(unittest.TestCase):
    """测试错误处理功能"""

    def setUp(self):
        """测试前准备"""
        # 创建一个 mock 服务
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "device_polling.interval": 30,
            "dedup.alarm_window": 300,
            "dedup.max_repeat_count": 99,
            "ai_analysis.api_key": "",
            "ai_analysis.api_base_url": "http://model-api.desaysv.com",
            "ai_analysis.model": "deepseek-v4-flash-anthropic",
            "ai_analysis.max_tokens": 2048,
            "ai_analysis.temperature": 0.3,
            "ai_analysis.enabled": True,
            "feishu.app_id": "",
            "feishu.app_secret": "",
            "feishu.chats": [],
            "log_source.max_context_lines": 20,
            "log_source.functional_log_window": 5,
            "daily_report.enabled": False  # 禁用日报，避免定时任务配置问题
        }.get(key, default)

        with patch('main.ConfigManager', return_value=mock_config):
            self.service = AlertService(config_path="config.yaml", enable_web=False)

    @patch('main.MultiDeviceWatcher')
    def test_start_with_database_failure(self, mock_watcher_class):
        """测试数据库连接失败时的处理"""
        # 模拟 MultiDeviceWatcher 实例
        mock_watcher = MagicMock()
        mock_watcher.load_devices_from_db.side_effect = Exception("数据库连接失败")
        mock_watcher_class.return_value = mock_watcher

        # 启动服务（不应该抛出异常）
        try:
            self.service.start()
        except Exception as e:
            self.fail(f"服务启动失败: {e}")

        # 验证服务仍然标记为运行
        self.assertTrue(self.service._running)

    @patch('main.MultiDeviceWatcher')
    def test_start_with_mixed_valid_invalid_configs(self, mock_watcher_class):
        """测试混合有效和无效配置的处理"""
        # 准备测试数据
        valid_config = {
            "device_name": "有效设备",
            "log_path": "C:\\Logs\\Valid",
            "encoding": "utf-8-sig",
            "polling_interval": 2
        }
        invalid_config = {
            "device_name": "",  # 无效：空名称
            "log_path": "C:\\Logs\\Invalid",
            "encoding": "utf-8-sig",
            "polling_interval": 2
        }

        # 模拟 MultiDeviceWatcher 实例
        mock_watcher = MagicMock()
        mock_watcher.load_devices_from_db.return_value = [valid_config, invalid_config]
        mock_watcher.start_all.return_value = None
        mock_watcher.get_active_devices.return_value = ["有效设备"]
        mock_watcher_class.return_value = mock_watcher

        # 启动服务（不应该抛出异常）
        try:
            self.service.start()
        except Exception as e:
            self.fail(f"服务启动失败: {e}")

        # 验证 start_all 只被调用了一次（只包含有效配置）
        mock_watcher.start_all.assert_called_once()
        called_devices = mock_watcher.start_all.call_args[0][0]
        self.assertEqual(len(called_devices), 1)
        self.assertEqual(called_devices[0]["device_name"], "有效设备")

    @patch('main.MultiDeviceWatcher')
    def test_start_all_devices_fail(self, mock_watcher_class):
        """测试所有设备启动失败的情况"""
        # 准备有效的配置
        valid_config = {
            "device_name": "设备1",
            "log_path": "C:\\Logs\\Device1",
            "encoding": "utf-8-sig",
            "polling_interval": 2
        }

        # 模拟 MultiDeviceWatcher 实例
        mock_watcher = MagicMock()
        mock_watcher.load_devices_from_db.return_value = [valid_config]
        mock_watcher.start_all.return_value = None
        mock_watcher.get_active_devices.return_value = []  # 所有设备都失败了
        mock_watcher_class.return_value = mock_watcher

        # 启动服务（不应该抛出异常）
        try:
            self.service.start()
        except Exception as e:
            self.fail(f"服务启动失败: {e}")

        # 验证服务仍然标记为运行
        self.assertTrue(self.service._running)


if __name__ == '__main__':
    unittest.main()
