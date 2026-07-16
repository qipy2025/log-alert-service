#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试告警检测功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.log_parser import parse_log_line, detect_alarm_level
from src.ai_analyzer import AIAnalyzer
from src.data_models import AlarmEvent, AlarmLevel
from datetime import datetime

print("=" * 80)
print("测试告警检测功能")
print("=" * 80)

# 1. 测试日志解析器
print("\n📝 测试日志解析器:")
print("-" * 80)

test_logs = [
    "2026-06-10 14:29:21,741 [  40] [DesaySV.Presentation.Core.FlowRelationStation][610] - 读取RFID信息失败,请人工检查处理，异常信息：System.ArgumentNullException: Array cannot be null.",
    "2026-06-10 07:50:17,763 [  41] [DesaySV.Presentation.Core.AssemblyStation][3907] - 工站1螺丝机_自动步骤：6000，工站索引[0]_电批返回信号异常-OK信号True,NG信号-False",
    "2026-06-10 00:35:34,840 [  16] [RunnerModel.FlowControlStation][394] - 中间流道1 上层流道自动步骤：240，前机台上层请求出料信号为true"
]

for i, log_line in enumerate(test_logs, 1):
    try:
        parsed = parse_log_line(log_line)

        if parsed:
            # 检查是否为告警
            alarm_level = detect_alarm_level(log_line)
            if alarm_level:
                print(f"✅ 日志 {i}: 检测到告警 ({alarm_level.value})")
                print(f"   内容: {log_line[:80]}...")
            else:
                print(f"⊙ 日志 {i}: 正常日志")
                print(f"   内容: {log_line[:80]}...")
        else:
            print(f"❌ 日志 {i}: 格式不匹配")

    except Exception as e:
        print(f"❌ 日志 {i}: 解析失败 - {e}")

# 2. 测试AI分析器
print("\n🤖 测试AI分析器:")
print("-" * 80)

try:
    # 检查AI配置
    from src.config_manager import ConfigManager
    config = ConfigManager('config.yaml')
    ai_config = config.get('ai_analysis', {})

    print(f"AI分析状态: {'启用' if ai_config.get('enabled', False) else '禁用'}")
    print(f"API地址: {ai_config.get('api_base_url', 'N/A')}")
    print(f"模型: {ai_config.get('model', 'N/A')}")

    # 创建测试告警事件
    test_event = AlarmEvent(
        timestamp=datetime.now(),
        alarm_text="读取RFID信息失败,请人工检查处理",
        module_name="打螺丝设备",
        level=AlarmLevel.WARNING,
        source=AlarmSource.DEFAULT_LOG,
        line_number=610,
        log_file="Default.log",
        raw_line="2026-06-10 14:29:21,741 [  40] [DesaySV.Presentation.Core.FlowRelationStation][610] - 读取RFID信息失败,请人工检查处理"
    )

    if ai_config.get('enabled', False):
        ai_analyzer = AIAnalyzer(
            api_key=ai_config.get('api_key', ''),
            api_base_url=ai_config.get('api_base_url', ''),
            model=ai_config.get('model', ''),
            enabled=True
        )

        print("\n正在分析测试告警...")
        analysis = ai_analyzer.analyze(test_event)

        if analysis:
            print(f"✅ AI分析完成:")
            print(f"   根本原因: {analysis.root_cause}")
            print(f"   严重程度: {analysis.severity}")
            print(f"   建议: {analysis.suggestion}")
        else:
            print("❌ AI分析失败")
    else:
        print("⚠️ AI分析已禁用，不会检测告警")

except Exception as e:
    print(f"❌ AI分析器测试失败: {e}")

# 3. 检查监控路径问题
print("\n🔍 监控路径问题分析:")
print("-" * 80)

print("问题分析:")
print("1. 当前日期: 2026-07-13")
print("2. 日志文件日期: 2026-06-10")
print("3. 监控系统正在查找: {设备路径}/2026-07-13/")
print("4. 实际日志位置: {设备路径}/2026-06-10/")
print()
print("结论: 监控系统无法检测到历史日志，因为:")
print("  • 系统只监控当前日期的日志目录")
print("  • 历史日志不在监控范围内")
print("  • 需要实时生成新的日志才会被检测")

print("\n" + "=" * 80)
print("💡 解决方案:")
print("=" * 80)
print("1. 等待设备生成今天的日志文件")
print("2. 或者手动创建今天的日志目录并复制一些测试日志")
print("3. 或者修改监控配置以监控历史日志")
print("=" * 80)