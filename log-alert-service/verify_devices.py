#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证设备添加结果"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.device_config import DeviceConfig

# 设置输出编码为UTF-8
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

devices = DeviceConfig.get_all()

print("=" * 60)
print("设备管理中的设备列表:")
print("=" * 60)

if devices:
    for i, device in enumerate(devices, 1):
        print(f"\n设备 {i}:")
        print(f"  名称: {device['device_name']}")
        print(f"  路径: {device['log_path']}")
        print(f"  状态: {'启用' if device.get('enabled', True) else '禁用'}")
        print(f"  自动通知: {'是' if device.get('auto_notify', False) else '否'}")
        print(f"  轮询间隔: {device.get('polling_interval', 2)} 秒")
        print(f"  编码: {device.get('encoding', 'utf-8-sig')}")
else:
    print("(无设备)")

print("\n" + "=" * 60)
print(f"总计: {len(devices)} 个设备")
print("=" * 60)