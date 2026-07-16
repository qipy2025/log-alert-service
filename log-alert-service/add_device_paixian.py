#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""添加"排线检测设备"：监控网络共享 \\10.146.175.53\\Log 上按日期命名的日志

特点：
  - UNC 网络共享路径，账号 Administrator / 密码 op（服务启动时 net use 自动建立会话）
  - 日志文件按日期命名（YYYY-MM-DD.log）
  - 只监控昨天 + 今天两个文件（monitor_days=2）

运行：./venv/Scripts/python.exe add_device_paixian.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows 控制台 UTF-8 输出
try:
    sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

from src.db.device_config import DeviceConfig
from src.device_manager import DeviceManager

DEVICE_CONFIG = {
    "device_name": "排线检测设备",
    "log_path": r"\\10.146.175.53\Log\上位机日志",
    "log_name_mode": "month_day_subdir",  # <base>/<YYYY-MM>/<YYYY-MM-DD>/Default.log
    "smb_username": "Administrator",
    "smb_password": "op",                # 明文，DeviceManager 内部 Base64 编码入库
    "monitor_days": 2,                   # 昨天 + 今天
    "enabled": True,
    "polling_interval": 5,               # 网络共享，轮询间隔适当放宽
    "encoding": "utf-8-sig",
}


def main():
    print("=" * 70)
    print("添加排线检测设备（网络共享 + 按日期文件名）")
    print("=" * 70)

    name = DEVICE_CONFIG["device_name"]

    # 已存在则先删除重建（保证配置最新）
    if DeviceConfig.exists(name):
        print(f"[INFO] 设备已存在，先删除旧记录: {name}")
        DeviceConfig.delete(name)

    try:
        manager = DeviceManager()
        device = manager.add_device(DEVICE_CONFIG)
        print(f"[OK] 设备添加成功: {name}")
        print(f"     日志路径: {device.get('log_path')}")
        print(f"     命名模式: {device.get('log_name_mode')}")
        print(f"     监控天数: {device.get('monitor_days')}")
        print(f"     共享账号: {device.get('smb_username')}")
        print(f"     轮询间隔: {device.get('polling_interval')}s")
        print(f"     密码(编码): {device.get('smb_password')}")
    except Exception as e:
        print(f"[FAIL] 添加设备失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print()
    print("=" * 70)
    print("下一步：")
    print("  1. 启动服务：./venv/Scripts/python.exe main.py --web")
    print("  2. 服务启动时会自动 net use 建立共享会话并开始轮询日志")
    print("  3. 访问 Web 界面：http://localhost:5000")
    print("=" * 70)


if __name__ == "__main__":
    main()
