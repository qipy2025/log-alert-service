"""每日汇总集成测试"""
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest

from src.models import AlarmEvent, AlarmLevel, AlarmSource, DailySummary
from src.daily_reporter import DailyReporter
from src.feishu_notifier import FeishuNotifier
from tests.mocks import MockFeishuAPI

class TestDailyReport:
    """每日汇总测试"""

    def test_4_1_daily_summary_trigger(self):
        """场景4.1：每日汇总触发"""
        # 1. 创建日报记录器
        reporter = DailyReporter(log_dir="/tmp")

        # 2. 当日发送10个不同类型的告警
        today = datetime(2026, 7, 9, 10, 0, 0)
        date_key = today.strftime("%Y-%m-%d")

        alarm_types = [
            ("右点胶阀缺胶报警", AlarmLevel.CRITICAL),
            ("左点胶阀缺胶预警", AlarmLevel.WARNING),
            ("报警复位操作", AlarmLevel.INFO),
        ]

        for i, (text, level) in enumerate(alarm_types * 3):  # 产生多个告警
            event = AlarmEvent(
                timestamp=today + timedelta(seconds=i*10),
                alarm_text=text,
                module_name="FrmMain",
                level=level,
                source=AlarmSource.DEFAULT_LOG,
                line_number=1,
                log_file="Default.log",
                raw_line=text,
            )
            reporter.record_alarm(event)

        # 3. 手动触发每日汇总任务
        summary = reporter.get_summary(date_key)

        # 4. 验证汇总
        assert summary.date == date_key
        assert summary.total_alarms == 9
        assert summary.reset_counts >= 3  # 至少3个复位操作
        assert len(summary.alarm_counts) > 0

        # 5. 验证按类型分组
        assert "右点胶阀缺胶报警" in summary.alarm_counts
        assert summary.alarm_counts["右点胶阀缺胶报警"] == 3

        # 6. 验证飞书推送格式
        with patch('src.feishu_notifier.requests.post') as mock_post:
            mock_post.return_value = MockFeishuAPI.success_response()

            notifier = FeishuNotifier(
                app_id="test",
                app_secret="test",
                chats=[{"chat_id": "test", "type": "production", "name": "测试群"}],
            )

            # 构建 daily report 卡片
            card = notifier._build_daily_report_card(summary)
            assert card is not None
            assert "header" in card
            assert "elements" in card

    def test_4_2_empty_day_summary(self):
        """场景4.2：空日汇总"""
        # 1. 创建日报记录器
        reporter = DailyReporter(log_dir="/tmp")

        # 2. 当日无告警发生
        date_key = "2026-07-09"

        # 3. 触发每日汇总任务
        summary = reporter.get_summary(date_key)

        # 4. 验证
        assert summary.total_alarms == 0
        assert summary.reset_counts == 0
        assert len(summary.alarm_counts) == 0

        # 5. 验证飞书推送
        with patch('src.feishu_notifier.requests.post') as mock_post:
            mock_post.return_value = MockFeishuAPI.success_response()

            notifier = FeishuNotifier(
                app_id="test",
                app_secret="test",
                chats=[{"chat_id": "test", "type": "production", "name": "测试群"}],
            )

            # 构建 daily report 卡片
            card = notifier._build_daily_report_card(summary)
            assert card is not None
            # 应该成功推送，即使无告警
            assert "header" in card
