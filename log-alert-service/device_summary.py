#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成CD-ADS-1设备管理总结报告"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.db.device_config import DeviceConfig
from src.db.cache import get_device_status
import glob

devices = DeviceConfig.get_all()

print("=" * 80)
print("CD-ADS-1 设备管理总结报告")
print("=" * 80)
print(f"生成时间: 2026-07-13")
print(f"设备总数: {len(devices)} 个")
print("=" * 80)

for i, device in enumerate(devices, 1):
    device_name = device['device_name']
    log_path = device['log_path']

    print(f"\n【设备 {i}】{device_name}")
    print("-" * 80)
    print(f"日志路径: {log_path}")
    print(f"启用状态: {'✓ 启用' if device.get('enabled', True) else '✗ 禁用'}")
    print(f"自动通知: {'✓ 是' if device.get('auto_notify', False) else '✗ 否'}")
    print(f"轮询间隔: {device.get('polling_interval', 2)} 秒")
    print(f"文件编码: {device.get('encoding', 'utf-8-sig')}")

    # 检查日志文件存在性
    print(f"日志文件检查:")

    # 检查不同日期的日志目录
    log_dirs = glob.glob(os.path.join(log_path, "*"))
    log_dirs = [d for d in log_dirs if os.path.isdir(d)]

    if log_dirs:
        for log_dir in sorted(log_dirs)[-3:]:  # 显示最近3个日期
            date_folder = os.path.basename(log_dir)
            log_files = glob.glob(os.path.join(log_dir, "*.log"))
            file_count = len(log_files)
            print(f"  - {date_folder}/: {file_count} 个日志文件")

            # 显示最近几个日志文件
            if log_files:
                recent_files = sorted(log_files, key=os.path.getmtime, reverse=True)[:3]
                for log_file in recent_files:
                    file_name = os.path.basename(log_file)
                    file_size = os.path.getsize(log_file)
                    print(f"    • {file_name} ({file_size:,} bytes)")
    else:
        print(f"  ⚠ 未找到日志目录")

    # 检查设备运行状态
    try:
        status = get_device_status(device_name)
        current_status = status.get('status', 'UNKNOWN')
        print(f"监控状态: {current_status}")
    except Exception as e:
        print(f"监控状态: 检查失败 - {str(e)}")

print("\n" + "=" * 80)
print("配置说明:")
print("=" * 80)
print("• 所有设备已添加到设备管理系统")
print("• 设备默认启用，需要通过Web界面或API启动监控")
print("• 自动通知功能默认关闭，可按需启用")
print("• 日志文件按日期分目录存储，便于历史数据管理")
print("• 支持 Default.log 和各种工站日志文件的监控")
print("=" * 80)