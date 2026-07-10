"""测试通知配置数据模型"""
import pytest
from unittest.mock import MagicMock
from src.models.notification_config import NotificationConfig


class TestNotificationConfig:
    """测试 NotificationConfig 数据模型"""

    def test_from_db_with_valid_data(self):
        """测试从有效数据库记录创建模型"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = True
        mock_record.allowed_levels = '["CRITICAL", "WARNING"]'

        config = NotificationConfig.from_db(mock_record)

        assert config.id == 1
        assert config.enabled is True
        assert config.allowed_levels == ["CRITICAL", "WARNING"]

    def test_from_db_with_list_data(self):
        """测试从列表类型的 allowed_levels 创建模型"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = False
        mock_record.allowed_levels = ["CRITICAL"]  # 已经是列表

        config = NotificationConfig.from_db(mock_record)

        assert config.allowed_levels == ["CRITICAL"]

    def test_from_db_with_empty_array(self):
        """测试空数组配置"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = False
        mock_record.allowed_levels = '[]'

        config = NotificationConfig.from_db(mock_record)

        assert config.enabled is False
        assert config.allowed_levels == []

    def test_from_db_with_null_levels(self):
        """测试 allowed_levels 为 None 的情况"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = True
        mock_record.allowed_levels = None

        config = NotificationConfig.from_db(mock_record)

        assert config.allowed_levels == []

    def test_from_db_with_invalid_json(self):
        """测试无效的 JSON 字符串"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = True
        mock_record.allowed_levels = 'invalid-json'

        config = NotificationConfig.from_db(mock_record)

        # 解析失败时应该返回空列表
        assert config.allowed_levels == []

    def test_from_db_with_none_record(self):
        """测试 record 为 None 的情况"""
        config = NotificationConfig.from_db(None)

        assert config.id == 1
        assert config.enabled is False
        assert config.allowed_levels == []
