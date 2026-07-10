from datetime import datetime
import pytest
from src.feishu_notifier import FeishuNotifier
from src.models import AlarmEvent, AlarmLevel, AlarmSource, AnalysisResult, DailySummary


def _make_event() -> AlarmEvent:
    return AlarmEvent(
        timestamp=datetime(2026, 6, 8, 21, 51, 36),
        alarm_text="右点胶阀缺胶报警_人工请马上更换",
        module_name="DesaySV.Presentation.Core.FrmMain",
        level=AlarmLevel.CRITICAL,
        source=AlarmSource.DEFAULT_LOG,
        line_number=319,
        log_file="Default.log",
        raw_line="...",
        context_lines=[
            "2026-06-08 21:51:34,189 - 热熔阀点胶回吸完成",
            "2026-06-08 21:51:36,674 - 右点胶阀缺胶报警_人工请马上更换",
        ],
        daily_count=3,
    )


class TestFeishuNotifier:
    def setup_method(self):
        self.notifier = FeishuNotifier(
            app_id="test_id",
            app_secret="test_secret",
            chats=[
                {"chat_id": "test_chat_1", "type": "debug", "name": "测试群"},
                {"chat_id": "test_chat_2", "type": "production", "name": "生产群"},
            ],
        )

    def test_build_alarm_card_without_analysis(self):
        """无 AI 分析的告警卡片"""
        event = _make_event()
        card = self.notifier._build_alarm_card(event)
        assert card["header"]["template"] == "red"
        assert "告警通知" in card["header"]["title"]["content"]
        assert "点胶设备" in card["header"]["title"]["content"]
        assert len(card["elements"]) >= 3  # 至少有 div + hr + note

    def test_build_alarm_card_with_analysis(self):
        """有 AI 分析的告警卡片"""
        event = _make_event()
        analysis = AnalysisResult(
            root_cause="胶量不足，建议更换胶桶",
            severity="critical",
            suggestion="1. 检查胶桶\n2. 更换胶桶",
            related_module="点胶阀",
            probable_time_to_resolve="10分钟",
        )
        card = self.notifier._build_alarm_card(event, analysis)
        assert "胶量不足" in str(card)
        assert len(card["elements"]) >= 5  # div + hr + div(AI分析) + hr + div(日志) + note

    def test_get_target_chats(self):
        """获取目标群"""
        production = self.notifier._get_target_chats("production")
        assert "test_chat_2" in production
        assert "test_chat_1" in production  # debug 群也包含

    def test_build_daily_report_card(self):
        """每日汇总卡片"""
        summary = DailySummary(
            date="2026-06-08",
            total_alarms=12,
            alarm_counts={"缺胶报警": 8, "缺胶预警": 3, "复位操作": 11},
            reset_counts=11,
            unresolved_alarms=6,
            summary_text="今日主要告警集中在右点胶阀缺胶。",
        )
        card = self.notifier._build_daily_report_card(summary)
        assert card["header"]["template"] == "blue"
        assert "2026-06-08" in card["header"]["title"]["content"]