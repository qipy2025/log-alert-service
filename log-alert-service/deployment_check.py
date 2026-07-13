#!/usr/bin/env python3
"""
测试环境部署前检查脚本
检查环境是否满足部署要求
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path


class DeploymentChecker:
    """部署检查器"""

    def __init__(self):
        self.checks = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def check_python_version(self):
        """检查Python版本"""
        print("🔍 检查Python版本...")
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
            self.passed += 1
            return True
        else:
            print(f"   ❌ Python版本过低: {version.major}.{version.minor}.{version.micro}")
            print(f"   需要Python 3.8+")
            self.failed += 1
            return False

    def check_mysql_connection(self):
        """检查MySQL连接"""
        print("🔍 检查MySQL连接...")
        try:
            import pymysql
            # 尝试读取配置
            config = self._load_config()
            if config:
                mysql_config = config.get('mysql', {})
                host = mysql_config.get('host', 'localhost')
                port = mysql_config.get('port', 3306)
                user = mysql_config.get('user', 'root')
                password = mysql_config.get('password', '')
                database = mysql_config.get('database', 'device_monitoring')

                conn = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database
                )
                conn.close()
                print(f"   ✅ MySQL连接成功: {host}:{port}/{database}")
                self.passed += 1
                return True
        except Exception as e:
            print(f"   ❌ MySQL连接失败: {e}")
            print(f"   请检查MySQL服务是否运行以及配置文件中的数据库设置")
            self.failed += 1
            return False

    def check_dependencies(self):
        """检查Python依赖包"""
        print("🔍 检查Python依赖包...")
        required_packages = [
            'watchdog', 'pyyaml', 'requests', 'apscheduler',
            'python-dotenv', 'flask', 'flask-cors', 'flask-socketio',
            'pymysql', 'sqlalchemy', 'openai'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"   ✅ {package}")
            except ImportError:
                print(f"   ❌ {package} (缺失)")
                missing_packages.append(package)

        if not missing_packages:
            print("   ✅ 所有依赖包已安装")
            self.passed += 1
            return True
        else:
            print(f"   ❌ 缺失 {len(missing_packages)} 个依赖包")
            print(f"   请运行: pip install -r requirements.txt")
            self.failed += 1
            return False

    def check_config_files(self):
        """检查配置文件"""
        print("🔍 检查配置文件...")
        config_files = ['config.yaml', '.env']
        missing_files = []

        for file in config_files:
            if Path(file).exists():
                print(f"   ✅ {file} 存在")
            else:
                print(f"   ⚠️  {file} 不存在")
                missing_files.append(file)

        if not missing_files:
            print("   ✅ 配置文件完整")
            self.passed += 1
            return True
        else:
            print(f"   ⚠️  缺失 {len(missing_files)} 个配置文件")
            print(f"   请参考 config.yaml.example 创建配置文件")
            self.warnings += 1
            return True  # 配置文件可以后续创建

    def check_log_directory(self):
        """检查日志目录访问"""
        print("🔍 检查日志目录访问...")
        try:
            config = self._load_config()
            if config:
                log_path = config.get('log_source', {}).get('path', '')
                if log_path and Path(log_path).exists():
                    print(f"   ✅ 日志目录可访问: {log_path}")
                    self.passed += 1
                    return True
                else:
                    print(f"   ⚠️  日志目录不存在或无法访问: {log_path}")
                    print(f"   这是正常的，因为设备日志路径因环境而异")
                    self.warnings += 1
                    return True
        except Exception as e:
            print(f"   ⚠️  无法检查日志目录: {e}")
            self.warnings += 1
            return True

    def check_ports(self):
        """检查端口占用"""
        print("🔍 检查端口占用...")
        port = 5000
        try:
            # 简单的端口检查
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()

            if result == 0:
                print(f"   ⚠️  端口 {port} 已被占用")
                print(f"   可以修改 .env 文件中的 WEB_PORT 变量")
                self.warnings += 1
                return True
            else:
                print(f"   ✅ 端口 {port} 可用")
                self.passed += 1
                return True
        except Exception as e:
            print(f"   ⚠️  无法检查端口: {e}")
            self.warnings += 1
            return True

    def check_api_connectivity(self):
        """检查外部API连接"""
        print("🔍 检查外部API连接...")
        try:
            import requests
            config = self._load_config()

            # 检查AI API
            ai_api_url = config.get('ai_analysis', {}).get('api_base_url', '')
            if ai_api_url:
                try:
                    response = requests.get(ai_api_url, timeout=5)
                    print(f"   ✅ AI API可访问: {ai_api_url}")
                except:
                    print(f"   ⚠️  AI API无法访问: {ai_api_url}")
                    print(f"   请检查网络连接或API地址")
                    self.warnings += 1

            self.passed += 1
            return True
        except Exception as e:
            print(f"   ⚠️  无法检查API连接: {e}")
            self.warnings += 1
            return True

    def _load_config(self):
        """加载配置文件"""
        try:
            import yaml
            with open('config.yaml', 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except:
            return None

    def run_all_checks(self):
        """运行所有检查"""
        print("=" * 60)
        print("🚀 测试环境部署前检查")
        print("=" * 60)
        print()

        self.check_python_version()
        self.check_config_files()
        self.check_dependencies()
        self.check_mysql_connection()
        self.check_log_directory()
        self.check_ports()
        self.check_api_connectivity()

        print()
        print("=" * 60)
        print("📊 检查结果汇总")
        print("=" * 60)
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"⚠️  警告: {self.warnings}")
        print()

        if self.failed == 0:
            print("🎉 环境检查通过！可以开始部署")
            return True
        else:
            print("❌ 环境检查失败！请解决上述问题后继续")
            return False


def main():
    """主函数"""
    checker = DeploymentChecker()
    success = checker.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()