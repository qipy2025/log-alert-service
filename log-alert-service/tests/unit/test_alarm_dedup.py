import time
import pytest
from datetime import datetime
from src.alarm_dedup import AlarmDedup
from src.models import AlarmLevel, AlarmSource, AlarmEvent


def _make_event(alarm_text: str, module: str = "TestModule") -> AlarmEvent:
    return AlarmEvent(
        timestamp=datetime.now(),
        alarm_text=alarm_text,
        module_name=module,
        level=AlarmLevel.CRITICAL,
        source=AlarmSource.DEFAULT_LOG,
        line_number=1,
        log_file="Default.log",
        raw_line=alarm_text,
    )


class TestAlarmDedup:
    def test_first_alarm_notifies(self):
        """首次告警应推送"""
        dedup = AlarmDedup(window_seconds=300)
        event = _make_event("右点胶阀缺胶报警")
        assert dedup.should_notify(event) is True

    def test_same_alarm_in_window_does_not_notify(self):
        """窗口内相同告警不应推送"""
        dedup = AlarmDedup(window_seconds=300)
        event = _make_event("右点胶阀缺胶报警")
        assert dedup.should_notify(event) is True
        assert dedup.should_notify(event) is False
        assert dedup.should_notify(event) is False

    def test_different_alarms_both_notify(self):
        """不同告警都应推送"""
        dedup = AlarmDedup(window_seconds=300)
        e1 = _make_event("右点胶阀缺胶报警")
        e2 = _make_event("左点胶阀缺胶报警")
        assert dedup.should_notify(e1) is True
        assert dedup.should_notify(e2) is True

    def test_same_alarm_after_window_expiry(self):
        """窗口过期后相同告警应再次推送"""
        dedup = AlarmDedup(window_seconds=1)
        event = _make_event("右点胶阀缺胶报警")
        assert dedup.should_notify(event) is True
        assert dedup.should_notify(event) is False
        time.sleep(1.1)
        assert dedup.should_notify(event) is True

    def test_repeat_count_tracking(self):
        """重复次数跟踪"""
        dedup = AlarmDedup(window_seconds=300)
        event = _make_event("右点胶阀缺胶报警")
        assert dedup.get_repeat_count(event) == 0
        dedup.should_notify(event)
        assert dedup.get_repeat_count(event) == 1
        dedup.should_notify(event)
        assert dedup.get_repeat_count(event) == 2

    def test_cleanup_removes_stale_entries(self):
        """清理应移除过期条目"""
        dedup = AlarmDedup(window_seconds=300)
        event = _make_event("右点胶阀缺胶报警")
        dedup.should_notify(event)
        assert len(dedup._cache) == 1
        time.sleep(0.1)  # 等待时间戳增长
        dedup.cleanup(max_age=0)  # 清理所有
        assert len(dedup._cache) == 0