#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试告警处理流程"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime
from src.data_models import AlarmEvent, AlarmLevel, AlarmSource
from src.config_manager import ConfigManager
from src.feishu_notifier import FeishuNotifier
from src.alarm_dedup import AlarmDedup

print("=" * 80)
print("告警处理流程测试")
print("=" * 80)

# 1. 测试通知配置检查
print("\n📋 步骤1: 通知配置检查")
print("-" * 80)

try:
    from src.db.notification_config_db import get_notification_config
    config = get_notification_config()

    if config:
        print(f"通知总开关: {'启用' if config.enabled else '禁用'}")
        print(f"允许的告警级别: {config.allowed_levels}")
    else:
        print("❌ 未找到通知配置")

except Exception as e:
    print(f"❌ 获取通知配置失败: {e}")

# 2. 创建测试告警事件
print("\n🚨 步骤2: 创建测试告警事件")
print("-" * 80)

try:
    test_event = AlarmEvent(
        timestamp=datetime.now(),
        alarm_text="报警_测试飞书通知流程验证",
        module_name="测试设备",
        level=AlarmLevel.CRITICAL,
        source=AlarmSource.DEFAULT_LOG,
        line_number=999,
        log_file="test.log",
        raw_line="2026-07-13 11:45:00,000 [999] [Test][999] - 报警_测试飞书通知流程验证"
    )

    print(f"告警级别: {test_event.level.value}")
    print(f"告警内容: {test_event.alarm_text}")

except Exception as e:
    print(f"❌ 创建告警事件失败: {e}")
    sys.exit(1)

# 3. 测试通知配置检查逻辑
print("\n🔍 步骤3: 测试通知配置检查逻辑")
print("-" * 80)

try:
    from src.db.notification_config_db import get_notification_config

    notification_config = get_notification_config()

    # 模拟 _should_send_notification 逻辑
    if not notification_config or not notification_config.enabled:
        print("❌ 通知总开关关闭，不会发送通知")
    elif not notification_config.allowed_levels or test_event.level.value not in notification_config.allowed_levels:
        print(f"❌ 告警级别 {test_event.level.value} 不在允许列表中")
        print(f"   允许的级别: {notification_config.allowed_levels}")
    else:
        print("✅ 通知配置检查通过，应该发送通知")

except Exception as e:
    print(f"❌ 通知配置检查失败: {e}")

# 4. 测试飞书通知发送
print("\n📤 步骤4: 测试飞书通知发送")
print("-" * 80)

try:
    config_manager = ConfigManager('config.yaml')
    feishu_config = config_manager.get('feishu', {})

    notifier = FeishuNotifier(
        app_id=feishu_config.get('app_id', ''),
        app_secret=feishu_config.get('app_secret', ''),
        chats=feishu_config.get('chats', [])
    )

    print("正在发送飞书通知...")
    success = notifier.send_alarm(test_event, None)

    if success:
        print("✅ 飞书通知发送成功！")
    else:
        print("❌ 飞书通知发送失败")

except Exception as e:
    print(f"❌ 发送飞书通知时出错: {e}")
    import traceback
    traceback.print_exc()

# 5. 检查告警去重
print("\n🔄 步骤5: 检查告警去重逻辑")
print("-" * 80)

try:
    dedup = AlarmDedup(window_seconds=300, max_repeat=99)

    # 测试去重检查
    should_notify = dedup.should_notify(test_event)

    if should_notify:
        print("✅ 告警通过去重检查，应该通知")
    else:
        print("❌ 告警被去重过滤，不会通知")

except Exception as e:
    print(f"❌ 去重检查失败: {e}")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)