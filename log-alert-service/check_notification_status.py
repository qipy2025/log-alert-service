#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查飞书通知状态"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.db.notification_config_db import get_notification_config
from src.db.mysql import get_db_session
from src.models.alarm import AlarmRecord
from src.config_manager import ConfigManager

print("=" * 80)
print("飞书通知状态检查")
print("=" * 80)

# 1. 检查通知配置
print("\n📢 通知配置状态:")
print("-" * 80)

try:
    config = get_notification_config()
    if config:
        print(f"总开关: {'✅ 启用' if config.enabled else '❌ 禁用'}")
        print(f"允许的告警级别: {config.allowed_levels}")
        print(f"配置时间: {config.created_at}")

        if not config.enabled:
            print("\n⚠️ 通知总开关已禁用，告警不会发送到飞书！")
    else:
        print("❌ 未找到通知配置（使用默认禁用状态）")
except Exception as e:
    print(f"❌ 获取通知配置失败: {e}")

# 2. 检查飞书配置
print("\n📱 飞书配置:")
print("-" * 80)

try:
    config_manager = ConfigManager('config.yaml')
    feishu_config = config_manager.get('feishu', {})

    app_id = feishu_config.get('app_id', '')
    app_secret = feishu_config.get('app_secret', '')
    chats = feishu_config.get('chats', [])

    print(f"App ID: {'已配置' if app_id and app_id != '${FEISHU_APP_ID}' else '❌ 未配置'}")
    print(f"App Secret: {'已配置' if app_secret and app_secret != '${FEISHU_APP_SECRET}' else '❌ 未配置'}")
    print(f"配置的群聊数量: {len(chats)}")

    if chats:
        for i, chat in enumerate(chats, 1):
            print(f"  {i}. {chat.get('name', 'Unknown')} ({chat.get('type', 'Unknown')})")
            print(f"     Chat ID: {chat.get('chat_id', 'N/A')}")

except Exception as e:
    print(f"❌ 获取飞书配置失败: {e}")

# 3. 检查告警通知状态
print("\n🚨 告警通知状态:")
print("-" * 80)

try:
    session = get_db_session()
    try:
        # 查询最近的告警
        recent_alarms = session.query(AlarmRecord).order_by(
            AlarmRecord.log_timestamp.desc()
        ).limit(10).all()

        print(f"最近 {len(recent_alarms)} 条告警的通知状态:")

        notified_count = 0
        not_notified_count = 0

        for alarm in recent_alarms:
            status = "✅ 已通知" if alarm.notified else "❌ 未通知"
            if alarm.notified:
                notified_count += 1
            else:
                not_notified_count += 1

            print(f"  {alarm.device_name} - {alarm.alarm_level}: {status}")
            print(f"    内容: {alarm.alarm_content[:50]}...")
            print(f"    时间: {alarm.log_timestamp}")

        print(f"\n总计: {notified_count} 条已通知, {not_notified_count} 条未通知")

    finally:
        session.close()

except Exception as e:
    print(f"❌ 查询告警状态失败: {e}")

# 4. 分析结果
print("\n" + "=" * 80)
print("📊 分析结果:")
print("=" * 80)

print("🔍 可能的原因:")
print("1. 通知总开关已禁用 - 需要在Web界面启用")
print("2. 飞书配置未完成 - 需要配置App ID和Secret")
print("3. 告警级别过滤 - 告警级别可能不在允许列表中")
print("4. AI分析功能 - 可能影响告警通知逻辑")

print("\n💡 解决方案:")
print("1. 访问Web界面: http://localhost:5000")
print("2. 进入通知配置页面")
print("3. 启用通知总开关")
print("4. 设置允许的告警级别 (如: CRITICAL, WARNING)")
print("5. 确保飞书App配置正确")

print("\n" + "=" * 80)