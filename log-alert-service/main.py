#!/usr/bin/env python3
"""
设备日志 AI 告警推送服务

实时监控点胶设备上位机日志，检测报警后通过飞书推送通知。
"""

import logging
import signal
import sys
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from src.config_manager import ConfigManager
from src.file_watcher import LogWatcher
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

        # 当前监控的日期目录
        self._current_log_dir: str = ""

    def _init_notification_config(self):
        """初始化通知配置（确保默认配置存在）"""
        try:
            from src.db.notification_config_db import init_default_config
            created = init_default_config()
            if created:
                logger.info("已创建默认通知配置：禁用状态")
        except Exception as e:
            logger.warning(f"初始化通知配置失败（不影响服务启动）: {e}")

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
            if config.allowed_levels and event.level.value not in config.allowed_levels:
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
            if self._current_log_dir:
                collect_context(
                    event,
                    self._current_log_dir,
                    self.config.get("log_source.max_context_lines", 20),
                    self.config.get("log_source.functional_log_window", 5),
                )

            # 3. AI 分析
            analysis = self.ai_analyzer.analyze(event)

            # 4. 记录到日报
            self.reporter.record_alarm(event)

            # 5. 存储告警到数据库
            try:
                from src.alarm_dedup import store_alarm_to_db
                store_alarm_to_db(event)
                logger.debug("告警已存储到数据库")
            except Exception as db_error:
                logger.warning(f"告警存储失败（数据库可能未配置）: {db_error}")

            # 6. 通过WebSocket实时推送（如果Web服务正在运行）
            try:
                from src.web.socketio import broadcast_alarm
                alarm_data = {
                    'device_name': event.module_name,
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

    def start(self):
        """启动服务"""
        logger.info("=" * 50)
        logger.info("设备日志 AI 告警推送服务启动中...")
        logger.info("=" * 50)

        # 获取日志路径
        log_source = self.config.get("log_source", {})
        base_path = log_source.get("path", "")

        # 检查是否直接使用完整路径（不自动添加日期）
        use_direct_path = log_source.get("use_direct_path", False)

        if use_direct_path:
            # 直接使用配置的路径，不添加日期子目录
            target_dir = base_path
        else:
            # 确定今天的日志目录
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")
            target_dir = str(Path(base_path) / today_str)

        self._current_log_dir = target_dir

        logger.info(f"监控日志目录: {target_dir}")

        # 启动文件监控
        self.watcher = LogWatcher(
            log_dir=target_dir,
            on_alarm=self._on_alarm,
            polling_interval=log_source.get("polling_interval", 2),
            encoding=log_source.get("encoding", "utf-8-sig"),
        )
        self.watcher.start()
        logger.info("文件监控已启动")

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

        self._running = True
        logger.info("服务启动完成 ✅")

    def stop(self):
        """停止服务"""
        logger.info("正在停止服务...")
        self._running = False

        # 停止Web服务
        if self.enable_web:
            self._stop_web_service()

        if hasattr(self, "watcher"):
            self.watcher.stop()
        if hasattr(self, "scheduler") and self.scheduler.running:
            self.scheduler.shutdown()
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