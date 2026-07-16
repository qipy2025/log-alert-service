#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试飞书通知功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime
from src.config_manager import ConfigManager
from src.feishu_notifier import FeishuNotifier
from src.data_models import AlarmEvent, AlarmLevel, AlarmSource
from src.ai_analyzer import AIAnalyzer

print("=" * 80)
print("飞书通知功能测试")
print("=" * 80)

# 1. 测试飞书配置
print("\n📱 步骤1: 检查飞书配置")
print("-" * 80)

try:
    config = ConfigManager('config.yaml')
    feishu_config = config.get('feishu', {})

    app_id = feishu_config.get('app_id', '')
    app_secret = feishu_config.get('app_secret', '')
    chats = feishu_config.get('chats', [])

    print(f"App ID: {app_id[:20]}... (已截断)")
    print(f"App Secret: {app_secret[:20]}... (已截断)")
    print(f"配置群聊数: {len(chats)}")

    # 找到生产环境群聊
    production_chat = None
    for chat in chats:
        if chat.get('type') == 'production':
            production_chat = chat
            break

    if production_chat:
        print(f"生产群聊: {production_chat.get('name')}")
    else:
        print("⚠️ 未找到生产类型群聊")

except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    sys.exit(1)

# 2. 创建通知器
print("\n🔧 步骤2: 创建飞书通知器")
print("-" * 80)

try:
    notifier = FeishuNotifier(
        app_id=app_id,
        app_secret=app_secret,
        chats=chats
    )
    print("✅ 飞书通知器创建成功")

except Exception as e:
    print(f"❌ 创建通知器失败: {e}")
    sys.exit(1)

# 3. 创建测试告警事件
print("\n🚨 步骤3: 创建测试告警事件")
print("-" * 80)

try:
    test_event = AlarmEvent(
        timestamp=datetime.now(),
        alarm_text="测试告警：设备监控系统飞书通知功能测试",
        module_name="测试设备",
        level=AlarmLevel.CRITICAL,
        source=AlarmSource.DEFAULT_LOG,
        line_number=999,
        log_file="test.log",
        raw_line="2026-07-13 11:30:00,000 [999] [Test][999] - 测试告警：设备监控系统飞书通知功能测试"
    )

    print(f"告警级别: {test_event.level.value}")
    print(f"告警内容: {test_event.alarm_text}")
    print(f"设备名称: {test_event.module_name}")

except Exception as e:
    print(f"❌ 创建告警事件失败: {e}")
    sys.exit(1)

# 4. 测试AI分析（可选）
print("\n🤖 步骤4: AI分析 (可选)")
print("-" * 80)

try:
    ai_config = config.get('ai_analysis', {})
    if ai_config.get('enabled', False):
        ai_analyzer = AIAnalyzer(
            api_key=ai_config.get('api_key', ''),
            api_base_url=ai_config.get('api_base_url', ''),
            model=ai_config.get('model', ''),
            enabled=True
        )

        print("正在进行AI分析...")
        analysis = ai_analyzer.analyze(test_event)

        if analysis:
            print("✅ AI分析完成:")
            print(f"   根本原因: {analysis.root_cause}")
            print(f"   严重程度: {analysis.severity}")
        else:
            print("⚠️ AI分析返回空结果")
    else:
        print("⚠️ AI分析已禁用")
        analysis = None

except Exception as e:
    print(f"⚠️ AI分析失败: {e}")
    analysis = None

# 5. 发送飞书通知
print("\n📤 步骤5: 发送飞书通知")
print("-" * 80)

try:
    print("正在发送测试告警到飞书...")
    success = notifier.send_alarm(test_event, analysis)

    if success:
        print("✅ 飞书通知发送成功!")
        print("请检查飞书群聊是否收到测试告警消息")
    else:
        print("❌ 飞书通知发送失败")

except Exception as e:
    print(f"❌ 发送通知时出错: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)