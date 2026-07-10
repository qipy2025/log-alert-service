"""多设备监控器

管理多个设备的日志监控，为每个设备创建独立的 LogWatcher 实例。
"""
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional

from src.file_watcher import LogWatcher
from src.device_monitor_info import DeviceMonitorInfo
from src.data_models import AlarmEvent
from src.db.device_config import DeviceConfig

logger = logging.getLogger(__name__)


class MultiDeviceWatcher:
    """多设备监控管理器

    从数据库读取启用的设备列表，为每个设备创建独立的 LogWatcher 实例，
    管理所有设备监控的生命周期（启动/停止）。
    """

    def __init__(self, on_alarm: Callable[[AlarmEvent], None]):
        """初始化多设备监控器

        Args:
            on_alarm: 告警回调函数
        """
        self.on_alarm = on_alarm
        self.device_monitors: Dict[str, DeviceMonitorInfo] = {}
        self._lock = threading.Lock()

    def load_devices_from_db(self) -> List[Dict[str, Any]]:
        """从数据库加载启用的设备配置

        Returns:
            启用的设备配置列表
        """
        all_devices = DeviceConfig.get_all()

        # 只返回启用的设备
        enabled_devices = [d for d in all_devices if d.get("enabled", False)]

        logger.info(f"从数据库加载了 {len(enabled_devices)} 个启用的设备（共 {len(all_devices)} 个）")

        return enabled_devices

    def start_device(self, device_config: Dict[str, Any]):
        """为单个设备启动监控

        Args:
            device_config: 设备配置字典
        """
        device_name = device_config.get("device_name")

        if not device_name:
            logger.error("设备配置缺少 device_name")
            return

        with self._lock:
            # 如果设备已在监控，先停止
            if device_name in self.device_monitors:
                logger.info(f"设备 {device_name} 已在监控，先停止旧监控")
                self.stop_device(device_name)

            try:
                # 构建日志文件路径（添加日期子目录）
                log_path = self._build_log_path(device_config.get("log_path", ""))

                # 创建 LogWatcher
                watcher = LogWatcher(
                    log_dir=log_path,
                    on_alarm=self._create_device_alarm_callback(device_name),
                    polling_interval=device_config.get("polling_interval", 2),
                    encoding=device_config.get("encoding", "utf-8-sig")
                )

                # 创建 DeviceMonitorInfo
                monitor_info = DeviceMonitorInfo(device_config, watcher)

                # 启动监控
                monitor_info.start()

                # 添加到监控列表
                self.device_monitors[device_name] = monitor_info

                logger.info(f"✅ 设备 {device_name} 监控已启动: {log_path}")

            except Exception as e:
                logger.error(f"❌ 启动设备 {device_name} 监控失败: {e}")
                raise

    def stop_device(self, device_name: str):
        """停止单个设备的监控

        Args:
            device_name: 设备名称
        """
        with self._lock:
            if device_name not in self.device_monitors:
                logger.warning(f"设备 {device_name} 未在监控中")
                return

            try:
                monitor_info = self.device_monitors[device_name]
                monitor_info.stop()

                # 从监控列表移除
                del self.device_monitors[device_name]

                logger.info(f"⏹️  设备 {device_name} 监控已停止")

            except Exception as e:
                logger.error(f"❌ 停止设备 {device_name} 监控失败: {e}")
                raise

    def start_all(self, devices: List[Dict[str, Any]]):
        """启动所有设备的监控

        Args:
            devices: 设备配置列表
        """
        logger.info(f"开始启动 {len(devices)} 个设备的监控...")

        for device_config in devices:
            try:
                self.start_device(device_config)
            except Exception as e:
                logger.error(f"启动设备 {device_config.get('device_name')} 失败: {e}")
                # 继续启动其他设备

        logger.info(f"✅ 成功启动 {len(self.device_monitors)} 个设备监控")

    def stop_all(self):
        """停止所有监控"""
        logger.info("停止所有设备监控...")

        device_names = list(self.device_monitors.keys())

        for device_name in device_names:
            try:
                self.stop_device(device_name)
            except Exception as e:
                logger.error(f"停止设备 {device_name} 失败: {e}")

        logger.info("✅ 所有设备监控已停止")

    def get_active_devices(self) -> List[str]:
        """获取当前正在监控的设备名称列表

        Returns:
            设备名称列表
        """
        with self._lock:
            return list(self.device_monitors.keys())

    def get_device_status(self, device_name: str) -> Optional[Dict[str, Any]]:
        """获取单个设备的监控状态

        Args:
            device_name: 设备名称

        Returns:
            设备状态字典，如果设备不存在则返回 None
        """
        with self._lock:
            if device_name not in self.device_monitors:
                return None

            return self.device_monitors[device_name].get_status()

    def _build_log_path(self, base_log_path: str) -> str:
        """构建日志文件路径（添加日期子目录）

        Args:
            base_log_path: 基础日志路径

        Returns:
            完整的日志目录路径
        """
        from datetime import datetime

        # 添加日期子目录
        today_str = datetime.now().strftime("%Y-%m-%d")
        full_path = str(Path(base_log_path) / today_str)

        return full_path

    def _create_device_alarm_callback(self, device_name: str) -> Callable[[AlarmEvent], None]:
        """创建设备特定的告警回调

        在告警事件中添加设备名称信息。

        Args:
            device_name: 设备名称

        Returns:
            告警回调函数
        """
        def callback(event: AlarmEvent):
            # 设置设备名称（如果没有）
            if not event.module_name:
                event.module_name = device_name

            # 调用主告警回调
            self.on_alarm(event)

            # 增加该设备的告警计数
            if device_name in self.device_monitors:
                self.device_monitors[device_name].increment_alarm_count()

        return callback
