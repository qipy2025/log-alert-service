"""日志文件监控器

使用自定义轮询线程（而非 watchdog 事件）读取日志新增行。
原因：网络共享（UNC）路径上 watchdog 的 ReadDirectoryChangesW 事件
通常不可靠或根本不触发；轮询方式对本地/网络路径一致可靠。

读取位置持久化到本地 json：首次启动对新文件从头扫描（发现历史告警），
后续重启从上次位置继续（不重复扫描、不重复告警）。

支持的日志命名模式：
  - date_subdir:       <base>/<YYYY-MM-DD>/Default.log
  - month_day_subdir:  <base>/<YYYY-MM>/<YYYY-MM-DD>/Default.log
  - date_filename:     <base>/<YYYY-MM-DD>.log
  - root_multi_subdir: <base>/<任意子目录>/<YYYY-MM>/<YYYY-MM-DD>/*.log
                       （扫描 base 下所有子目录的所有 .log，用于一个根目录下
                         多个并列日志子目录的场景，如 上位机日志/默认日志）
"""
import glob
import json
import logging
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List

from .log_parser import parse_log_line, detect_alarm_level, create_alarm_event
from src.data_models import AlarmEvent

logger = logging.getLogger(__name__)

DEFAULT_POSITION_FILE = "data/file_positions.json"


def check_device_enabled(device_name: str) -> bool:
    """检查设备是否启用监控"""
    try:
        from src.db.cache import get_device_status
        status_data = get_device_status(device_name)
        status = status_data.get('status', 'RUNNING')
        return status == 'RUNNING'
    except Exception as e:
        logger.error(f"检查设备状态失败: {e}")
        return True  # 默认启用


class LogWatcher:
    """日志轮询监控器（读取位置持久化）"""

    def __init__(
        self,
        log_dir: str,
        on_alarm: Callable[[AlarmEvent], None],
        polling_interval: int = 2,
        encoding: str = "utf-8-sig",
        log_name_mode: str = "date_subdir",
        monitor_days: int = 1,
        position_file: str = None,
    ):
        self.log_dir = log_dir
        self.on_alarm = on_alarm
        self.polling_interval = max(1, polling_interval)
        self.encoding = encoding
        self.log_name_mode = log_name_mode or "date_subdir"
        self.monitor_days = max(1, monitor_days)
        self.position_file = position_file or DEFAULT_POSITION_FILE
        # 文件路径 → 上次读取到的字节位置（从持久化加载）
        self._last_position: dict[str, int] = self._load_positions()

        self._running = False
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None

    # ---------- 读取位置持久化 ----------

    def _load_positions(self) -> dict:
        try:
            with open(self.position_file, "r", encoding="utf-8") as f:
                return dict(json.load(f))
        except Exception:
            return {}

    def _save_positions(self) -> None:
        try:
            parent = os.path.dirname(self.position_file)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.position_file, "w", encoding="utf-8") as f:
                json.dump(self._last_position, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存读取位置失败: {e}")

    # ---------- 文件路径解析 ----------

    def _resolve_target_files(self) -> List[str]:
        """根据日志命名模式计算当前应监控的文件列表"""
        base = Path(self.log_dir)
        files: List[str] = []
        now = datetime.now()

        if self.log_name_mode == "date_filename":
            for d in range(self.monitor_days):
                ds = (now - timedelta(days=d)).strftime("%Y-%m-%d")
                files.append(str(base / f"{ds}.log"))
        elif self.log_name_mode == "month_day_subdir":
            for d in range(self.monitor_days):
                dt = now - timedelta(days=d)
                files.append(str(base / dt.strftime("%Y-%m") / dt.strftime("%Y-%m-%d") / "Default.log"))
        elif self.log_name_mode == "root_multi_subdir":
            # <base>/<任意子目录>/<YYYY-MM>/<YYYY-MM-DD>/*.log
            for d in range(self.monitor_days):
                dt = now - timedelta(days=d)
                pattern = os.path.join(str(base), "*", dt.strftime("%Y-%m"), dt.strftime("%Y-%m-%d"), "*.log")
                files.extend(glob.glob(pattern))
        else:  # date_subdir
            for d in range(self.monitor_days):
                ds = (now - timedelta(days=d)).strftime("%Y-%m-%d")
                files.append(str(base / ds / "Default.log"))

        return files

    # ---------- 增量读取 ----------

    def _process_new_lines(self, file_path: str):
        """读取文件新增的行，检测告警

        新文件（_last_position 无记录）从头扫描；已有记录从上次位置增量读取。
        """
        path = Path(file_path)
        if not path.exists():
            return

        try:
            current_size = path.stat().st_size
        except Exception as e:
            logger.debug(f"获取文件大小失败 {file_path}: {e}")
            return

        last_pos = self._last_position.get(file_path, 0)  # 0 表示新文件，从头扫描
        if current_size < last_pos:
            last_pos = 0  # 文件轮转/截断

        if current_size == last_pos:
            return

        try:
            with open(file_path, "r", encoding=self.encoding, errors="replace") as f:
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
        except Exception as e:
            logger.warning(f"读取日志文件失败 {file_path}: {e}")
            return

        self._last_position[file_path] = current_size

    # ---------- 轮询线程 ----------

    def _poll(self):
        """单次轮询：计算目标文件、增量读取、保存位置"""
        try:
            for file_path in self._resolve_target_files():
                self._process_new_lines(file_path)
            self._save_positions()
        except Exception as e:
            logger.error(f"轮询日志失败 ({self.log_dir}): {e}", exc_info=True)

    def _run(self):
        logger.info(f"🔍 日志轮询线程启动: {self.log_dir} (间隔 {self.polling_interval}s, 模式 {self.log_name_mode})")
        while self._running:
            self._poll()
            if self._stop_event:
                self._stop_event.wait(self.polling_interval)
        logger.info(f"日志轮询线程退出: {self.log_dir}")

    def start(self):
        """启动监控（后台轮询线程）"""
        if self._running:
            return
        self._running = True
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"LogWatcher-{self.log_dir}", daemon=True)
        self._thread.start()

    def stop(self):
        """停止监控"""
        self._running = False
        if self._stop_event:
            self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._save_positions()
