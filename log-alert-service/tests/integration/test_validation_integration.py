"""集成测试：验证配置验证和错误处理的实际行为"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from unittest.mock import MagicMock, patch
from main import AlertService


def test_validation_output():
    """测试配置验证的日志输出"""
    print("=" * 60)
    print("测试配置验证和错误处理功能")
    print("=" * 60)

    # 创建 mock 配置
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
        "daily_report.enabled": False,
        "daily_report.schedule_time": "22:00"
    }.get(key, default)

    # 准备测试数据：混合有效和无效配置
    test_devices = [
        {
            "device_name": "设备1",
            "log_path": "C:\\Logs\\Device1",
            "encoding": "utf-8-sig",
            "polling_interval": 2,
            "enabled": True
        },
        {
            "device_name": "",  # 无效：空名称
            "log_path": "C:\\Logs\\Device2",
            "encoding": "utf-8-sig",
            "polling_interval": 2,
            "enabled": True
        },
        {
            "device_name": "设备3",
            "log_path": "C:\\Logs\\Device3",
            "encoding": "utf-8-sig",
            "polling_interval": 2,
            "enabled": True
        },
        {
            "device_name": "设备4",
            "log_path": "",  # 无效：空路径
            "encoding": "utf-8-sig",
            "polling_interval": 2,
            "enabled": True
        },
        {
            "device_name": "设备5",
            "log_path": "C:\\Logs\\Device5",
            "encoding": "utf-8-sig",
            "polling_interval": -1,  # 无效：负数间隔
            "enabled": True
        },
    ]

    with patch('main.ConfigManager', return_value=mock_config):
        # 模拟 MultiDeviceWatcher
        with patch('main.MultiDeviceWatcher') as mock_watcher_class:
            mock_watcher = MagicMock()
            mock_watcher.load_devices_from_db.return_value = test_devices
            mock_watcher.start_all.return_value = None
            # 模拟成功启动2个设备（设备1和设备3）
            mock_watcher.get_active_devices.return_value = ["设备1", "设备3"]
            mock_watcher_class.return_value = mock_watcher

            # 创建服务
            service = AlertService(config_path="config.yaml", enable_web=False)

            print("\n开始启动服务...")
            print("-" * 60)

            # 启动服务
            try:
                service.start()
                print("\n" + "-" * 60)
                print("[OK] 服务启动成功")
                print("-" * 60)

                # 验证调用
                assert mock_watcher.load_devices_from_db.called, "应该加载设备配置"
                assert mock_watcher.start_all.called, "应该启动有效设备"

                # 检查传递给 start_all 的设备列表
                called_devices = mock_watcher.start_all.call_args[0][0]
                print(f"\n传递给 start_all 的设备数量: {len(called_devices)}")
                print(f"设备名称: {[d['device_name'] for d in called_devices]}")

                # 验证只有有效设备被传递
                assert len(called_devices) == 2, f"应该只有2个有效设备，实际有 {len(called_devices)} 个"
                assert all(d['device_name'] in ['设备1', '设备3'] for d in called_devices), \
                    "应该只包含设备1和设备3"

                print("\n[OK] 验证通过！")
                print("  - 配置验证正确识别了3个无效配置")
                print("  - 错误处理正确跳过了无效配置")
                print("  - 服务成功启动了2个有效设备")

            except Exception as e:
                print(f"\n[FAIL] 服务启动失败: {e}")
                import traceback
                traceback.print_exc()
                return False

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    return True


def test_database_failure():
    """测试数据库连接失败的处理"""
    print("\n" + "=" * 60)
    print("测试数据库连接失败的处理")
    print("=" * 60)

    # 创建 mock 配置
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
        "daily_report.enabled": False,
        "daily_report.schedule_time": "22:00"
    }.get(key, default)

    with patch('main.ConfigManager', return_value=mock_config):
        # 模拟 MultiDeviceWatcher 数据库连接失败
        with patch('main.MultiDeviceWatcher') as mock_watcher_class:
            mock_watcher = MagicMock()
            mock_watcher.load_devices_from_db.side_effect = Exception("数据库连接失败")
            mock_watcher_class.return_value = mock_watcher

            # 创建服务
            service = AlertService(config_path="config.yaml", enable_web=False)

            print("\n开始启动服务（模拟数据库连接失败）...")
            print("-" * 60)

            try:
                service.start()
                print("\n" + "-" * 60)
                print("[OK] 服务启动成功（即使数据库连接失败）")
                print("-" * 60)
                print("\n[OK] 验证通过！")
                print("  - 数据库连接失败不会阻止服务启动")
                print("  - 服务将继续运行但不会监控任何设备")

            except Exception as e:
                print(f"\n[FAIL] 服务启动失败（不应该发生）: {e}")
                import traceback
                traceback.print_exc()
                return False

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = True
    success = test_validation_output() and success
    success = test_database_failure() and success

    if success:
        print("\n[SUCCESS] 所有测试通过！")
        sys.exit(0)
    else:
        print("\n[FAIL] 部分测试失败")
        sys.exit(1)
