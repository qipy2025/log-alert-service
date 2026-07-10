import tempfile
from datetime import datetime
from pathlib import Path
import pytest

from src.context_collector import (
    read_lines,
    extract_context,
    find_related_functional_logs,
    collect_context,
)
from src.models import AlarmLevel, AlarmSource, AlarmEvent


SAMPLE_LINES = [
    "2026-06-08 21:51:30,072 [  37] [Module1][233] - 轨迹数据3动作",
    "2026-06-08 21:51:30,104 [  37] [Module1][233] - 轨迹数据4动作",
    "2026-06-08 21:51:30,136 [  37] [Module1][233] - 轨迹数据5动作",
    "2026-06-08 21:51:36,674 [   1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换",
    "2026-06-08 21:51:55,901 [   6] [FrmMain][1742] - 报警复位操作",
    "2026-06-08 21:52:04,619 [   6] [FrmMain][1742] - 报警复位操作",
]


class TestContextCollector:
    def test_read_lines(self):
        """测试读取和解析日志行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            with open(log_path, "w", encoding="utf-8") as f:
                for line in SAMPLE_LINES:
                    f.write(line + "\n")

            lines = read_lines(str(log_path))
            assert len(lines) == 6
            # 验证解析成功的行
            parsed_count = sum(1 for _, _, p in lines if p is not None)
            assert parsed_count == 6

    def test_extract_context(self):
        """测试上下文提取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            with open(log_path, "w", encoding="utf-8") as f:
                for line in SAMPLE_LINES:
                    f.write(line + "\n")

            lines = read_lines(str(log_path))
            # 提取索引 3（告警行）前后各 2 行
            ctx = extract_context(lines, 3, context_lines=2)
            assert len(ctx) <= 5  # start=1, end=6
            assert "缺胶报警" in " ".join(ctx)

    def test_collect_context_sets_context_lines(self):
        """collect_context 应填充 context_lines"""
        event = AlarmEvent(
            timestamp=datetime(2026, 6, 8, 21, 51, 36),
            alarm_text="右点胶阀缺胶报警_人工请马上更换",
            module_name="FrmMain",
            level=AlarmLevel.CRITICAL,
            source=AlarmSource.DEFAULT_LOG,
            line_number=319,
            log_file="Default.log",
            raw_line=SAMPLE_LINES[3],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            with open(log_path, "w", encoding="utf-8") as f:
                for line in SAMPLE_LINES:
                    f.write(line + "\n")

            result = collect_context(event, str(tmpdir), max_context_lines=2)
            assert len(result.context_lines) > 0