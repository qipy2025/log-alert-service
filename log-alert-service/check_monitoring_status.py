#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查监控系统状态和告警情况"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.db.device_config import DeviceConfig
from src.db.cache import get_device_status
from src.db.mysql import get_db_session
from src.models.alarm import AlarmRecord
from datetime import datetime, timedelta

print("=" * 80)
print("监控系统状态检查")
print("=" * 80)

# 1. 检查设备状态
print("\n📊 设备监控状态:")
print("-" * 80)

devices = DeviceConfig.get_all()
for device in devices:
    device_name = device['device_name']
    try:
        status = get_device_status(device_name)
        monitor_status = status.get('status', 'UNKNOWN')
        print(f"  {device_name}: {monitor_status}")
    except:
        print(f"  {device_name}: 状态获取失败")

# 2. 检查告警记录
print("\n🚨 告警记录:")
print("-" * 80)

try:
    session = get_db_session()
    try:
        # 查询今天的告警
        today = datetime.now().strftime('%Y-%m-%d')
        today_alarms = session.query(AlarmRecord).filter(
            AlarmRecord.log_timestamp >= today
        ).count()

        # 查询所有告警
        all_alarms = session.query(AlarmRecord).count()

        # 查询最近的告警
        recent_alarms = session.query(AlarmRecord).order_by(
            AlarmRecord.log_timestamp.desc()
        ).limit(5).all()

        print(f"  今日告警数: {today_alarms}")
        print(f"  历史告警总数: {all_alarms}")

        if recent_alarms:
            print(f"\n  最近告警记录:")
            for alarm in recent_alarms:
                print(f"    - {alarm.device_name}: {alarm.alarm_text}")
                print(f"      时间: {alarm.log_timestamp}, 级别: {alarm.alarm_level}")
        else:
            print(f"  没有告警记录")

    finally:
        session.close()

except Exception as e:
    print(f"  查询告警记录失败: {e}")

# 3. 检查通知配置
print("\n📢 通知配置:")
print("-" * 80)

try:
    from src.db.notification_config_db import get_notification_config
    config = get_notification_config()

    if config:
        print(f"  总开关: {'启用' if config.enabled else '禁用'}")
        print(f"  允许的告警级别: {config.allowed_levels}")
    else:
        print(f"  未配置通知（使用默认设置）")

except Exception as e:
    print(f"  获取通知配置失败: {e}")

# 4. 检查日志文件
print("\n📁 日志文件检查:")
print("-" * 80)

import glob
import os

for device in devices:
    device_name = device['device_name']
    log_path = device['log_path']

    print(f"\n  {device_name}:")

    if os.path.exists(log_path):
        # 检查最新的日志目录
        date_dirs = [d for d in os.listdir(log_path) if os.path.isdir(os.path.join(log_path, d))]
        if date_dirs:
            latest_date = sorted(date_dirs)[-1]
            latest_dir = os.path.join(log_path, latest_date)

            log_files = glob.glob(os.path.join(latest_dir, "*.log"))
            print(f"    最新日志目录: {latest_date}")
            print(f"    日志文件数: {len(log_files)}")

            # 检查是否有最新的日志
            if log_files:
                latest_log = sorted(log_files, key=os.path.getmtime, reverse=True)[0]
                mtime = os.path.getmtime(latest_log)
                mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                file_size = os.path.getsize(latest_log)

                print(f"    最新文件: {os.path.basename(latest_log)}")
                print(f"    文件大小: {file_size:,} bytes")
                print(f"    修改时间: {mtime_str}")
        else:
            print(f"    没有日志目录")
    else:
        print(f"    路径不存在")

print("\n" + "=" * 80)
print("📝 说明:")
print("=" * 80)
print("• 如果设备状态显示 RUNNING，表示监控系统正在运行")
print("• 如果没有告警记录，可能原因:")
print("  1. 历史日志中没有异常内容")
print("  2. AI分析器未检测到需要告警的问题")
print("  3. 日志格式不符合解析规则")
print("• 建议查看实时日志生成情况，或手动添加测试告警")
print("=" * 80)