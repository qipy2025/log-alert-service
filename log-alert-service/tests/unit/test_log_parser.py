import pytest
from datetime import datetime
from src.log_parser import (
    parse_log_line,
    detect_alarm_level,
    create_alarm_event,
)
from src.models import AlarmLevel, AlarmSource


class TestParseLogLine:
    def test_parse_normal_line(self):
        """测试解析正常的 Default.log 行"""
        line = "2026-06-08 21:51:55,901 [   6] [DesaySV.Presentation.Core.FrmMain][1742] - 报警复位操作"
        result = parse_log_line(line)
        assert result is not None
        assert result["thread_id"] == 6
        assert result["class_name"] == "DesaySV.Presentation.Core.FrmMain"
        assert result["line_number"] == 1742
        assert result["message"] == "报警复位操作"

    def test_parse_alarm_line(self):
        """测试解析告警行"""
        line = "2026-06-08 21:51:36,674 [   1] [DesaySV.Presentation.Core.FrmMain][319] - 点胶交互流程:右点胶阀缺胶报警_人工请马上更换"
        result = parse_log_line(line)
        assert result is not None
        assert "缺胶报警" in result["message"]

    def test_parse_invalid_line(self):
        """测试不匹配格式的行"""
        line = "这是一行无效日志"
        assert parse_log_line(line) is None

    def test_parse_empty_line(self):
        """测试空行"""
        assert parse_log_line("") is None


class TestDetectAlarmLevel:
    def test_critical_alarm(self):
        """检测 critical 级别告警"""
        assert detect_alarm_level("右点胶阀缺胶报警_人工请马上更换") == AlarmLevel.CRITICAL

    def test_warning_alarm(self):
        """检测 warning 级别告警"""
        assert detect_alarm_level("右点胶阀缺胶预警_人工请及时更换") == AlarmLevel.WARNING

    def test_reset_operation(self):
        """检测复位操作"""
        assert detect_alarm_level("报警复位操作") == AlarmLevel.INFO

    def test_no_alarm(self):
        """非告警消息返回 None"""
        assert detect_alarm_level("轨迹数据3动作") is None

    def test_functional_log_critical(self):
        """功能日志 critical 告警"""
        assert detect_alarm_level(
            "右点胶阀缺胶报警_人工请马上更换", is_functional_log=True
        ) == AlarmLevel.CRITICAL


class TestCreateAlarmEvent:
    def test_create_from_parsed_line(self):
        """从解析行创建告警事件"""
        parsed = {
            "timestamp": datetime(2026, 6, 8, 21, 51, 36),
            "thread_id": 1,
            "class_name": "DesaySV.Presentation.Core.FrmMain",
            "line_number": 319,
            "message": "右点胶阀缺胶报警_人工请马上更换",
            "raw_line": "2026-06-08 21:51:36,674 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换",
        }
        event = create_alarm_event(parsed, "Default.log")
        assert event is not None
        assert event.level == AlarmLevel.CRITICAL
        assert event.module_name == "DesaySV.Presentation.Core.FrmMain"
        assert event.log_file == "Default.log"

    def test_non_alarm_returns_none(self):
        """非告警行返回 None"""
        parsed = {
            "timestamp": datetime(2026, 6, 8, 21, 51, 30),
            "thread_id": 37,
            "class_name": "DesaySV.Presentation.Core.GlueModule",
            "line_number": 233,
            "message": "轨迹数据3动作",
            "raw_line": "...",
        }
        assert create_alarm_event(parsed, "Default.log") is None