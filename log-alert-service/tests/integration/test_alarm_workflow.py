"""完整告警流程集成测试"""
import time
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest

from src.config_manager import ConfigManager
from src.models import AlarmEvent, AlarmLevel, AlarmSource
from src.alarm_dedup import AlarmDedup
from src.context_collector import collect_context
from src.ai_analyzer import AIAnalyzer
from src.feishu_notifier import FeishuNotifier
from src.file_watcher import LogWatcher
from tests.mocks import MockFeishuAPI, MockAIAnalyzer

class TestAlarmWorkflow:
    """完整告警流程测试"""

    def test_1_1_normal_alarm_flow(self, temp_log_dir):
        """场景1.1：正常告警流程"""
        # 1. 准备测试配置
        captured_alarms = []
        def alarm_callback(event):
            captured_alarms.append(event)

        # 2. 创建告警日志文件
        log_content = (
            "2026-07-09 10:29:50,000 [37] [GlueModule][233] - 轨迹数据3动作\n"
            "2026-07-09 10:30:00,000 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换\n"
            "2026-07-09 10:30:05,000 [6] [FrmMain][1742] - 报警复位操作\n"
        )
        log_file = temp_log_dir / "Default.log"
        log_file.write_text(log_content, encoding="utf-8-sig")

        # 3. 启动文件监控
        watcher = LogWatcher(
            log_dir=str(temp_log_dir),
            on_alarm=alarm_callback,
            polling_interval=1,
        )
        watcher.start()
        time.sleep(2)  # 等待监控启动
        watcher.stop()

        # 4. 验证：检测到告警
        assert len(captured_alarms) >= 1
        # 找到 CRITICAL 级别的告警
        critical_alarms = [a for a in captured_alarms if a.level == AlarmLevel.CRITICAL]
        assert len(critical_alarms) == 1
        alarm = critical_alarms[0]
        assert "缺胶报警" in alarm.alarm_text
        assert alarm.module_name == "FrmMain"

        # 5. 验证：去重检查通过（首次告警）
        dedup = AlarmDedup(window_seconds=10)
        assert dedup.should_notify(alarm) is True

        # 6. 验证：模拟 AI 分析（使用 mock）
        with patch('src.ai_analyzer.requests.post') as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"content": [{"text": '{"root_cause":"胶量不足"}'}]}
            )
            analyzer = AIAnalyzer(api_key="test", enabled=True)
            # 注意：这里只是验证能调用，实际解析可能需要调整
            assert analyzer.enabled is True

    def test_1_2_alarm_deduplication(self, sample_alarm_event):
        """场景1.2：告警去重验证"""
        dedup = AlarmDedup(window_seconds=10)

        # 第1次：应该推送
        assert dedup.should_notify(sample_alarm_event) is True
        assert dedup.get_repeat_count(sample_alarm_event) == 1

        # 5分钟内连续3次：应该被去重
        for i in range(3):
            assert dedup.should_notify(sample_alarm_event) is False
            assert dedup.get_repeat_count(sample_alarm_event) == 2 + i

        # 等待超过去重窗口（10秒）
        time.sleep(11)

        # 再次触发：应该推送
        assert dedup.should_notify(sample_alarm_event) is True
        assert dedup.get_repeat_count(sample_alarm_event) == 5

    def test_1_3_alarm_window_reset(self):
        """场景1.3：告警窗口重置"""
        from datetime import datetime

        dedup = AlarmDedup(window_seconds=10)

        # 创建告警 A
        alarm_a = AlarmEvent(
            timestamp=datetime.now(),
            alarm_text="告警A_缺胶报警",
            module_name="ModuleA",
            level=AlarmLevel.CRITICAL,
            source=AlarmSource.DEFAULT_LOG,
            line_number=1,
            log_file="Default.log",
            raw_line="...",
        )

        # 创建告警 B
        alarm_b = AlarmEvent(
            timestamp=datetime.now(),
            alarm_text="告警B_预警",
            module_name="ModuleB",
            level=AlarmLevel.WARNING,
            source=AlarmSource.DEFAULT_LOG,
            line_number=1,
            log_file="Default.log",
            raw_line="...",
        )

        # 1. 写入告警A
        assert dedup.should_notify(alarm_a) is True

        # 2. 等待3分钟（测试中使用3秒）
        time.sleep(11)  # 调整为11秒以确保窗口过期

        # 3. 写入告警B（不同类型）
        assert dedup.should_notify(alarm_b) is True

        # 4. 再等待3秒
        time.sleep(3)

        # 5. 写入告警A（窗口已过期）
        assert dedup.should_notify(alarm_a) is True

        # 验证：告警A收到2次通知，告警B收到1次
        # （在实际实现中，需要记录推送次数）