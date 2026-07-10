import tempfile
import time
from pathlib import Path
import pytest
from src.file_watcher import LogFileHandler, LogWatcher
from src.models import AlarmLevel


class TestLogFileHandler:
    def test_process_new_lines_detects_alarm(self):
        """新写入的告警行应被检测"""
        alarms = []

        def callback(event):
            alarms.append(event)

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            log_path.write_text(
                "2026-06-08 21:51:30,072 [37] [Module][233] - 轨迹数据\n",
                encoding="utf-8",
            )

            handler = LogFileHandler(
                default_log_file=str(log_path),
                on_alarm=callback,
            )

            # 追加告警行
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("2026-06-08 21:51:36,674 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换\n")

            handler._process_new_lines(str(log_path))
            assert len(alarms) == 1
            assert alarms[0].level == AlarmLevel.CRITICAL

    def test_no_alarm_no_callback(self):
        """非告警行不触发回调"""
        alarms = []

        def callback(event):
            alarms.append(event)

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            log_path.write_text("", encoding="utf-8")

            handler = LogFileHandler(
                default_log_file=str(log_path),
                on_alarm=callback,
            )

            with open(log_path, "a", encoding="utf-8") as f:
                f.write("2026-06-08 21:51:30,072 [37] [Module][233] - 轨迹数据\n")

            handler._process_new_lines(str(log_path))
            assert len(alarms) == 0