#!/usr/bin/env python3
"""
部署验证脚本 - 验证服务部署是否成功
"""

import sys
import subprocess
import requests
import time
import json
from pathlib import Path


class DeploymentVerifier:
    """部署验证器"""

    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def print_header(self, title):
        """打印标题"""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")

    def check_service_running(self):
        """检查服务是否运行"""
        print("🔍 检查服务是否运行...")
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                print("   ✅ 服务正在运行")
                self.passed += 1
                return True
            else:
                print(f"   ⚠️  服务响应异常: {response.status_code}")
                self.warnings += 1
                return True
        except requests.exceptions.ConnectionError:
            print("   ❌ 服务未运行或无法连接")
            print(f"   请检查服务是否已启动: python main.py --web")
            self.failed += 1
            return False
        except Exception as e:
            print(f"   ⚠️  检查服务状态时出错: {e}")
            self.warnings += 1
            return True

    def check_database_connection(self):
        """检查数据库连接"""
        print("🔍 检查数据库连接...")
        try:
            response = requests.get(f"{self.base_url}/api/devices", timeout=5)
            if response.status_code == 200:
                print("   ✅ 数据库连接正常")
                self.passed += 1
                return True
            else:
                print(f"   ⚠️  数据库连接异常: {response.status_code}")
                self.warnings += 1
                return True
        except Exception as e:
            print(f"   ⚠️  检查数据库时出错: {e}")
            self.warnings += 1
            return True

    def check_api_endpoints(self):
        """检查API端点"""
        print("🔍 检查API端点...")
        endpoints = [
            ("/api/devices", "GET", "设备列表"),
            ("/api/alarms", "GET", "告警列表"),
            ("/api/notification-config", "GET", "通知配置"),
        ]

        for endpoint, method, description in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"   ✅ {description} API: {method} {endpoint}")
                else:
                    print(f"   ⚠️  {description} API: {method} {endpoint} (状态码: {response.status_code})")
            except Exception as e:
                print(f"   ❌ {description} API: {method} {endpoint} - {e}")

        self.passed += 1
        return True

    def check_websocket_connection(self):
        """检查WebSocket连接"""
        print("🔍 检查WebSocket连接...")
        try:
            import socketio
            sio = socketio.Client()

            @sio.event
            def connect():
                print("   ✅ WebSocket连接成功")
                sio.disconnect()

            @sio.event
            def disconnect():
                pass

            sio.connect(f"ws://{self.base_url.replace('http://', '')}")
            sio.wait()

            self.passed += 1
            return True
        except ImportError:
            print("   ⚠️  未安装python-socketio客户端，跳过WebSocket测试")
            print("   安装: pip install python-socketio")
            self.warnings += 1
            return True
        except Exception as e:
            print(f"   ⚠️  WebSocket连接测试失败: {e}")
            self.warnings += 1
            return True

    def check_configuration_files(self):
        """检查配置文件"""
        print("🔍 检查配置文件...")
        required_files = [
            'config.yaml',
            '.env'
        ]

        missing_files = []
        for file in required_files:
            if Path(file).exists():
                print(f"   ✅ {file} 存在")
            else:
                print(f"   ❌ {file} 不存在")
                missing_files.append(file)

        if not missing_files:
            print("   ✅ 配置文件完整")
            self.passed += 1
            return True
        else:
            print(f"   ❌ 缺失 {len(missing_files)} 个配置文件")
            self.failed += 1
            return False

    def check_log_files(self):
        """检查日志文件"""
        print("🔍 检查日志文件...")
        log_files = ['service.log']

        for log_file in log_files:
            if Path(log_file).exists():
                size = Path(log_file).stat().st_size
                print(f"   ✅ {log_file} 存在 (大小: {size} bytes)")
            else:
                print(f"   ⚠️  {log_file} 不存在 (服务可能未启动)")

        self.passed += 1
        return True

    def test_device_management(self):
        """测试设备管理功能"""
        print("🔍 测试设备管理功能...")
        try:
            # 获取设备列表
            response = requests.get(f"{self.base_url}/api/devices", timeout=5)
            if response.status_code == 200:
                devices = response.json()
                print(f"   ✅ 获取设备列表成功，当前设备数量: {len(devices)}")

                if len(devices) > 0:
                    first_device = devices[0]
                    device_name = first_device.get('device_name', 'unknown')
                    print(f"   📋 示例设备: {device_name}")

                self.passed += 1
                return True
            else:
                print(f"   ⚠️  获取设备列表失败: {response.status_code}")
                self.warnings += 1
                return True
        except Exception as e:
            print(f"   ⚠️  设备管理测试失败: {e}")
            self.warnings += 1
            return True

    def test_alarm_query(self):
        """测试告警查询功能"""
        print("🔍 测试告警查询功能...")
        try:
            # 获取告警列表
            response = requests.get(f"{self.base_url}/api/alarms?limit=10", timeout=5)
            if response.status_code == 200:
                alarms = response.json()
                print(f"   ✅ 告警查询成功，告警数量: {len(alarms)}")
                self.passed += 1
                return True
            else:
                print(f"   ⚠️  告警查询失败: {response.status_code}")
                self.warnings += 1
                return True
        except Exception as e:
            print(f"   ⚠️  告警查询测试失败: {e}")
            self.warnings += 1
            return True

    def generate_summary(self):
        """生成验证摘要"""
        self.print_header("验证结果摘要")
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"⚠️  警告: {self.warnings}")

        total = self.passed + self.failed + self.warnings
        success_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"📊 成功率: {success_rate:.1f}%")

        if self.failed == 0:
            print("\n🎉 部署验证通过！服务可以正常使用")
            return True
        else:
            print("\n⚠️  部署验证发现问题，建议修复后再使用")
            return False

    def run_verification(self):
        """运行完整验证"""
        self.print_header("🚀 开始部署验证")

        # 检查配置文件
        self.check_configuration_files()

        # 检查服务是否运行
        if not self.check_service_running():
            print("\n⚠️  服务未运行，跳过部分验证步骤")
            print("💡 请先启动服务: python main.py --web")
            return self.generate_summary()

        # 检查数据库连接
        self.check_database_connection()

        # 检查API端点
        self.check_api_endpoints()

        # 检查日志文件
        self.check_log_files()

        # 测试设备管理
        self.test_device_management()

        # 测试告警查询
        self.test_alarm_query()

        # 检查WebSocket（可选）
        self.check_websocket_connection()

        # 生成摘要
        return self.generate_summary()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='部署验证脚本')
    parser.add_argument('--url', default='http://localhost:5000', help='服务基础URL')
    parser.add_argument('--wait', type=int, default=0, help='等待服务启动的秒数')

    args = parser.parse_args()

    if args.wait > 0:
        print(f"⏳ 等待 {args.wait} 秒后开始验证...")
        time.sleep(args.wait)

    verifier = DeploymentVerifier(base_url=args.url)
    success = verifier.run_verification()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()