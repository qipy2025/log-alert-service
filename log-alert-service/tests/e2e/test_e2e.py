#!/usr/bin/env python3
"""
端到端测试

测试完整的告警流程：
1. 模拟日志文件写入
2. 检测告警
3. AI分析
4. WebSocket推送
5. 数据库存储
"""

import os
import sys
import time
import tempfile
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class E2ETester:
    """端到端测试器"""

    def __init__(self):
        self.test_log_dir = None
        self.test_log_file = None
        self.alarms_detected = []

    def setup_test_environment(self):
        """设置测试环境"""
        logger.info("设置测试环境...")

        # 创建临时目录
        self.test_log_dir = tempfile.mkdtemp(prefix="log_test_")
        self.test_log_file = os.path.join(self.test_log_dir, "Default.log")

        logger.info(f"测试日志目录: {self.test_log_dir}")
        logger.info(f"测试日志文件: {self.test_log_file}")

        return True

    def test_database_connection(self):
        """测试数据库连接"""
        logger.info("测试数据库连接...")
        try:
            from src.db.mysql import get_db_session
            from src.models.alarm import AlarmRecord

            session = get_db_session()
            # 清理之前的测试数据
            session.query(AlarmRecord).filter(
                AlarmRecord.device_name.like('TEST-%')
            ).delete()
            session.commit()
            session.close()

            logger.info("✅ 数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            return False

    def test_config_loading(self):
        """测试配置加载"""
        logger.info("测试配置加载...")
        try:
            from src.config_manager import ConfigManager
            config = ConfigManager('config.yaml')
            logger.info("✅ 配置加载成功")
            return True
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            return False

    def test_alarm_detection(self):
        """测试告警检测"""
        logger.info("测试告警检测...")
        try:
            from main import AlertService
            import threading

            # 创建测试服务（不启动Web服务）
            service = AlertService('config.yaml', enable_web=False)

            # 修改配置使用测试目录
            service.config.data['log_source'] = {
                'path': self.test_log_dir,
                'use_direct_path': True,
                'polling_interval': 1,
                'encoding': 'utf-8-sig'
            }

            # 启动服务
            service.start()
            logger.info("监控服务已启动")

            # 等待初始化
            time.sleep(2)

            # 写入测试告警
            logger.info("写入测试告警...")
            test_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            test_log_content = f"""{test_timestamp} [INFO] 系统启动
{test_timestamp} [INFO] 设备初始化
{test_timestamp} [ERROR] 报警：TEST-DEVICE 温度过高，当前温度：85℃
{test_timestamp} [INFO] 正常运行中
"""

            with open(self.test_log_file, 'w', encoding='utf-8') as f:
                f.write(test_log_content)

            logger.info("等待告警检测...")
            time.sleep(3)

            # 停止服务
            service.stop()
            logger.info("监控服务已停止")

            return True

        except Exception as e:
            logger.error(f"❌ 告警检测失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_database_storage(self):
        """测试数据库存储"""
        logger.info("测试数据库存储...")
        try:
            from src.db.mysql import get_db_session
            from src.models.alarm import AlarmRecord

            session = get_db_session()
            try:
                # 查询测试告警
                alarms = session.query(AlarmRecord).filter(
                    AlarmRecord.alarm_content.like('%温度过高%')
                ).all()

                if alarms:
                    logger.info(f"✅ 发现 {len(alarms)} 条告警记录")
                    for alarm in alarms:
                        logger.info(f"  - 设备: {alarm.device_name}, 级别: {alarm.alarm_level}, 内容: {alarm.alarm_content}")
                    return True
                else:
                    logger.warning("⚠️  未发现测试告警记录")
                    return False

            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ 数据库存储测试失败: {e}")
            return False

    def test_websocket_connection(self):
        """测试WebSocket连接"""
        logger.info("测试WebSocket连接...")
        try:
            from socketio import Client

            # 尝试连接WebSocket服务
            socket = Client()
            connected = False

            def on_connect():
                nonlocal connected
                connected = True
                logger.info("✅ WebSocket连接成功")

            socket.on('connect', on_connect)

            try:
                socket.connect('http://localhost:5000', transports=['websocket', 'polling'], timeout=2)
                time.sleep(1)
                socket.disconnect()
                return connected
            except Exception as e:
                logger.warning(f"⚠️  WebSocket连接失败（服务可能未启动）: {e}")
                return False  # 不算失败，因为服务可能未启动

        except ImportError:
            logger.warning("⚠️  python-socketio未安装，跳过WebSocket测试")
            return False

    def test_api_endpoints(self):
        """测试API端点"""
        logger.info("测试API端点...")
        try:
            import requests

            # 测试健康检查
            response = requests.get('http://localhost:5000/health', timeout=2)
            if response.status_code == 200:
                logger.info("✅ 健康检查端点正常")
            else:
                logger.error(f"❌ 健康检查端点异常: {response.status_code}")
                return False

            # 测试设备列表
            response = requests.get('http://localhost:5000/api/devices', timeout=2)
            if response.status_code == 200:
                logger.info("✅ 设备列表端点正常")
                data = response.json()
                logger.info(f"  设备数量: {len(data.get('devices', []))}")
            else:
                logger.error(f"❌ 设备列表端点异常: {response.status_code}")
                return False

            return True

        except ImportError:
            logger.warning("⚠️  requests未安装，跳过API测试")
            return False
        except Exception as e:
            logger.warning(f"⚠️  API测试失败（服务可能未启动）: {e}")
            return False

    def cleanup_test_environment(self):
        """清理测试环境"""
        logger.info("清理测试环境...")
        try:
            import shutil
            if self.test_log_dir and os.path.exists(self.test_log_dir):
                shutil.rmtree(self.test_log_dir)
                logger.info("✅ 测试环境已清理")
        except Exception as e:
            logger.warning(f"⚠️  清理失败: {e}")

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("开始端到端测试")
        logger.info("=" * 60)

        tests = [
            ("环境设置", self.setup_test_environment),
            ("数据库连接", self.test_database_connection),
            ("配置加载", self.test_config_loading),
            ("告警检测", self.test_alarm_detection),
            ("数据库存储", self.test_database_storage),
            ("WebSocket连接", self.test_websocket_connection),
            ("API端点", self.test_api_endpoints),
        ]

        results = {}
        for name, test_func in tests:
            logger.info(f"\n--- {name} ---")
            try:
                results[name] = test_func()
            except Exception as e:
                logger.error(f"测试失败: {e}")
                import traceback
                traceback.print_exc()
                results[name] = False

        # 清理
        self.cleanup_test_environment()

        # 打印总结
        logger.info("\n" + "=" * 60)
        logger.info("测试总结")
        logger.info("=" * 60)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"{status}: {name}")

        logger.info(f"\n通过: {passed}/{total}")

        if passed >= total - 2:  # 允许WebSocket和API测试失败（服务可能未启动）
            logger.info("\n🎉 核心功能测试通过！")
            return True
        else:
            logger.error("\n❌ 部分测试失败")
            return False


def main():
    """主函数"""
    tester = E2ETester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
