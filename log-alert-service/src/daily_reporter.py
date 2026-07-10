from collections import defaultdict
from datetime import datetime
from typing import Optional

from .models import AlarmEvent, DailySummary
from .ai_analyzer import AIAnalyzer
from .log_parser import scan_file_for_alarms


class DailyReporter:
    """每日告警汇总"""

    def __init__(
        self,
        log_dir: str,
        ai_analyzer: Optional[AIAnalyzer] = None,
        functional_log_dir: Optional[str] = None,
    ):
        self.log_dir = log_dir
        self.ai_analyzer = ai_analyzer
        self.functional_log_dir = functional_log_dir or log_dir
        self._today_alarms: dict[str, list[AlarmEvent]] = defaultdict(list)

    def record_alarm(self, event: AlarmEvent):
        """记录告警（由文件监控器触发时调用）"""
        date_key = event.timestamp.strftime("%Y-%m-%d")
        self._today_alarms[date_key].append(event)

    def get_summary(self, date_str: str) -> DailySummary:
        """生成指定日期的汇总"""
        alarms = self._today_alarms.get(date_str, [])

        alarm_counts: dict[str, int] = defaultdict(int)
        reset_count = 0
        for a in alarms:
            if "复位" in a.alarm_text:
                reset_count += 1
            # 取告警文本的前 10 个字作为类型
            alarm_type = a.alarm_text[:10]
            alarm_counts[alarm_type] += 1

        # 判断未解决告警：报警次数 > 复位次数
        critical_count = sum(1 for a in alarms if a.level.value == "critical")
        unresolved = max(0, critical_count - reset_count)

        summary_text = ""
        if self.ai_analyzer and self.ai_analyzer.enabled and alarms:
            # 用 AI 生成总结
            try:
                combined_context = "\n".join(
                    [f"[{a.timestamp}] {a.alarm_text}" for a in alarms[-10:]]
                )
                from .models import AlarmEvent as TempEvent
                from datetime import datetime as dt

                mock_event = TempEvent(
                    timestamp=dt.now(),
                    alarm_text=f"告警日报汇总 - {date_str}",
                    module_name="DailyReporter",
                    level=__import__("src.models", fromlist=["AlarmLevel"]).AlarmLevel.INFO,
                    source=__import__("src.models", fromlist=["AlarmSource"]).AlarmSource.DEFAULT_LOG,
                    line_number=0,
                    log_file="",
                    raw_line="",
                    context_lines=[f"今日告警共 {len(alarms)} 次"] + alarms[-5:],
                )
                result = self.ai_analyzer.analyze(mock_event)
                if result:
                    summary_text = result.root_cause
            except Exception as e:
                summary_text = f"AI 总结生成失败: {e}"

        if not summary_text:
            summary_text = f"今日共 {len(alarms)} 次告警，{reset_count} 次复位操作，{unresolved} 次未解决。"

        return DailySummary(
            date=date_str,
            total_alarms=len(alarms),
            alarm_counts=dict(alarm_counts),
            reset_counts=reset_count,
            unresolved_alarms=unresolved,
            summary_text=summary_text,
        )