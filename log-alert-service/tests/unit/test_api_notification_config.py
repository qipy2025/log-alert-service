"""测试通知配置 API"""
import pytest
import json
from unittest.mock import patch, MagicMock
from src.models.notification_config import NotificationConfig


@pytest.fixture
def app():
    """创建测试应用"""
    from src.web.app import create_app
    app = create_app(testing=True)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class TestNotificationConfigAPI:
    """测试通知配置 API 接口"""

    @patch('src.web.routes.get_notification_config')
    def test_get_config_success(self, mock_get_config, client):
        """测试成功获取配置"""
        mock_config = NotificationConfig(id=1, enabled=True, allowed_levels=["CRITICAL"])
        mock_get_config.return_value = mock_config

        response = client.get('/api/notification-config')

        assert response.status_code == 200
        data = response.get_json()
        assert data['enabled'] is True
        assert data['allowed_levels'] == ["CRITICAL"]

    @patch('src.web.routes.get_notification_config')
    def test_get_config_returns_default_when_none(self, mock_get_config, client):
        """测试配置不存在时返回默认值"""
        mock_get_config.return_value = None

        response = client.get('/api/notification-config')

        assert response.status_code == 200
        data = response.get_json()
        assert data['enabled'] is False
        assert data['allowed_levels'] == []

    @patch('src.web.routes.update_notification_config')
    @patch('src.web.routes.broadcast_config_update')
    def test_update_config_success(self, mock_broadcast, mock_update, client):
        """测试成功更新配置"""
        mock_config = NotificationConfig(id=1, enabled=True, allowed_levels=["CRITICAL", "WARNING"])
        mock_update.return_value = mock_config

        response = client.put('/api/notification-config',
                            data=json.dumps({'enabled': True, 'allowed_levels': ['CRITICAL', 'WARNING']}),
                            content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['config']['enabled'] is True
        mock_broadcast.assert_called_once()

    def test_update_config_invalid_levels_type(self, client):
        """测试 allowed_levels 类型无效"""
        response = client.put('/api/notification-config',
                            data=json.dumps({'enabled': True, 'allowed_levels': 'INVALID'}),
                            content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_update_config_invalid_level_value(self, client):
        """测试告警级别值无效"""
        response = client.put('/api/notification-config',
                            data=json.dumps({'enabled': True, 'allowed_levels': ['INVALID_LEVEL']}),
                            content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid alarm level' in data['error']

    def test_update_config_missing_body(self, client):
        """测试缺少请求体"""
        response = client.put('/api/notification-config')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
