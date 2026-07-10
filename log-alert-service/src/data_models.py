from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AlarmLevel(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlarmSource(Enum):
    DEFAULT_LOG = "Default.log"
    FUNCTIONAL_LOG = "functional_log"


@dataclass
class AlarmEvent:
    """单个告警事件"""
    timestamp: datetime
    alarm_text: str
    module_name: str
    level: AlarmLevel
    source: AlarmSource
    line_number: int
    log_file: str
    raw_line: str
    context_lines: list[str] = field(default_factory=list)
    functional_log_context: list[str] = field(default_factory=list)
    daily_count: int = 1


@dataclass
class AnalysisResult:
    """AI 分析结果"""
    root_cause: str
    severity: str
    suggestion: str
    related_module: str
    probable_time_to_resolve: str = ""


@dataclass
class DailySummary:
    """每日汇总数据"""
    date: str
    total_alarms: int
    alarm_counts: dict[str, int]  # {alarm_type: count}
    reset_counts: int
    unresolved_alarms: int
    summary_text: str = ""