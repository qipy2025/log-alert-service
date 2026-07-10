#!/usr/bin/env python3
"""
WebSocket连接测试脚本

测试WebSocket实时通信功能：
1. 连接测试
2. 心跳测试
3. 消拟告警事件广播
4. 设备状态变更广播
"""

import time
import json
import logging
from socketio import Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class WebSocketTester:
    """WebSocket连接测试器"""

    def __init__(self, url: str = "http://localhost:5000"):
        self.url = url
        self.client = None
        self.connected = False
        self.messages_received = []

    def on_connect(self):
        """连接成功回调"""
        logger.info("✅ WebSocket连接成功")
        self.connected = True

    def on_disconnect(self):
        """断开连接回调"""
        logger.info("❌ WebSocket已断开")
        self.connected = False

    def on_connected_message(self, data):
        """接收连接确认消息"""
        logger.info(f"📨 收到连接消息: {data}")

    def on_alarm(self, data):
        """接收告警消息"""
        logger.info(f"🚨 收到告警消息: {json.dumps(data, ensure_ascii=False, indent=2)}")
        self.messages_received.append(('alarm', data))

    def on_device_status_changed(self, data):
        """接收设备状态变更消息"""
        logger.info(f"🔄 收到状态变更消息: {json.dumps(data, ensure_ascii=False, indent=2)}")
        self.messages_received.append(('device_status_changed', data))

    def on_pong(self, data):
        """接收心跳响应"""
        logger.info(f"💓 收到心跳响应: {data}")

    def connect(self):
        """连接到WebSocket服务器"""
        logger.info(f"连接到WebSocket服务器: {self.url}")

        self.client = Client()
        self.client.on('connect', self.on_connect)
        self.client.on('disconnect', self.on_disconnect)
        self.client.on('connected', self.on_connected_message)
        self.client.on('alarm', self.on_alarm)
        self.client.on('device_status_changed', self.on_device_status_changed)
        self.client.on('pong', self.on_pong)

        try:
            self.client.connect(self.url, transports=['websocket', 'polling'])
            logger.info("等待连接建立...")
            time.sleep(2)
            return self.connected
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.client:
            self.client.disconnect()
            logger.info("已断开连接")

    def test_ping(self):
        """测试心跳"""
        logger.info("发送心跳测试...")
        self.client.emit('ping')
        time.sleep(1)

    def wait_for_messages(self, timeout: int = 10):
        """等待接收消息"""
        logger.info(f"等待消息（最多{timeout}秒）...")
        initial_count = len(self.messages_received)
        start_time = time.time()

        while time.time() - start_time < timeout:
            time.sleep(0.5)
            if len(self.messages_received) > initial_count:
                break

        received = len(self.messages_received) - initial_count
        logger.info(f"收到 {received} 条新消息")

    def print_summary(self):
        """打印测试总结"""
        logger.info("=" * 60)
        logger.info("测试总结")
        logger.info("=" * 60)
        logger.info(f"连接状态: {'✅ 已连接' if self.connected else '❌ 未连接'}")
        logger.info(f"接收消息总数: {len(self.messages_received)}")

        for msg_type, data in self.messages_received:
            logger.info(f"  - {msg_type}: {json.dumps(data, ensure_ascii=False)}")


def main():
    """主函数"""
    tester = WebSocketTester()

    try:
        # 1. 测试连接
        if not tester.connect():
            logger.error("连接失败，请检查Web服务是否启动")
            return

        # 2. 测试心跳
        tester.test_ping()

        # 3. 等待接收消息（如果有其他服务在发送）
        logger.info("等待接收消息（可以通过其他服务触发告警或状态变更）...")
        tester.wait_for_messages(timeout=30)

        # 4. 打印总结
        tester.print_summary()

    except KeyboardInterrupt:
        logger.info("测试被中断")
    finally:
        tester.disconnect()


if __name__ == "__main__":
    main()
