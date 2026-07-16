#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重启监控系统以加载新设备配置"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("=" * 60)
    print("监控系统设备加载检查")
    print("=" * 60)

    print("\n当前数据库中的设备配置:")
    print("-" * 60)

    from src.db.device_config import DeviceConfig
    devices = DeviceConfig.get_all()

    if devices:
        enabled_count = 0
        for i, device in enumerate(devices, 1):
            status = "✓ 启用" if device.get('enabled', False) else "✗ 禁用"
            if device.get('enabled', False):
                enabled_count += 1
            print(f"{i}. {device['device_name']} - {status}")
            print(f"   路径: {device['log_path']}")
        print(f"\n总计: {len(devices)} 个设备，其中 {enabled_count} 个已启用")
    else:
        print("(无设备)")

    print("\n" + "=" * 60)
    print("启动监控系统:")
    print("=" * 60)
    print("如果监控系统尚未运行，请使用以下命令启动:")
    print()
    print("1. 只启动监控服务:")
    print("   python main.py")
    print()
    print("2. 启动监控+Web界面:")
    print("   python run_web.py")
    print()
    print("3. 使用启动脚本:")
    print("   Windows: start.bat")
    print("   Linux/Mac: ./start.sh")
    print()
    print("监控系统会自动从数据库加载启用的设备并开始监控。")
    print("=" * 60)

if __name__ == "__main__":
    main()