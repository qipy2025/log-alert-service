"""设备管理器单元测试"""
import pytest
from src.device_manager import DeviceManager
from src.db.device_config import DeviceConfig

def test_validate_device_name():
    """测试设备名称验证"""
    manager = DeviceManager()

    # 有效名称
    assert manager.validate_device_name("点胶设备") is True
    assert manager.validate_device_name("Device_123") is True

    # 无效名称
    with pytest.raises(ValueError, match="设备名称不能为空"):
        manager.validate_device_name("")

    with pytest.raises(ValueError, match="设备名称格式无效"):
        manager.validate_device_name("设备@名称")

def test_validate_log_path():
    """测试日志路径验证"""
    manager = DeviceManager()

    # 有效路径
    assert manager.validate_log_path("设备\\日志\\") is True
    assert manager.validate_log_path("/var/log/device/") is True

    # 无效路径
    with pytest.raises(ValueError, match="日志路径不能为空"):
        manager.validate_log_path("")

    with pytest.raises(ValueError, match="路径格式无效"):
        manager.validate_log_path("invalid<>path")

def test_add_device_success():
    """测试成功添加设备"""
    manager = DeviceManager()

    # 清理
    if DeviceConfig.exists("新设备"):
        DeviceConfig.delete("新设备")

    result = manager.add_device({
        "device_name": "新设备",
        "log_path": "新设备\\日志\\",
        "auto_notify": False
    })

    assert result["device_name"] == "新设备"
    assert result["auto_notify"] in (False, 0)  # MySQL返回0而不是False

    # 清理
    DeviceConfig.delete("新设备")

def test_add_device_duplicate():
    """测试添加重复设备"""
    manager = DeviceManager()

    # 先添加一个设备
    DeviceConfig.create(device_name="已存在设备", log_path="路径\\")

    # 尝试添加同名设备
    with pytest.raises(ValueError, match="设备名称已存在"):
        manager.add_device({
            "device_name": "已存在设备",
            "log_path": "其他路径\\"
        })

    # 清理
    DeviceConfig.delete("已存在设备")

def test_add_device_invalid_name():
    """测试添加设备时名称无效"""
    manager = DeviceManager()

    with pytest.raises(ValueError, match="设备名称格式无效"):
        manager.add_device({
            "device_name": "无效@名称",
            "log_path": "路径\\"
        })

def test_add_device_invalid_path():
    """测试添加设备时路径无效"""
    manager = DeviceManager()

    with pytest.raises(ValueError, match="路径格式无效"):
        manager.add_device({
            "device_name": "设备",
            "log_path": "invalid<>path"
        })

def test_delete_device_success():
    """测试成功删除设备"""
    manager = DeviceManager()

    # 清理（如果存在）
    if DeviceConfig.exists("待删除设备"):
        DeviceConfig.delete("待删除设备")

    # 先添加设备
    DeviceConfig.create(device_name="待删除设备", log_path="路径\\")

    result = manager.delete_device("待删除设备")
    assert result is True
    assert DeviceConfig.exists("待删除设备") is False

def test_delete_device_not_found():
    """测试删除不存在的设备"""
    manager = DeviceManager()

    with pytest.raises(ValueError, match="设备不存在"):
        manager.delete_device("不存在的设备")
