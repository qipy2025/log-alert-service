#!/usr/bin/env python3
"""
设备监控服务统一启动脚本

同时启动：
1. 日志监控服务（监控日志文件、AI分析、飞书推送）
2. Web服务（REST API + WebSocket实时通信）
"""

import logging
import signal
import sys
import threading
import time
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("service.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class ServiceManager:
    """服务管理器"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._running = False
        self._services = {}

    def start_log_monitor(self):
        """启动日志监控服务"""
        try:
            from main import AlertService

            logger.info("启动日志监控服务...")
            log_service = AlertService(self.config_path)
            log_service.start()

            self._services['log_monitor'] = log_service
            logger.info("✅ 日志监控服务已启动")

        except Exception as e:
            logger.error(f"❌ 日志监控服务启动失败: {e}")
            raise

    def start_web_service(self):
        """启动Web服务"""
        try:
            import multiprocessing
            from run_web import main as run_web_main

            logger.info("启动Web服务（API + WebSocket）...")

            # 在独立进程中启动Web服务
            web_process = multiprocessing.Process(target=run_web_main)
            web_process.daemon = True
            web_process.start()

            self._services['web_service'] = web_process
            logger.info("✅ Web服务已启动")

            # 等待Web服务初始化
            time.sleep(2)

        except Exception as e:
            logger.error(f"❌ Web服务启动失败: {e}")
            raise

    def start(self):
        """启动所有服务"""
        logger.info("=" * 60)
        logger.info("设备监控服务启动中...")
        logger.info("=" * 60)

        try:
            # 1. 启动日志监控服务（主进程）
            self.start_log_monitor()

            # 2. 启动Web服务（子进程）
            self.start_web_service()

            self._running = True
            logger.info("=" * 60)
            logger.info("🚀 所有服务已启动")
            logger.info("  - 日志监控: 运行中")
            logger.info("  - Web API: http://localhost:5000/api")
            logger.info("  - WebSocket: ws://localhost:5000")
            logger.info("=" * 60)

            # 保持主进程运行
            while self._running:
                time.sleep(1)

                # 检查Web服务进程状态
                if 'web_service' in self._services:
                    web_process = self._services['web_service']
                    if not web_process.is_alive():
                        logger.error("Web服务已停止，尝试重启...")
                        try:
                            web_process.terminate()
                            web_process.join()
                            self.start_web_service()
                        except Exception as e:
                            logger.error(f"重启Web服务失败: {e}")

        except KeyboardInterrupt:
            logger.info("收到停止信号")
            self.stop()
        except Exception as e:
            logger.error(f"服务启动失败: {e}")
            self.stop()
            sys.exit(1)

    def stop(self):
        """停止所有服务"""
        logger.info("正在停止服务...")
        self._running = False

        # 停止日志监控服务
        if 'log_monitor' in self._services:
            try:
                self._services['log_monitor'].stop()
                logger.info("日志监控服务已停止")
            except Exception as e:
                logger.error(f"停止日志监控服务失败: {e}")

        # 停止Web服务
        if 'web_service' in self._services:
            try:
                self._services['web_service'].terminate()
                self._services['web_service'].join(timeout=5)
                logger.info("Web服务已停止")
            except Exception as e:
                logger.error(f"停止Web服务失败: {e}")

        logger.info("所有服务已停止")


def main():
    """主函数"""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"

    manager = ServiceManager(config_path)

    # 信号处理
    def signal_handler(sig, frame):
        logger.info("收到停止信号")
        manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        manager.start()
    except KeyboardInterrupt:
        manager.stop()


if __name__ == "__main__":
    main()
