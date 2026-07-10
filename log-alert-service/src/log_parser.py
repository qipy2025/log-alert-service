import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import AlarmLevel, AlarmSource, AlarmEvent


# Default.log 日志行正则
# 格式：2026-06-08 21:51:36,674 [   1] [Namespace.Class][Line] - 消息
LOG_LINE_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+"
    r"\[\s*(\d+)\]\s+"
    r"\[([^\]]+)\]"
    r"\[(\d+)\]\s*-\s*(.*)$"
)

# 告警级别匹配模式
ALARM_PATTERNS: dict[AlarmLevel, list[re.Pattern]] = {
    AlarmLevel.CRITICAL: [
        re.compile(r"报警_(?!复位)"),    # "报警_xxx" 但不匹配 "报警复位"
        re.compile(r"异常"),
    ],
    AlarmLevel.WARNING: [
        re.compile(r"预警_"),
    ],
    AlarmLevel.INFO: [
        re.compile(r"报警复位操作"),
    ],
}

# 功能日志告警匹配
FUNCTIONAL_ALARM_PATTERNS: dict[AlarmLevel, list[re.Pattern]] = {
    AlarmLevel.CRITICAL: [
        re.compile(r"报警_人工请马上更换"),
    ],
    AlarmLevel.WARNING: [
        re.compile(r"预警_人工请及时更换"),
    ],
}


def parse_log_line(line: str) -> Optional[dict]:
    """解析单行日志，返回结构化字典或 None（不匹配格式时）"""
    match = LOG_LINE_PATTERN.match(line)
    if not match:
        return None

    timestamp_str = match.group(1)
    thread_id = match.group(2)
    class_name = match.group(3)
    line_number = int(match.group(4))
    message = match.group(5)

    # 解析时间戳
    timestamp = datetime.strptime(
        timestamp_str.replace(",", "."),
        "%Y-%m-%d %H:%M:%S.%f"
    )

    return {
        "timestamp": timestamp,
        "thread_id": int(thread_id),
        "class_name": class_name,
        "line_number": line_number,
        "message": message,
        "raw_line": line.strip(),
    }


def detect_alarm_level(message: str, is_functional_log: bool = False) -> Optional[AlarmLevel]:
    """检测消息是否包含告警，返回告警级别或 None"""
    patterns = FUNCTIONAL_ALARM_PATTERNS if is_functional_log else ALARM_PATTERNS
    for level, regexes in patterns.items():
        for pattern in regexes:
            if pattern.search(message):
                return level
    return None


def create_alarm_event(
    parsed_line: dict,
    log_file: str,
    is_functional_log: bool = False,
) -> Optional[AlarmEvent]:
    """从解析后的日志行创建告警事件"""
    level = detect_alarm_level(parsed_line["message"], is_functional_log)
    if level is None:
        return None

    return AlarmEvent(
        timestamp=parsed_line["timestamp"],
        alarm_text=parsed_line["message"],
        module_name=parsed_line["class_name"],
        level=level,
        source=AlarmSource.FUNCTIONAL_LOG if is_functional_log else AlarmSource.DEFAULT_LOG,
        line_number=parsed_line["line_number"],
        log_file=log_file,
        raw_line=parsed_line["raw_line"],
    )


def scan_file_for_alarms(
    file_path: str,
    start_line: int = 0,
    is_functional_log: bool = False,
) -> list[AlarmEvent]:
    """扫描文件中的告警行，返回告警事件列表"""
    alarms: list[AlarmEvent] = []
    filepath = Path(file_path)
    if not filepath.exists():
        return alarms

    with open(filepath, "r", encoding="utf-8-sig") as f:
        for line_idx, line in enumerate(f):
            if line_idx < start_line:
                continue
            parsed = parse_log_line(line)
            if parsed is None:
                continue
            event = create_alarm_event(parsed, file_path, is_functional_log)
            if event is not None:
                alarms.append(event)
    return alarms