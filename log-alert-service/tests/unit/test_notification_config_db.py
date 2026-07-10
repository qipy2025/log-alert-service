"""测试通知配置数据库操作层"""
import pytest
from unittest.mock import patch, MagicMock
from src.db.notification_config_db import get_notification_config, update_notification_config, init_default_config
from src.models.notification_config import NotificationConfig


class TestNotificationConfigDB:
    """测试通知配置数据库操作"""

    @patch('src.db.notification_config_db.get_db_session')
    def test_get_notification_config_success(self, mock_get_session):
        """测试成功获取配置"""
        # mock 直接返回 session 对象
        mock_session = MagicMock()

        # 模拟查询结果
        mock_session.execute().fetchone.return_value = (1, True, '["CRITICAL"]')

        # 直接返回 session（不是上下文管理器）
        mock_get_session.return_value = mock_session

        config = get_notification_config()

        assert config is not None
        assert config.enabled is True
        assert config.allowed_levels == ["CRITICAL"]

    @patch('src.db.notification_config_db.get_db_session')
    def test_get_notification_config_not_found(self, mock_get_session):
        """测试配置不存在时返回 None"""
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = None
        mock_get_session.return_value = mock_session

        config = get_notification_config()

        assert config is None

    @patch('src.db.notification_config_db.get_db_session')
    def test_update_notification_config_success(self, mock_get_session):
        """测试成功更新配置"""
        mock_session = MagicMock()
        mock_session.commit = MagicMock()

        mock_get_session.return_value = mock_session

        config = update_notification_config(True, ["CRITICAL", "WARNING"])

        assert config.enabled is True
        assert config.allowed_levels == ["CRITICAL", "WARNING"]
        assert config.id == 1
        mock_session.commit.assert_called_once()

    @patch('src.db.notification_config_db.get_db_session')
    def test_init_default_config_creates_new(self, mock_get_session):
        """测试初始化配置（不存在时创建）"""
        mock_session = MagicMock()
        mock_session.commit = MagicMock()

        mock_get_session.return_value = mock_session

        mock_session.execute().fetchone.return_value = None

        result = init_default_config()

        assert result is True
        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()

    @patch('src.db.notification_config_db.get_db_session')
    def test_init_default_config_already_exists(self, mock_get_session):
        """测试初始化配置（已存在时不创建）"""
        mock_session = MagicMock()

        mock_get_session.return_value = mock_session

        # 模拟 fetchone 返回 truthy 值
        mock_session.execute().fetchone.return_value = True

        result = init_default_config()

        assert result is False
        # 至少应该执行一次 SELECT
        assert mock_session.execute.call_count >= 1

    @patch('src.db.notification_config_db.get_db_session')
    def test_get_notification_config_exception_handling(self, mock_get_session):
        """测试异常处理 - 数据库错误时应抛出 RuntimeError"""
        mock_session = MagicMock()

        # 模拟数据库异常
        mock_session.execute.side_effect = Exception("DB connection failed")

        mock_get_session.return_value = mock_session

        with pytest.raises(RuntimeError, match="Failed to get notification config"):
            get_notification_config()

    @patch('src.db.notification_config_db.get_db_session')
    def test_update_notification_config_exception_handling(self, mock_get_session):
        """测试更新配置时的异常处理"""
        mock_session = MagicMock()
        mock_session.rollback = MagicMock()

        # 模拟执行失败
        mock_session.execute.side_effect = Exception("Update failed")

        mock_get_session.return_value = mock_session

        with pytest.raises(RuntimeError, match="Failed to update notification config"):
            update_notification_config(True, ["CRITICAL"])

        mock_session.rollback.assert_called_once()

    @patch('src.db.notification_config_db.get_db_session')
    def test_init_default_config_exception_handling(self, mock_get_session):
        """测试初始化配置时的异常处理"""
        mock_session = MagicMock()
        mock_session.rollback = MagicMock()

        # 模拟执行失败
        mock_session.execute.side_effect = Exception("Init failed")

        mock_get_session.return_value = mock_session

        with pytest.raises(RuntimeError, match="Failed to init default config"):
            init_default_config()

        mock_session.rollback.assert_called_once()
