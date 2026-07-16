#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""添加"打螺丝设备"：监控网络共享 \\10.146.175.66\\log（账号密码与排线检测设备一致）

运行：./venv/Scripts/python.exe add_device_daluosi.py
"""
import glob
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

from src.db.device_config import DeviceConfig
from src.device_manager import DeviceManager
from src.network_share import ensure_share_connection

DEVICE_CONFIG = {
    "device_name": "打螺丝设备",
    "log_path": r"\\10.146.175.66\log",
    "log_name_mode": "root_multi_subdir",  # base/*/<YYYY-MM>/<YYYY-MM-DD>/*.log
    "smb_username": "Administrator",
    "smb_password": "op",
    "monitor_days": 2,                     # 昨天 + 今天
    "enabled": True,
    "polling_interval": 5,
    "encoding": "utf-8-sig",
}


def main():
    print("=" * 70)
    print("添加打螺丝设备（网络共享）")
    print("=" * 70)

    name = DEVICE_CONFIG["device_name"]
    if DeviceConfig.exists(name):
        print(f"[INFO] 设备已存在，先删除旧记录: {name}")
        DeviceConfig.delete(name)

    try:
        DeviceManager().add_device(DEVICE_CONFIG)
        print(f"[OK] 设备添加成功: {name} -> {DEVICE_CONFIG['log_path']}")
    except Exception as e:
        print(f"[FAIL] 添加设备失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 探测目录结构，验证 root_multi_subdir 是否匹配
    base = DEVICE_CONFIG["log_path"]
    ok = ensure_share_connection(base, DEVICE_CONFIG["smb_username"], DEVICE_CONFIG["smb_password"])
    print(f"\n网络共享连接: {'成功' if ok else '失败'}")
    if ok:
        now = datetime.now()
        for d in range(DEVICE_CONFIG["monitor_days"]):
            dt = now - timedelta(days=d)
            pattern = os.path.join(base, "*", dt.strftime("%Y-%m"), dt.strftime("%Y-%m-%d"), "*.log")
            matches = sorted(glob.glob(pattern))
            print(f"  {dt.strftime('%Y-%m-%d')}: 匹配 {len(matches)} 个 .log 文件")
            for m in matches[:10]:
                print("    ", m.replace(base, ""))


if __name__ == "__main__":
    main()
