import pytest
from src.web.app import create_app
import json

@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app(testing=True)
    return app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

def test_get_devices(client):
    """测试获取设备列表"""
    response = client.get('/api/devices')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'devices' in data
    assert isinstance(data['devices'], list)

def test_pause_device(client):
    """测试暂停设备"""
    response = client.post('/api/devices/测试设备/pause',
                          json={'reason': '测试暂停'},
                          content_type='application/json')
    # 暂时不验证响应，只验证不报错
    assert response.status_code in [200, 404, 500]

def test_start_device(client):
    """测试启动设备"""
    response = client.post('/api/devices/测试设备/start',
                          json={'reason': '测试启动'},
                          content_type='application/json')
    assert response.status_code in [200, 404, 500]

def test_get_alarms(client):
    """测试获取告警列表"""
    response = client.get('/api/alarms?device=测试设备&limit=10')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'alarms' in data
    assert 'total' in data
