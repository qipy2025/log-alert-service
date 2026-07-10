from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .log_parser import parse_log_line, detect_alarm_level
from src.data_models import AlarmEvent


def read_lines(
    file_path: str,
    encoding: str = "utf-8-sig",
) -> list[tuple[int, str, Optional[dict]]]:
    """
    读取文件，返回 [(line_number_0index, raw_line, parsed_dict_or_None), ...]
    """
    lines: list[tuple[int, str, Optional[dict]]] = []
    filepath = Path(file_path)
    if not filepath.exists():
        return lines

    with open(filepath, "r", encoding=encoding) as f:
        for idx, raw_line in enumerate(f):
            parsed = parse_log_line(raw_line)
            lines.append((idx, raw_line.rstrip("\n\r"), parsed))
    return lines


def extract_context(
    lines: list[tuple[int, str, Optional[dict]]],
    target_idx: int,
    context_lines: int = 20,
) -> list[str]:
    """提取目标行前后各 N 行的上下文"""
    start = max(0, target_idx - context_lines)
    end = min(len(lines), target_idx + context_lines + 1)
    return [lines[i][1] for i in range(start, end)]


def find_related_functional_logs(
    timestamp: datetime,
    log_dir: str,
    window_seconds: int = 5,
) -> list[tuple[str, str]]:
    """
    在功能日志中查找时间相关的告警行。
    返回 [(文件名, 原始行), ...]
    """
    related: list[tuple[str, str]] = []
    log_dir_path = Path(log_dir)

    # 中文功能日志文件列表
    functional_logs = [
        "点胶交互流程.log",
        "点胶工站.log",
        "中间流道1.log",
        "清胶工站.log",
        "视觉交互.log",
    ]

    time_start = timestamp - timedelta(seconds=window_seconds)
    time_end = timestamp + timedelta(seconds=window_seconds)

    for log_name in functional_logs:
        log_path = log_dir_path / log_name
        if not log_path.exists():
            continue

        with open(log_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                parsed = parse_log_line(line)
                if parsed is None:
                    continue
                # 检查时间窗口内且包含告警
                if time_start <= parsed["timestamp"] <= time_end:
                    level = detect_alarm_level(parsed["message"], is_functional_log=True)
                    if level is not None:
                        related.append((log_name, parsed["raw_line"]))

    return related


def collect_context(
    event: AlarmEvent,
    log_dir: str,
    max_context_lines: int = 20,
    functional_window: int = 5,
) -> AlarmEvent:
    """
    为告警事件收集上下文：
    1. Default.log 前后行上下文
    2. 功能日志中的关联告警行
    """
    # 1. 收集 Default.log 上下文
    default_log_path = Path(log_dir) / event.log_file
    if default_log_path.exists():
        lines = read_lines(str(default_log_path))
        target_idx = next(
            (i for i, (_, _, p) in enumerate(lines) if p and p["line_number"] == event.line_number),
            None,
        )
        if target_idx is not None:
            event.context_lines = extract_context(lines, target_idx, max_context_lines)

    # 2. 收集功能日志上下文
    functional_context = find_related_functional_logs(
        event.timestamp,
        str(Path(log_dir).parent),  # 上位机日志/ 目录
        functional_window,
    )
    event.functional_log_context = [
        f"[{fname}] {line}" for fname, line in functional_context
    ]

    return event