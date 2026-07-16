#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""添加CD-ADS-1的四个设备到设备管理"""

import sys
import os

# 添加项目路径到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.device_config import DeviceConfig
from src.device_manager import DeviceManager

def add_cd_ads_devices():
    """添加CD-ADS-1的四个设备"""

    # 设备列表
    devices_to_add = [
        {
            "device_name": "打螺丝设备",
            "log_path": r"C:\code\01 log-alert-servies\CD-ADS-1\打螺丝设备\上位机日志",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "排线检测设备",
            "log_path": r"C:\code\01 log-alert-servies\CD-ADS-1\排线检测设备\上位机日志",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "点胶设备",
            "log_path": r"C:\code\01 log-alert-servies\CD-ADS-1\点胶设备\上位机日志",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "贴屏设备",
            "log_path": r"C:\code\01 log-alert-servies\CD-ADS-1\贴屏设备\上位机日志",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        }
    ]

    device_manager = DeviceManager()

    # 首先显示当前所有设备
    print("当前设备列表:")
    existing_devices = device_manager.get_all_devices()
    if existing_devices:
        for device in existing_devices:
            print(f"  - {device['device_name']}: {device['log_path']}")
    else:
        print("  (无)")

    print(f"\n准备添加 {len(devices_to_add)} 个设备:\n")

    added_count = 0
    skipped_count = 0

    for device_config in devices_to_add:
        device_name = device_config['device_name']
        log_path = device_config['log_path']

        try:
            # 检查设备是否已存在
            if DeviceConfig.exists(device_name):
                print(f"[SKIP] 跳过: {device_name} (已存在)")
                skipped_count += 1
                continue

            # 添加设备
            device = device_manager.add_device(device_config)
            print(f"[OK] 成功添加: {device_name} -> {log_path}")
            added_count += 1

        except Exception as e:
            print(f"[FAIL] 添加失败: {device_name} -> {str(e)}")

    print(f"\n添加完成: 成功 {added_count} 个, 跳过 {skipped_count} 个")

    # 显示更新后的设备列表
    print("\n更新后的设备列表:")
    updated_devices = device_manager.get_all_devices()
    if updated_devices:
        for device in updated_devices:
            status = "启用" if device.get('enabled', True) else "禁用"
            print(f"  - {device['device_name']}: {device['log_path']} [{status}]")
    else:
        print("  (无)")

if __name__ == "__main__":
    add_cd_ads_devices()