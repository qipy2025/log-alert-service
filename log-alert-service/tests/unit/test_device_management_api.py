"""测试设备管理 API"""
import pytest
import json
from unittest.mock import patch, MagicMock


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


class TestDeviceManagementAPI:
    """测试设备管理 API 接口"""

    @patch('src.device_manager.DeviceManager')
    def test_get_devices_config_success(self, mock_dm_class, client):
        """测试成功获取设备配置列表"""
        mock_dm = MagicMock()
        mock_dm.get_all_devices.return_value = [
            {
                "device_name": "设备1",
                "log_path": "path1\\\\",
                "auto_notify": False,
                "polling_interval": 2,
                "encoding": "utf-8-sig",
                "enabled": True
            }
        ]
        mock_dm_class.return_value = mock_dm

        response = client.get('/api/devices/config')

        assert response.status_code == 200
        data = response.get_json()
        assert 'devices' in data
        assert len(data['devices']) == 1
        assert data['devices'][0]['device_name'] == "设备1"

    @patch('src.device_manager.DeviceManager')
    def test_add_device_success(self, mock_dm_class, client):
        """测试成功添加设备"""
        mock_dm = MagicMock()
        mock_dm.add_device.return_value = {
            "device_name": "新设备",
            "log_path": "new\\path\\\\",
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig",
            "enabled": True
        }
        mock_dm_class.return_value = mock_dm

        response = client.post('/api/devices',
                              data=json.dumps({
                                  'device_name': '新设备',
                                  'log_path': 'new\\path\\',
                                  'enabled': True
                              }),
                              content_type='application/json')

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['device']['device_name'] == "新设备"

    def test_add_device_missing_fields(self, client):
        """测试添加设备缺少必填字段"""
        response = client.post('/api/devices',
                              data=json.dumps({'device_name': '设备1'}),
                              content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    @patch('src.device_manager.DeviceManager')
    def test_add_device_duplicate(self, mock_dm_class, client):
        """测试添加重复设备"""
        mock_dm = MagicMock()
        mock_dm.add_device.side_effect = ValueError("设备名称已存在: 新设备")
        mock_dm_class.return_value = mock_dm

        response = client.post('/api/devices',
                              data=json.dumps({
                                  'device_name': '新设备',
                                  'log_path': 'new\\path\\',
                                  'enabled': True
                              }),
                              content_type='application/json')

        assert response.status_code == 409
        data = response.get_json()
        assert '设备名称已存在' in data['error']

    @patch('src.device_manager.DeviceManager')
    def test_update_device_success(self, mock_dm_class, client):
        """测试成功更新设备"""
        mock_dm = MagicMock()
        mock_dm.update_device.return_value = {
            "device_name": "更新后",
            "log_path": "new\\path\\\\",
            "enabled": False
        }
        mock_dm_class.return_value = mock_dm

        response = client.put('/api/devices/旧名称',
                             data=json.dumps({
                                 'device_name': '更新后',
                                 'log_path': 'new\\path\\',
                                 'enabled': False
                             }),
                             content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('src.device_manager.DeviceManager')
    def test_update_device_not_found(self, mock_dm_class, client):
        """测试更新不存在的设备"""
        mock_dm = MagicMock()
        mock_dm.update_device.side_effect = ValueError("设备不存在: 不存在")
        mock_dm_class.return_value = mock_dm

        response = client.put('/api/devices/不存在',
                             data=json.dumps({'enabled': False}),
                             content_type='application/json')

        assert response.status_code == 404

    @patch('src.device_manager.DeviceManager')
    def test_delete_device_success(self, mock_dm_class, client):
        """测试成功删除设备"""
        mock_dm = MagicMock()
        mock_dm.delete_device.return_value = True
        mock_dm_class.return_value = mock_dm

        response = client.delete('/api/devices/测试设备')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('src.device_manager.DeviceManager')
    def test_delete_device_not_found(self, mock_dm_class, client):
        """测试删除不存在的设备"""
        mock_dm = MagicMock()
        mock_dm.delete_device.side_effect = ValueError("设备不存在: 不存在")
        mock_dm_class.return_value = mock_dm

        response = client.delete('/api/devices/不存在')

        assert response.status_code == 404

    @patch('src.device_manager.DeviceManager')
    def test_delete_device_running(self, mock_dm_class, client):
        """测试删除正在运行的设备"""
        mock_dm = MagicMock()
        mock_dm.delete_device.side_effect = RuntimeError("设备正在运行，无法删除")
        mock_dm_class.return_value = mock_dm

        response = client.delete('/api/devices/运行中')

        assert response.status_code == 409
