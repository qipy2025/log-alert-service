"""测试通知配置数据库操作层"""
import pytest
from unittest.mock import patch, MagicMock
from src.db.notification_config_db import get_notification_config, update_notification_config, init_default_config
from src.models.notification_config import NotificationConfig


class MockDBRecord:
    """模拟数据库记录"""
    def __init__(self, id, enabled, allowed_levels):
        self.id = id
        self.enabled = enabled
        self.allowed_levels = allowed_levels


class TestNotificationConfigDB:
    """测试通知配置数据库操作"""

    @patch('src.db.notification_config_db.get_db_session')
    def test_get_notification_config_success(self, mock_get_session):
        """测试成功获取配置"""
        # 模拟数据库返回结果
        mock_session = MagicMock()
        mock_record = MockDBRecord(1, True, '["CRITICAL"]')
        mock_session.execute().fetchone.return_value = mock_record
        mock_get_session.return_value.__enter__.return_value = mock_session

        config = get_notification_config()

        assert config is not None
        assert config.enabled is True
        assert config.allowed_levels == ["CRITICAL"]

    @patch('src.db.notification_config_db.get_db_session')
    def test_get_notification_config_not_found(self, mock_get_session):
        """测试配置不存在时返回 None"""
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        config = get_notification_config()

        assert config is None

    @patch('src.db.notification_config_db.get_db_session')
    @patch('src.db.notification_config_db.get_notification_config')
    def test_update_notification_config_success(self, mock_get_config, mock_get_session):
        """测试成功更新配置"""
        # 模拟更新后的配置
        mock_config = NotificationConfig(id=1, enabled=True, allowed_levels=["CRITICAL", "WARNING"])
        mock_get_config.return_value = mock_config

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        config = update_notification_config(True, ["CRITICAL", "WARNING"])

        assert config.enabled is True
        assert config.allowed_levels == ["CRITICAL", "WARNING"]
        mock_session.commit.assert_called_once()

    @patch('src.db.notification_config_db.get_db_session')
    def test_init_default_config_creates_new(self, mock_get_session):
        """测试初始化配置（不存在时创建）"""
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = init_default_config()

        assert result is True
        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()

    @patch('src.db.notification_config_db.get_db_session')
    def test_init_default_config_already_exists(self, mock_get_session):
        """测试初始化配置（已存在时不创建）"""
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = MagicMock()  # 存在记录
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = init_default_config()

        assert result is False
        # 不应该执行 INSERT（只有 SELECT）
        assert mock_session.execute.call_count == 1
