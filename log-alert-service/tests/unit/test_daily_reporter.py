from datetime import datetime
import pytest
from src.daily_reporter import DailyReporter
from src.models import AlarmEvent, AlarmLevel, AlarmSource


def _make_alarm(text: str, level: AlarmLevel = AlarmLevel.CRITICAL) -> AlarmEvent:
    return AlarmEvent(
        timestamp=datetime(2026, 6, 8, 21, 51, 36),
        alarm_text=text,
        module_name="FrmMain",
        level=level,
        source=AlarmSource.DEFAULT_LOG,
        line_number=1,
        log_file="Default.log",
        raw_line=text,
    )


class TestDailyReporter:
    def test_get_summary_empty_day(self):
        """空日期的汇总"""
        reporter = DailyReporter(log_dir="/tmp")
        summary = reporter.get_summary("2026-06-08")
        assert summary.total_alarms == 0
        assert summary.reset_counts == 0

    def test_get_summary_with_alarms(self):
        """有告警的汇总"""
        reporter = DailyReporter(log_dir="/tmp")
        reporter.record_alarm(_make_alarm("右点胶阀缺胶报警"))
        reporter.record_alarm(_make_alarm("右点胶阀缺胶报警"))
        reporter.record_alarm(_make_alarm("报警复位操作", AlarmLevel.INFO))
        reporter.record_alarm(_make_alarm("左点胶阀缺胶预警", AlarmLevel.WARNING))

        summary = reporter.get_summary("2026-06-08")
        assert summary.total_alarms == 4
        assert summary.reset_counts == 1
        assert "右点胶阀缺胶报警" in summary.alarm_counts