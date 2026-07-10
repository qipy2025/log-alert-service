import pytest
from datetime import datetime
from src.ai_analyzer import AIAnalyzer, AnalysisResult
from src.models import AlarmLevel, AlarmSource, AlarmEvent


def _make_event() -> AlarmEvent:
    return AlarmEvent(
        timestamp=datetime(2026, 6, 8, 21, 51, 36),
        alarm_text="右点胶阀缺胶报警_人工请马上更换",
        module_name="DesaySV.Presentation.Core.FrmMain",
        level=AlarmLevel.CRITICAL,
        source=AlarmSource.DEFAULT_LOG,
        line_number=319,
        log_file="Default.log",
        raw_line="2026-06-08 21:51:36,674 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换",
        context_lines=[
            "2026-06-08 21:51:34,189 [37] [GlueModule][751] - 热熔阀点胶回吸完成",
            "2026-06-08 21:51:36,674 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换",
            "2026-06-08 21:51:55,901 [6] [FrmMain][1742] - 报警复位操作",
        ],
        functional_log_context=[
            "[点胶交互流程.log] 2026-06-08 21:51:36,512 - 右点胶阀缺胶报警_人工请马上更换",
        ],
    )


class TestAIAnalyzer:
    def test_disabled_returns_none(self):
        """禁用 AI 分析时返回 None"""
        analyzer = AIAnalyzer(api_key="test", enabled=False)
        result = analyzer.analyze(_make_event())
        assert result is None

    def test_build_prompt_contains_alarm_info(self):
        """prompt 应包含告警信息"""
        analyzer = AIAnalyzer(api_key="test")
        event = _make_event()
        prompt = analyzer._build_prompt(event)
        assert "右点胶阀缺胶报警" in prompt
        assert "Default.log 上下文" in prompt
        assert "功能日志关联" in prompt

    def test_parse_valid_json(self):
        """解析有效的 JSON 响应"""
        analyzer = AIAnalyzer(api_key="test")
        text = '{"root_cause":"胶量不足","severity":"critical","suggestion":"更换胶桶","related_module":"点胶阀","probable_time_to_resolve":"10分钟"}'
        result = analyzer._parse_response(text)
        assert result is not None
        assert result.root_cause == "胶量不足"
        assert result.severity == "critical"
        assert result.suggestion == "更换胶桶"

    def test_parse_json_in_code_block(self):
        """解析被 ```json 包裹的 JSON"""
        analyzer = AIAnalyzer(api_key="test")
        text = '```json\n{"root_cause":"胶路堵塞","severity":"critical","suggestion":"检查胶路","related_module":"点胶阀","probable_time_to_resolve":"30分钟"}\n```'
        result = analyzer._parse_response(text)
        assert result is not None
        assert result.root_cause == "胶路堵塞"

    def test_parse_invalid_json(self):
        """解析无效 JSON 返回 None"""
        analyzer = AIAnalyzer(api_key="test")
        with pytest.raises(Exception):
            analyzer._parse_response("不是 JSON 内容")