import pytest
from src.db.device_config import DeviceConfig

@pytest.fixture
def clean_db():
    """测试前清理"""
    DeviceConfig.delete("测试设备A")
    DeviceConfig.delete("测试设备B")
    DeviceConfig.delete("test_update_device")
    yield
    # 测试后清理
    DeviceConfig.delete("测试设备A")
    DeviceConfig.delete("测试设备B")
    DeviceConfig.delete("test_update_device")

def test_create_device(clean_db):
    """测试创建设备配置"""
    device = DeviceConfig.create(
        device_name="测试设备A",
        log_path="测试路径\\",
        auto_notify=False
    )
    assert device["device_name"] == "测试设备A"
    assert device["auto_notify"] == 0  # MySQL TINYINT(1) 返回整数

def test_device_exists(clean_db):
    """测试设备存在性检查"""
    DeviceConfig.create(device_name="测试设备A", log_path="路径\\")
    assert DeviceConfig.exists("测试设备A") is True
    assert DeviceConfig.exists("不存在的设备") is False

def test_get_device(clean_db):
    """测试获取设备配置"""
    DeviceConfig.create(device_name="测试设备A", log_path="路径\\")
    device = DeviceConfig.get_by_name("测试设备A")
    assert device is not None
    assert device["log_path"] == "路径\\"

def test_delete_device(clean_db):
    """测试删除设备"""
    DeviceConfig.create(device_name="测试设备A", log_path="路径\\")
    result = DeviceConfig.delete("测试设备A")
    assert result is True
    assert DeviceConfig.exists("测试设备A") is False

def test_update_auto_notify(clean_db):
    """测试更新自动发送设置"""
    DeviceConfig.create(device_name="测试设备A", log_path="路径\\", auto_notify=False)
    result = DeviceConfig.update_auto_notify("测试设备A", True)
    assert result is True

    device = DeviceConfig.get_by_name("测试设备A")
    assert device["auto_notify"] == 1  # MySQL TINYINT(1) 返回整数

def test_get_all_devices(clean_db):
    """测试获取所有设备"""
    DeviceConfig.create(device_name="测试设备A", log_path="路径A\\")
    DeviceConfig.create(device_name="测试设备B", log_path="路径B\\")

    devices = DeviceConfig.get_all()
    assert len(devices) >= 2
    device_names = [d["device_name"] for d in devices]
    assert "测试设备A" in device_names
    assert "测试设备B" in device_names

def test_update_device_config(clean_db):
    """测试更新设备配置"""
    # 创建测试设备
    DeviceConfig.create(
        device_name="test_update_device",
        log_path="test\\path\\",
        auto_notify=False,
        polling_interval=2,
        encoding="utf-8-sig",
        enabled=True
    )

    # 更新设备配置
    result = DeviceConfig.update(
        device_name="test_update_device",
        log_path="new\\path\\",
        enabled=False
    )

    assert result is True

    # 验证更新结果
    updated = DeviceConfig.get_by_name("test_update_device")
    assert updated["log_path"] == "new\\path\\"
    assert updated["enabled"] == 0  # MySQL TINYINT(1) 返回整数
    # 其他字段应保持不变
    assert updated["auto_notify"] == 0
    assert updated["polling_interval"] == 2
