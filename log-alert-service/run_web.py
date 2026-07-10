#!/usr/bin/env python3
"""
设备监控Web服务

提供REST API和WebSocket实时通信服务。
"""

import logging
import sys
from src.web.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """启动Web服务"""
    logger.info("=" * 50)
    logger.info("设备监控Web服务启动中...")
    logger.info("=" * 50)

    # 创建Flask应用
    app = create_app()
    socketio = app.extensions['socketio']

    # 获取配置
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5000)
    debug = app.config.get('DEBUG', False)

    logger.info(f"WebSocket服务地址: ws://localhost:{port}")
    logger.info(f"API服务地址: http://localhost:{port}/api")

    # 启动服务（使用SocketIO）
    try:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("服务已停止")
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
