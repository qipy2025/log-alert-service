#!/usr/bin/env python3
"""
设备监控服务验证脚本

检查所有组件是否正常工作：
1. Python依赖
2. 数据库连接
3. 配置文件
4. Web服务健康检查
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class SetupVerifier:
    """安装验证器"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def verify_python_version(self):
        """验证Python版本"""
        logger.info("检查Python版本...")
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.errors.append(f"Python版本过低: {version.major}.{version.minor}.{version.micro}，需要 >= 3.8")
            return False
        logger.info(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True

    def verify_dependencies(self):
        """验证Python依赖"""
        logger.info("检查Python依赖...")
        required_packages = [
            ('flask', 'Flask'),
            ('flask_cors', 'Flask-CORS'),
            ('flask_socketio', 'Flask-SocketIO'),
            ('pymysql', 'PyMySQL'),
            ('watchdog', 'watchdog'),
            ('apscheduler', 'APScheduler'),
            ('python-dotenv', 'python-dotenv'),
            ('openai', 'openai'),
            ('feishu', 'feishu'),
        ]

        missing_packages = []
        for package, display_name in required_packages:
            try:
                __import__(package)
                logger.info(f"  ✅ {display_name}")
            except ImportError:
                missing_packages.append(display_name)
                logger.warning(f"  ❌ {display_name}")

        if missing_packages:
            self.errors.append(f"缺少依赖包: {', '.join(missing_packages)}")
            logger.error(f"请运行: pip install -r requirements.txt")
            return False

        logger.info("✅ 所有依赖已安装")
        return True

    def verify_config_file(self):
        """验证配置文件"""
        logger.info("检查配置文件...")
        config_paths = ['config.yaml', 'config.yml']

        config_found = False
        for config_path in config_paths:
            if Path(config_path).exists():
                logger.info(f"✅ 配置文件存在: {config_path}")
                config_found = True

                try:
                    from src.config_manager import ConfigManager
                    config = ConfigManager(config_path)
                    logger.info("✅ 配置文件格式正确")
                    return True
                except Exception as e:
                    self.errors.append(f"配置文件格式错误: {e}")
                    return False

        if not config_found:
            self.warnings.append("未找到配置文件，将使用默认配置")
            logger.warning("⚠️  未找到配置文件")
            return False

        return True

    def verify_database(self):
        """验证数据库连接"""
        logger.info("检查数据库连接...")
        try:
            from src.db.mysql import get_db_session, init_database

            # 尝试连接数据库
            session = get_db_session()
            session.close()
            logger.info("✅ 数据库连接成功")

            # 检查表是否存在
            from src.models.alarm import AlarmRecord
            from src.models.device import DeviceStatusHistory, OperationLog

            session = get_db_session()
            try:
                # 检查表
                session.query(AlarmRecord).first()
                session.query(DeviceStatusHistory).first()
                session.query(OperationLog).first()
                logger.info("✅ 数据库表已创建")
            except Exception as e:
                self.warnings.append(f"数据库表可能未创建: {e}")
                logger.warning("⚠️  数据库表可能未创建，尝试初始化...")
                try:
                    init_database()
                    logger.info("✅ 数据库表已创建")
                except Exception as init_error:
                    self.errors.append(f"数据库初始化失败: {init_error}")
                    return False
            finally:
                session.close()

            return True

        except Exception as e:
            self.errors.append(f"数据库连接失败: {e}")
            logger.error(f"❌ 数据库连接失败: {e}")
            logger.error("请检查MySQL服务是否运行，以及配置文件中的数据库设置")
            return False

    def verify_web_service(self):
        """验证Web服务（可选）"""
        logger.info("检查Web服务...")
        try:
            import requests
            response = requests.get('http://localhost:5000/health', timeout=2)
            if response.status_code == 200:
                logger.info("✅ Web服务运行中")
                return True
        except Exception as e:
            self.warnings.append(f"Web服务未运行或无法访问: {e}")
            logger.warning("⚠️  Web服务未运行（这是正常的，如果只运行日志监控服务）")
            return False

    def verify_directories(self):
        """验证目录结构"""
        logger.info("检查目录结构...")
        required_dirs = [
            'src',
            'src/db',
            'src/models',
            'src/web',
        ]

        all_exist = True
        for dir_path in required_dirs:
            if Path(dir_path).exists():
                logger.info(f"  ✅ {dir_path}")
            else:
                self.errors.append(f"缺少目录: {dir_path}")
                logger.error(f"  ❌ {dir_path}")
                all_exist = False

        if all_exist:
            logger.info("✅ 目录结构完整")
        return all_exist

    def run_all_checks(self):
        """运行所有检查"""
        logger.info("=" * 60)
        logger.info("开始验证设备监控服务安装")
        logger.info("=" * 60)

        checks = [
            ("Python版本", self.verify_python_version),
            ("目录结构", self.verify_directories),
            ("Python依赖", self.verify_dependencies),
            ("配置文件", self.verify_config_file),
            ("数据库连接", self.verify_database),
            ("Web服务", self.verify_web_service),
        ]

        results = {}
        for name, check_func in checks:
            logger.info(f"\n--- {name} ---")
            try:
                results[name] = check_func()
            except Exception as e:
                logger.error(f"检查失败: {e}")
                results[name] = False

        # 打印总结
        logger.info("\n" + "=" * 60)
        logger.info("验证总结")
        logger.info("=" * 60)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"{status}: {name}")

        logger.info(f"\n通过: {passed}/{total}")

        if self.errors:
            logger.error("\n错误:")
            for error in self.errors:
                logger.error(f"  - {error}")

        if self.warnings:
            logger.warning("\n警告:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        if passed == total:
            logger.info("\n🎉 所有检查通过！服务可以正常启动。")
            return True
        else:
            logger.error("\n❌ 部分检查失败，请修复错误后再启动服务。")
            return False


def main():
    """主函数"""
    verifier = SetupVerifier()
    success = verifier.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
