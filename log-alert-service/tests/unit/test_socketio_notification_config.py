"""测试 WebSocket 配置广播功能"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import sys


class TestWebSocketConfigBroadcast:
    """测试配置更新广播"""

    def test_broadcast_config_update(self):
        """测试成功广播配置更新"""
        # Setup mock
        mock_socketio = MagicMock()
        mock_current_app = Mock()
        mock_current_app.extensions.get.return_value = mock_socketio
        mock_logger = MagicMock()

        # Mock flask.current_app 和 src.web.socketio.logger
        with patch('flask.current_app', mock_current_app):
            with patch('src.web.socketio.logger', mock_logger):
                from src.web.socketio import broadcast_config_update

                config = {'enabled': True, 'allowed_levels': ['CRITICAL']}
                broadcast_config_update(config)

                # 验证 socketio.emit 被正确调用
                mock_socketio.emit.assert_called_once_with(
                    'notification_config_updated',
                    {
                        'type': 'notification_config_updated',
                        'data': config
                    },
                    broadcast=True
                )
                mock_logger.info.assert_called_once_with(
                    "通知配置更新已广播: enabled=True, levels=['CRITICAL']"
                )

    def test_broadcast_config_update_with_disabled_config(self):
        """测试广播禁用状态的配置"""
        # Setup mock
        mock_socketio = MagicMock()
        mock_current_app = Mock()
        mock_current_app.extensions.get.return_value = mock_socketio
        mock_logger = MagicMock()

        with patch('flask.current_app', mock_current_app):
            with patch('src.web.socketio.logger', mock_logger):
                from src.web.socketio import broadcast_config_update

                config = {'enabled': False, 'allowed_levels': []}
                broadcast_config_update(config)

                # 验证 socketio.emit 被正确调用
                mock_socketio.emit.assert_called_once_with(
                    'notification_config_updated',
                    {
                        'type': 'notification_config_updated',
                        'data': config
                    },
                    broadcast=True
                )
                mock_logger.info.assert_called_once_with(
                    "通知配置更新已广播: enabled=False, levels=[]"
                )

    def test_broadcast_config_update_without_socketio(self):
        """测试没有 socketio 实例时的情况"""
        # Setup mock - socketio 为 None
        mock_current_app = Mock()
        mock_current_app.extensions.get.return_value = None
        mock_logger = MagicMock()

        with patch('flask.current_app', mock_current_app):
            with patch('src.web.socketio.logger', mock_logger):
                from src.web.socketio import broadcast_config_update

                config = {'enabled': True, 'allowed_levels': ['WARNING']}

                # 应该不会抛出异常
                broadcast_config_update(config)

                # 由于 socketio 是 None，不应该调用 emit
                mock_socketio = MagicMock()
                mock_socketio.emit.assert_not_called()

    def test_broadcast_config_update_runtime_error(self):
        """测试 Flask 应用上下文不存在时的 RuntimeError"""
        mock_logger = MagicMock()
        mock_current_app = Mock()
        # 让 extensions.get 抛出 RuntimeError
        mock_current_app.extensions.get.side_effect = RuntimeError("No application context")

        with patch('flask.current_app', mock_current_app):
            with patch('src.web.socketio.logger', mock_logger):
                from src.web.socketio import broadcast_config_update

                config = {'enabled': True, 'allowed_levels': ['ERROR']}

                # 应该不会抛出异常，而是记录警告
                broadcast_config_update(config)

                # 验证记录了警告
                mock_logger.warning.assert_called_once()
                assert "Flask应用未运行" in mock_logger.warning.call_args[0][0]

    def test_broadcast_config_update_generic_error(self):
        """测试其他异常情况"""
        mock_logger = MagicMock()
        mock_current_app = Mock()
        # 让 extensions.get 抛出通用异常
        mock_current_app.extensions.get.side_effect = Exception("Unexpected error")

        with patch('flask.current_app', mock_current_app):
            with patch('src.web.socketio.logger', mock_logger):
                from src.web.socketio import broadcast_config_update

                config = {'enabled': True, 'allowed_levels': ['INFO']}

                # 应该不会抛出异常，而是记录错误
                broadcast_config_update(config)

                # 验证记录了错误
                mock_logger.error.assert_called_once()
                assert "广播配置更新失败" in mock_logger.error.call_args[0][0]
