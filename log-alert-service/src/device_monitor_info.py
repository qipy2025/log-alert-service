"""设备监控信息类

存储单个设备的监控信息，管理 LogWatcher 实例和线程。
"""
import threading
from datetime import datetime
from typing import Dict, Callable, Optional, Any


class DeviceMonitorInfo:
    """设备监控信息

    存储单个设备的监控状态、LogWatcher 实例和监控线程。
    """

    def __init__(self, device_config: Dict[str, Any], watcher: Any):
        """初始化设备监控信息

        Args:
            device_config: 设备配置字典
            watcher: LogWatcher 实例
        """
        self.device_config = device_config
        self.watcher = watcher
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_heartbeat: Optional[datetime] = None
        self.alarm_count = 0
        self._lock = threading.Lock()

    def start(self):
        """启动设备监控

        在独立线程中启动 LogWatcher，避免阻塞主线程。
        """
        with self._lock:
            if self.is_running:
                return

            def run_watcher():
                """运行 LogWatcher 的线程函数"""
                try:
                    self.watcher.start()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"设备 {self.device_config.get('device_name')} 监控线程异常: {e}")

            # 创建线程对象
            thread = threading.Thread(
                target=run_watcher,
                name=f"DeviceMonitor-{self.device_config.get('device_name')}",
                daemon=True
            )
            self.thread = thread
            self.is_running = True
            self.last_heartbeat = datetime.now()

        # 在锁外启动线程，避免阻塞锁
        thread.start()

    def stop(self):
        """停止设备监控

        停止 LogWatcher 并清理资源。
        """
        # 在锁内获取引用并更新状态
        with self._lock:
            if not self.is_running:
                return

            self.is_running = False
            thread = self.thread
            watcher = self.watcher

        # 在锁外停止 watcher
        if watcher:
            try:
                watcher.stop()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"停止设备 {self.device_config.get('device_name')} watcher 失败: {e}")

        # 等待线程结束
        if thread and thread.is_alive():
            thread.join(timeout=5.0)

        # 清理状态
        with self._lock:
            self.thread = None

    def increment_alarm_count(self):
        """增加告警计数"""
        with self._lock:
            self.alarm_count += 1

    def reset_alarm_count(self):
        """重置告警计数"""
        with self._lock:
            self.alarm_count = 0

    def get_status(self) -> Dict[str, Any]:
        """获取设备监控状态

        Returns:
            包含设备状态信息的字典
        """
        with self._lock:
            return {
                "device_name": self.device_config.get("device_name"),
                "is_running": self.is_running,
                "alarm_count": self.alarm_count,
                "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
                "log_path": self.device_config.get("log_path"),
                "enabled": self.device_config.get("enabled", True)
            }
