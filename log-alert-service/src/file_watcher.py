import os
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer

from .log_parser import parse_log_line, detect_alarm_level, create_alarm_event
from src.data_models import AlarmEvent


def check_device_enabled(device_name: str) -> bool:
    """检查设备是否启用监控"""
    try:
        from src.db.cache import get_device_status
        status_data = get_device_status(device_name)
        status = status_data.get('status', 'RUNNING')
        return status == 'RUNNING'
    except Exception as e:
        logger = __import__('logging').getLogger(__name__)
        logger.error(f"检查设备状态失败: {e}")
        return True  # 默认启用


class LogFileHandler(FileSystemEventHandler):
    """watchdog 事件处理器，监控日志文件变更"""

    def __init__(
        self,
        default_log_file: str,
        on_alarm: Callable[[AlarmEvent], None],
        encoding: str = "utf-8-sig",
    ):
        self.default_log_file = default_log_file
        self.on_alarm = on_alarm
        self.encoding = encoding
        self._last_position: dict[str, int] = {}  # 文件路径 → 上次读取到的位置

    def on_modified(self, event: FileModifiedEvent):
        """文件被修改时调用"""
        if not event.is_directory and event.src_path.endswith("Default.log"):
            self._process_new_lines(event.src_path)

    def _process_new_lines(self, file_path: str):
        """读取文件新增的行，检测告警"""
        path = Path(file_path)
        if not path.exists():
            return

        current_size = path.stat().st_size
        last_pos = self._last_position.get(file_path, 0)

        # 检测文件轮转（新文件比上次位置小）
        if current_size < last_pos:
            last_pos = 0

        if current_size == last_pos:
            return

        with open(file_path, "r", encoding=self.encoding) as f:
            f.seek(last_pos)
            for line in f:
                parsed = parse_log_line(line)
                if parsed is None:
                    continue
                level = detect_alarm_level(parsed["message"])
                if level is not None:
                    event = create_alarm_event(parsed, file_path)
                    if event is not None:
                        self.on_alarm(event)

        self._last_position[file_path] = current_size

    def scan_existing_file(self, file_path: str):
        """扫描已有文件全部内容（启动时使用）"""
        self._last_position[file_path] = 0
        self._process_new_lines(file_path)


class LogWatcher:
    """日志目录监控器"""

    def __init__(
        self,
        log_dir: str,
        on_alarm: Callable[[AlarmEvent], None],
        polling_interval: int = 2,
        encoding: str = "utf-8-sig",
    ):
        self.log_dir = log_dir
        self.polling_interval = polling_interval
        self.observer = Observer()
        self.handler = LogFileHandler(
            default_log_file=str(Path(log_dir) / "Default.log"),
            on_alarm=on_alarm,
            encoding=encoding,
        )

    def start(self):
        """启动监控"""
        self.observer.schedule(
            self.handler,
            self.log_dir,
            recursive=False,
        )
        self.observer.start()

        # 启动时扫描已有文件
        default_log = Path(self.log_dir) / "Default.log"
        if default_log.exists():
            self.handler.scan_existing_file(str(default_log))

    def stop(self):
        """停止监控"""
        self.observer.stop()
        self.observer.join()