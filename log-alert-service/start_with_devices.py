#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""启动监控系统并加载CD-ADS-1设备"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("启动监控系统 - CD-ADS-1设备")
print("=" * 60)

# 首先验证设备配置
from src.db.device_config import DeviceConfig
devices = DeviceConfig.get_all()

enabled_devices = [d for d in devices if d.get('enabled', False)]

print(f"\n数据库中设备状态:")
print(f"总设备数: {len(devices)}")
print(f"已启用: {len(enabled_devices)}")

if enabled_devices:
    print(f"\n将要启动监控的设备:")
    for device in enabled_devices:
        print(f"  - {device['device_name']}")

print("\n" + "=" * 60)
print("启动监控系统...")
print("=" * 60)

# 启动主程序
from main import AlertService

try:
    # 创建服务实例（启用Web界面）
    service = AlertService(enable_web=True)

    # 启动服务
    service.start()

    print("\n" + "=" * 60)
    print("✅ 监控系统启动成功!")
    print("=" * 60)
    print(f"Web界面: http://localhost:5000")
    print(f"WebSocket: ws://localhost:5000")
    print("=" * 60)

    # 保持运行
    import signal
    def signal_handler(sig, frame):
        print("\n收到停止信号，正在关闭服务...")
        service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("监控系统正在运行，按 Ctrl+C 停止...")
    signal.pause()

except Exception as e:
    print(f"\n❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()

    print("\n常见问题排查:")
    print("1. 数据库连接失败 - 检查 .env 文件中的MySQL配置")
    print("2. 端口被占用 - 检查5000端口是否被其他程序占用")
    print("3. 依赖缺失 - 运行: pip install -r requirements.txt")
    sys.exit(1)