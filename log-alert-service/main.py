#!/usr/bin/env python3
"""
设备日志 AI 告警推送服务

实时监控点胶设备上位机日志，检测报警后通过飞书推送通知。
"""

import logging
import signal
import sys
import threading
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from src.config_manager import ConfigManager
from src.file_watcher import LogWatcher
from src.multi_device_watcher import MultiDeviceWatcher
from src.device_monitor_info import DeviceMonitorInfo
from src.alarm_dedup import AlarmDedup
from src.context_collector import collect_context
from src.ai_analyzer import AIAnalyzer
from src.feishu_notifier import FeishuNotifier
from src.daily_reporter import DailyReporter

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("service.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class AlertService:
    """告警推送服务主类"""

    def __init__(self, config_path: str = "config.yaml", enable_web: bool = False):
        self.config = ConfigManager(config_path)
        self._running = False
        self.enable_web = enable_web
        self.web_app = None
        self.web_socketio = None
        self.web_thread = None

        # 轮询相关
        self._polling_stop_event = None
        self._polling_thread = None
        self._polling_interval = self.config.get("device_polling.interval", 30)  # 默认30秒

        # 初始化组件
        self._init_components()

        # 初始化通知配置（如果不存在）
        self._init_notification_config()

    def _init_components(self):
        """初始化各组件"""
        # 告警去重
        self.dedup = AlarmDedup(
            window_seconds=self.config.get("dedup.alarm_window", 300),
            max_repeat=self.config.get("dedup.max_repeat_count", 99),
        )

        # AI 分析
        ai_config = self.config.get("ai_analysis", {})
        self.ai_analyzer = AIAnalyzer(
            api_key=ai_config.get("api_key", ""),
            api_base_url=ai_config.get("api_base_url", "http://model-api.desaysv.com"),
            model=ai_config.get("model", "deepseek-v4-flash-anthropic"),
            max_tokens=ai_config.get("max_tokens", 2048),
            temperature=ai_config.get("temperature", 0.3),
            enabled=ai_config.get("enabled", True),
        )

        # 飞书通知器
        feishu_config = self.config.get("feishu", {})
        self.notifier = FeishuNotifier(
            app_id=feishu_config.get("app_id", ""),
            app_secret=feishu_config.get("app_secret", ""),
            chats=feishu_config.get("chats", []),
        )

        # 每日汇总
        self.reporter = DailyReporter(
            log_dir="",
            ai_analyzer=self.ai_analyzer,
        )

        # 定时任务
        self.scheduler = BackgroundScheduler()

        # 多设备监控器
        self.multi_device_watcher = None

    def _init_notification_config(self):
        """初始化通知配置（确保默认配置存在）"""
        try:
            from src.db.notification_config_db import init_default_config
            created = init_default_config()
            if created:
                logger.info("已创建默认通知配置：禁用状态")
        except Exception as e:
            logger.warning(f"初始化通知配置失败（不影响服务启动）: {e}")

    def _get_device_log_dir(self, device_name: str) -> str:
        """获取设备的日志目录

        Args:
            device_name: 设备名称

        Returns:
            日志目录路径，如果获取失败返回空字符串
        """
        if not self.multi_device_watcher:
            logger.warning(f"MultiDeviceWatcher 未初始化，无法获取设备 {device_name} 的日志目录")
            return ""

        try:
            # 优先从数据库获取完整配置（含 log_name_mode）
            log_path = ""
            log_name_mode = "date_subdir"
            try:
                from src.db.device_config import DeviceConfig
                device_config = DeviceConfig.get_by_name(device_name)
                if device_config:
                    log_path = device_config.get("log_path", "")
                    log_name_mode = device_config.get("log_name_mode", "date_subdir")
            except Exception:
                pass

            # 回退：从 watcher 状态获取 log_path
            if not log_path:
                device_status = self.multi_device_watcher.get_device_status(device_name)
                if device_status:
                    log_path = device_status.get("log_path", "")

            if not log_path:
                logger.warning(f"设备 {device_name} 没有配置日志路径")
                return ""

            from datetime import datetime
            from pathlib import Path

            now = datetime.now()
            # date_filename / root_multi_subdir 模式：返回根目录
            if log_name_mode in ("date_filename", "root_multi_subdir"):
                return log_path

            # month_day_subdir 模式：<base>/<YYYY-MM>/<YYYY-MM-DD>
            if log_name_mode == "month_day_subdir":
                month_str = now.strftime("%Y-%m")
                day_str = now.strftime("%Y-%m-%d")
                return str(Path(log_path) / month_str / day_str)

            # date_subdir 模式：<base>/<YYYY-MM-DD>
            today_str = now.strftime("%Y-%m-%d")
            return str(Path(log_path) / today_str)

        except Exception as e:
            logger.error(f"获取设备 {device_name} 日志目录失败: {e}")
            return ""

    def _should_send_notification(self, event) -> bool:
        """检查配置是否允许发送此告警

        Args:
            event: 告警事件对象

        Returns:
            True 如果允许发送，False 如果不允许发送
        """
        try:
            from src.db.notification_config_db import get_notification_config
            from src.models.notification_config import NotificationConfig

            config = get_notification_config()

            # 如果配置不存在或总开关关闭，不发送
            if not config or not config.enabled:
                return False

            # 检查告警级别是否在允许列表中
            # 如果 allowed_levels 为空，则所有级别都被过滤
            if not config.allowed_levels or event.level.value not in config.allowed_levels:
                return False

            return True
        except Exception as e:
            logger.error(f"检查通知配置失败: {e}")
            # 安全失败：配置有问题时不发送通知
            return False

    def _on_alarm(self, event):
        """告警回调"""
        try:
            # 1. 去重检查
            if not self.dedup.should_notify(event):
                logger.debug(f"告警被去重: {event.alarm_text}")
                return

            # 更新告警的当日重复次数
            event.daily_count = self.dedup.get_repeat_count(event)

            # 2. 收集上下文
            device_log_dir = self._get_device_log_dir(getattr(event, 'device_name', None) or event.module_name)
            if device_log_dir:
                collect_context(
                    event,
                    device_log_dir,
                    self.config.get("log_source.max_context_lines", 20),
                    self.config.get("log_source.functional_log_window", 5),
                )
            else:
                logger.warning(f"无法获取设备 {event.module_name} 的日志目录，跳过上下文收集")

            # 3. AI 分析
            analysis = self.ai_analyzer.analyze(event)

            # 4. 记录到日报
            self.reporter.record_alarm(event)

            # 5. 存储告警到数据库
            try:
                from src.alarm_dedup import store_alarm_to_db
                store_alarm_to_db(event, analysis)
                logger.debug("告警已存储到数据库")
            except Exception as db_error:
                logger.warning(f"告警存储失败（数据库可能未配置）: {db_error}")

            # 6. 通过WebSocket实时推送（如果Web服务正在运行）
            try:
                from src.web.socketio import broadcast_alarm
                alarm_data = {
                    'device_name': getattr(event, 'device_name', None) or event.module_name,
                    'alarm_level': event.level.value,
                    'alarm_text': event.alarm_text,
                    'timestamp': event.timestamp.isoformat(),
                    'daily_count': event.daily_count,
                    'analysis': {
                        'root_cause': analysis.root_cause,
                        'severity': analysis.severity,
                        'suggestion': analysis.suggestion,
                        'related_module': analysis.related_module
                    } if analysis else None
                }
                broadcast_alarm(alarm_data)
                logger.debug("告警已通过WebSocket广播")
            except Exception as ws_error:
                logger.warning(f"WebSocket广播失败（Web服务可能未启动）: {ws_error}")

            # 7. 推送飞书（添加配置检查）
            if self._should_send_notification(event):
                success = self.notifier.send_alarm(event, analysis)
                if success:
                    logger.info(f"告警推送成功: {event.alarm_text}")
                    # 更新告警记录的通知状态
                    try:
                        from src.alarm_dedup import update_alarm_notified_status
                        update_alarm_notified_status(event)
                        logger.debug("告警通知状态已更新")
                    except Exception as db_error:
                        logger.warning(f"更新告警通知状态失败: {db_error}")
                else:
                    logger.error(f"告警推送失败: {event.alarm_text}")
            else:
                logger.debug(f"告警被配置过滤: {event.alarm_text}")

        except Exception as e:
            logger.exception(f"处理告警时出错: {e}")

    def _send_daily_report(self):
        """发送每日汇总报告"""
        try:
            from datetime import datetime, timedelta

            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            summary = self.reporter.get_summary(yesterday)
            self.notifier.send_daily_report(summary)
            logger.info(f"每日汇总推送成功: {yesterday}")
        except Exception as e:
            logger.exception(f"发送每日汇总时出错: {e}")

    def _start_web_service(self):
        """在独立线程中启动Web服务"""
        try:
            import threading
            from src.web.app import create_app
            import os

            logger.info("启动Web服务...")

            # 创建Flask应用
            self.web_app = create_app()
            self.web_socketio = self.web_app.extensions['socketio']

            # 在独立线程中运行Web服务
            def run_web():
                host = os.getenv('WEB_HOST', '0.0.0.0')
                port = int(os.getenv('WEB_PORT', 5000))
                debug = os.getenv('DEBUG', 'False').lower() == 'true'

                logger.info(f"Web服务地址: http://localhost:{port}")
                logger.info(f"WebSocket地址: ws://localhost:{port}")

                self.web_socketio.run(
                    self.web_app,
                    host=host,
                    port=port,
                    debug=debug,
                    allow_unsafe_werkzeug=True
                )

            self.web_thread = threading.Thread(target=run_web, daemon=True)
            self.web_thread.start()

            logger.info("✅ Web服务已启动（后台运行）")

        except Exception as e:
            logger.error(f"❌ Web服务启动失败: {e}")
            self.web_app = None
            self.web_socketio = None
            self.web_thread = None

    def _stop_web_service(self):
        """停止Web服务"""
        if self.web_socketio:
            try:
                # Flask-SocketIO没有直接停止的方法
                # Web服务会随主进程退出
                logger.info("Web服务已停止")
            except Exception as e:
                logger.error(f"停止Web服务失败: {e}")

    def _poll_device_changes(self):
        """轮询设备配置变更

        后台线程方法，定期检查数据库中的设备配置变更，
        自动启动新设备、停止已禁用设备、处理配置变更。
        """
        logger.info(f"设备轮询线程已启动（间隔: {self._polling_interval}秒）")

        while not self._polling_stop_event.is_set():
            try:
                # 等待轮询间隔或停止信号
                self._polling_stop_event.wait(timeout=self._polling_interval)

                # 如果收到停止信号，退出轮询
                if self._polling_stop_event.is_set():
                    break

                logger.debug("开始检查设备配置变更...")

                # 1. 从数据库加载最新的启用设备列表
                db_devices = self.multi_device_watcher.load_devices_from_db()

                # 2. 获取当前活动设备列表
                active_devices = self.multi_device_watcher.get_active_devices()

                # 3. 构建设备配置字典（便于查找）
                db_device_map = {d["device_name"]: d for d in db_devices}

                # 4. 检测新增设备（在DB中启用但未在活动列表中）
                new_devices = []
                for device_config in db_devices:
                    device_name = device_config["device_name"]
                    if device_name not in active_devices:
                        new_devices.append(device_config)

                if new_devices:
                    logger.info(f"检测到 {len(new_devices)} 个新设备")
                    for device_config in new_devices:
                        device_name = device_config["device_name"]
                        try:
                            self.multi_device_watcher.start_device(device_config)
                            logger.info(f"✅ 自动启动新设备: {device_name}")
                        except Exception as e:
                            logger.error(f"❌ 启动新设备 {device_name} 失败: {e}")

                # 5. 检测移除设备（在活动列表但DB中未启用）
                removed_devices = []
                for device_name in active_devices:
                    if device_name not in db_device_map:
                        removed_devices.append(device_name)

                if removed_devices:
                    logger.info(f"检测到 {len(removed_devices)} 个被移除的设备")
                    for device_name in removed_devices:
                        try:
                            self.multi_device_watcher.stop_device(device_name)
                            logger.info(f"⏹️  自动停止已禁用设备: {device_name}")
                        except Exception as e:
                            logger.error(f"❌ 停止设备 {device_name} 失败: {e}")

                # 6. 检测配置变更（设备名称在两边都有，但配置发生变化）
                changed_devices = []
                for device_config in db_devices:
                    device_name = device_config["device_name"]
                    if device_name in active_devices:
                        # 获取当前设备状态
                        current_status = self.multi_device_watcher.get_device_status(device_name)
                        if current_status:
                            # 比较关键配置字段
                            current_config = current_status.get("config", {})

                            # 检查配置是否变更（比较 log_path, polling_interval, encoding）
                            if (device_config.get("log_path") != current_config.get("log_path") or
                                device_config.get("polling_interval") != current_config.get("polling_interval") or
                                device_config.get("encoding") != current_config.get("encoding")):

                                changed_devices.append(device_config)

                if changed_devices:
                    logger.info(f"检测到 {len(changed_devices)} 个配置变更的设备")
                    for device_config in changed_devices:
                        device_name = device_config["device_name"]
                        try:
                            # 先停止旧监控
                            self.multi_device_watcher.stop_device(device_name)
                            # 再启动新监控
                            self.multi_device_watcher.start_device(device_config)
                            logger.info(f"🔄 重启配置变更设备: {device_name}")
                        except Exception as e:
                            logger.error(f"❌ 重启设备 {device_name} 失败: {e}")

                if not new_devices and not removed_devices and not changed_devices:
                    logger.debug("未检测到设备配置变更")

            except Exception as e:
                logger.error(f"设备轮询出错: {e}", exc_info=True)
                # 即使出错也继续下一轮轮询

        logger.info("设备轮询线程已退出")

    def _start_polling_thread(self):
        """启动设备变更轮询线程"""
        if self._polling_thread is not None:
            logger.warning("轮询线程已在运行")
            return

        self._polling_stop_event = threading.Event()
        self._polling_thread = threading.Thread(
            target=self._poll_device_changes,
            name="DevicePollingThread",
            daemon=True
        )
        self._polling_thread.start()
        logger.info("✅ 设备变更轮询线程已启动")

    def _stop_polling_thread(self):
        """停止设备变更轮询线程"""
        if self._polling_thread is None:
            return

        logger.info("正在停止设备轮询线程...")

        # 设置停止信号
        self._polling_stop_event.set()

        # 等待线程结束（最多5秒）
        self._polling_thread.join(timeout=5)

        if self._polling_thread.is_alive():
            logger.warning("⚠️  轮询线程未能在5秒内停止，可能仍在运行")
        else:
            logger.info("✅ 设备轮询线程已停止")

        self._polling_thread = None
        self._polling_stop_event = None

    def _validate_device_config(self, device_config: dict) -> tuple[bool, str]:
        """验证单个设备配置

        Args:
            device_config: 设备配置字典

        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 1. 验证 device_name
            device_name = device_config.get("device_name")
            if not device_name:
                return False, "缺少 device_name 字段"

            # 使用 DeviceManager 的验证逻辑
            from src.device_manager import DeviceManager
            DeviceManager.validate_device_name(device_name)

            # 2. 验证 log_path
            log_path = device_config.get("log_path")
            if not log_path:
                return False, "缺少 log_path 字段"

            DeviceManager.validate_log_path(log_path)

            # 3. 验证 encoding
            encoding = device_config.get("encoding")
            if not encoding:
                return False, "缺少 encoding 字段"

            # 4. 验证 polling_interval
            polling_interval = device_config.get("polling_interval")
            if polling_interval is None:
                return False, "缺少 polling_interval 字段"

            if not isinstance(polling_interval, int) or polling_interval <= 0:
                return False, f"polling_interval 必须为正整数，当前值: {polling_interval}"

            return True, ""

        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"验证异常: {e}"

    def start(self):
        """启动服务"""
        logger.info("=" * 50)
        logger.info("设备日志 AI 告警推送服务启动中...")
        logger.info("=" * 50)

        # 创建多设备监控器
        self.multi_device_watcher = MultiDeviceWatcher(on_alarm=self._on_alarm)
        logger.info("MultiDeviceWatcher 已创建")

        # 从数据库加载启用的设备列表（添加错误处理）
        devices = []
        try:
            devices = self.multi_device_watcher.load_devices_from_db()
        except Exception as e:
            logger.error(f"从数据库加载设备配置失败: {e}")
            logger.warning("服务将启动但不会监控任何设备（数据库连接失败）")

        if not devices:
            logger.warning("没有有效的设备配置，服务将启动但不会监控任何日志")
        else:
            # 配置验证摘要
            total_devices = len(devices)
            valid_devices = []
            invalid_devices = []

            logger.info(f"开始验证 {total_devices} 个设备配置...")

            # 验证每个设备配置
            for device_config in devices:
                device_name = device_config.get("device_name", "未知")
                is_valid, error_msg = self._validate_device_config(device_config)

                if is_valid:
                    valid_devices.append(device_config)
                else:
                    invalid_devices.append((device_name, error_msg))
                    logger.warning(f"设备配置无效 [{device_name}]: {error_msg}")

            # 记录验证摘要
            logger.info(f"配置验证摘要: 总计 {total_devices} 个, 有效 {len(valid_devices)} 个, 无效 {len(invalid_devices)} 个")

            if invalid_devices:
                logger.warning("以下设备配置将被跳过:")
                for device_name, error in invalid_devices:
                    logger.warning(f"  - {device_name}: {error}")

            # 启动有效的设备监控
            if valid_devices:
                self.multi_device_watcher.start_all(valid_devices)

                # 验证至少启动了一个设备
                active_count = len(self.multi_device_watcher.get_active_devices())
                if active_count == 0:
                    logger.error("❌ 所有设备启动失败，服务将继续运行但不会监控任何设备")
                else:
                    logger.info(f"✅ 成功启动 {active_count} 个设备监控（共 {len(valid_devices)} 个有效配置）")
            else:
                logger.warning("没有有效的设备配置，服务将启动但不会监控任何日志")

        # 配置每日汇总定时任务
        daily_config = self.config.get("daily_report", {})
        if daily_config.get("enabled", True):
            schedule_time = daily_config.get("schedule_time", "22:00")
            hour, minute = schedule_time.split(":")
            self.scheduler.add_job(
                self._send_daily_report,
                "cron",
                hour=int(hour),
                minute=int(minute),
                id="daily_report",
            )
            self.scheduler.start()
            logger.info(f"每日汇总定时任务已设定: {schedule_time}")

        # 启动Web服务（如果启用）
        if self.enable_web:
            self._start_web_service()
            # 设置 AlertService 全局实例（供 API 端点使用）
            from src.web.app import set_alert_service_instance
            set_alert_service_instance(self)

        # 启动设备变更轮询线程
        self._start_polling_thread()

        self._running = True
        logger.info("服务启动完成 ✅")

    def start_device_by_name(self, device_name: str):
        """通过设备名称启动设备监控

        Args:
            device_name: 设备名称

        Raises:
            ValueError: 设备不存在或已在监控中
            Exception: 启动失败
        """
        from src.db.device_config import DeviceConfig

        if not self.multi_device_watcher:
            raise RuntimeError("MultiDeviceWatcher 未初始化")

        # 1. 检查设备是否存在
        device_config = DeviceConfig.get_by_name(device_name)
        if not device_config:
            raise ValueError(f"设备不存在: {device_name}")

        # 2. 检查设备是否已在监控
        active_devices = self.multi_device_watcher.get_active_devices()
        if device_name in active_devices:
            raise ValueError(f"设备已在监控中: {device_name}")

        # 3. 启动设备监控
        try:
            self.multi_device_watcher.start_device(device_config)
            logger.info(f"手动启动设备监控成功: {device_name}")
        except Exception as e:
            logger.error(f"手动启动设备监控失败 {device_name}: {e}")
            raise

    def stop_device_by_name(self, device_name: str):
        """通过设备名称停止设备监控

        Args:
            device_name: 设备名称

        Raises:
            ValueError: 设备未在监控中
            Exception: 停止失败
        """
        if not self.multi_device_watcher:
            raise RuntimeError("MultiDeviceWatcher 未初始化")

        # 1. 检查设备是否在监控中
        active_devices = self.multi_device_watcher.get_active_devices()
        if device_name not in active_devices:
            raise ValueError(f"设备未在监控中: {device_name}")

        # 2. 停止设备监控
        try:
            self.multi_device_watcher.stop_device(device_name)
            logger.info(f"手动停止设备监控成功: {device_name}")
        except Exception as e:
            logger.error(f"手动停止设备监控失败 {device_name}: {e}")
            raise

    def stop(self):
        """停止服务"""
        logger.info("正在停止服务...")
        self._running = False

        # 停止设备变更轮询线程（已包含超时保护）
        self._stop_polling_thread()

        # 停止Web服务
        if self.enable_web:
            self._stop_web_service()

        # 停止所有设备监控（添加超时保护）
        if self.multi_device_watcher:
            import time
            start_time = time.time()
            timeout = 5  # 5秒超时

            try:
                self.multi_device_watcher.stop_all()

                # 验证是否所有设备都已停止
                active_devices = self.multi_device_watcher.get_active_devices()
                if active_devices:
                    elapsed = time.time() - start_time
                    if elapsed < timeout:
                        logger.warning(f"⚠️  还有 {len(active_devices)} 个设备未停止，等待最多 {timeout - elapsed:.1f} 秒...")
                        # 等待剩余时间
                        time.sleep(timeout - elapsed)
                        active_devices = self.multi_device_watcher.get_active_devices()

                    if active_devices:
                        logger.warning(f"⚠️  超时后仍有 {len(active_devices)} 个设备未停止，强制继续")
                    else:
                        logger.info("✅ 所有设备监控已正常停止")
                else:
                    logger.info("✅ 所有设备监控已正常停止")

            except Exception as e:
                logger.error(f"停止设备监控时出错: {e}")
                # 继续执行其他清理操作

        if hasattr(self, "scheduler") and self.scheduler.running:
            try:
                self.scheduler.shutdown(wait=False)
                logger.info("定时任务调度器已停止")
            except Exception as e:
                logger.error(f"停止调度器时出错: {e}")

        logger.info("服务已停止")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='设备日志AI告警推送服务')
    parser.add_argument('--config', '-c', default='config.yaml', help='配置文件路径')
    parser.add_argument('--web', '-w', action='store_true', help='同时启动Web服务（API + WebSocket）')
    args = parser.parse_args()

    service = AlertService(args.config, enable_web=args.web)

    def signal_handler(sig, frame):
        logger.info("收到停止信号")
        service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        service.start()
        # 保持运行
        import time

        while service._running:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()


if __name__ == "__main__":
    main()