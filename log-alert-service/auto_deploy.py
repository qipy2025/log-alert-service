#!/usr/bin/env python3
"""
一键部署脚本 - 自动化测试环境部署
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
import time


class AutoDeployer:
    """自动部署器"""

    def __init__(self, config_file=None, skip_checks=False, start_service=False):
        self.config_file = config_file
        self.skip_checks = skip_checks
        self.start_service = start_service
        self.project_root = Path(__file__).parent

    def print_step(self, step_num, total_steps, message):
        """打印部署步骤"""
        print(f"\n{'='*60}")
        print(f"步骤 {step_num}/{total_steps}: {message}")
        print(f"{'='*60}")

    def check_python(self):
        """检查Python环境"""
        print("🔍 检查Python环境...")
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            print(f"❌ Python版本过低: {version.major}.{version.minor}.{version.micro}")
            print("需要Python 3.8或更高版本")
            return False

    def setup_virtual_env(self):
        """设置虚拟环境"""
        print("🔍 设置虚拟环境...")
        venv_path = self.project_root / "venv"

        if venv_path.exists():
            print("✅ 虚拟环境已存在")
            # 检查虚拟环境是否可用
            python_exe = venv_path / "Scripts" / "python.exe" if os.name == 'nt' else venv_path / "bin" / "python"
            if python_exe.exists():
                return True
            else:
                print("⚠️  虚拟环境损坏，重新创建...")
                shutil.rmtree(venv_path)

        print("📦 创建虚拟环境...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ 虚拟环境创建成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 虚拟环境创建失败: {e}")
            return False

    def get_venv_python(self):
        """获取虚拟环境Python路径"""
        if os.name == 'nt':  # Windows
            return self.project_root / "venv" / "Scripts" / "python.exe"
        else:  # Linux/Mac
            return self.project_root / "venv" / "bin" / "python"

    def get_venv_pip(self):
        """获取虚拟环境pip路径"""
        if os.name == 'nt':  # Windows
            return self.project_root / "venv" / "Scripts" / "pip.exe"
        else:  # Linux/Mac
            return self.project_root / "venv" / "bin" / "pip"

    def install_dependencies(self):
        """安装依赖包"""
        print("🔍 安装依赖包...")
        venv_pip = self.get_venv_pip()

        if not venv_pip.exists():
            print("❌ 虚拟环境pip不存在")
            return False

        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            print("❌ requirements.txt 文件不存在")
            return False

        try:
            print("📦 正在安装依赖包，这可能需要几分钟...")
            subprocess.run(
                [str(venv_pip), "install", "-r", str(requirements_file)],
                check=True,
                capture_output=True
            )
            print("✅ 依赖包安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖包安装失败: {e}")
            print("💡 请手动运行: pip install -r requirements.txt")
            return False

    def create_config_files(self):
        """创建配置文件"""
        print("🔍 检查配置文件...")

        # 检查config.yaml
        config_file = self.project_root / "config.yaml"
        if not config_file.exists():
            example_config = self.project_root / "config.example.yaml"
            if example_config.exists():
                print("📋 从 config.example.yaml 创建 config.yaml...")
                shutil.copy(example_config, config_file)
                print("✅ config.yaml 已创建")
                print("⚠️  请编辑 config.yaml 配置数据库和API密钥信息")
            else:
                print("❌ config.example.yaml 不存在，无法创建配置文件")
                return False
        else:
            print("✅ config.yaml 已存在")

        # 检查.env文件
        env_file = self.project_root / ".env"
        if not env_file.exists():
            example_env = self.project_root / ".env.example"
            if example_env.exists():
                print("📋 从 .env.example 创建 .env...")
                shutil.copy(example_env, env_file)
                print("✅ .env 已创建")
                print("⚠️  请编辑 .env 配置敏感信息")
            else:
                print("⚠️  .env.example 不存在")
        else:
            print("✅ .env 已存在")

        return True

    def setup_database(self):
        """设置数据库"""
        print("🔍 设置数据库...")
        print("💡 请确保MySQL服务正在运行")
        print("💡 请手动创建数据库: CREATE DATABASE device_monitoring;")

        # 询问是否继续
        response = input("数据库是否已准备好？(y/n): ").lower()
        if response == 'y':
            print("✅ 数据库准备步骤完成")
            return True
        else:
            print("⚠️  请先准备数据库后再继续")
            return False

    def run_deployment_check(self):
        """运行部署检查"""
        print("🔍 运行部署检查...")
        check_script = self.project_root / "deployment_check.py"
        venv_python = self.get_venv_python()

        if not check_script.exists():
            print("⚠️  deployment_check.py 不存在，跳过检查")
            return True

        if not venv_python.exists():
            print("❌ 虚拟环境Python不存在")
            return False

        try:
            result = subprocess.run(
                [str(venv_python), str(check_script)],
                capture_output=True,
                text=True
            )
            print(result.stdout)
            if result.stderr:
                print("错误:", result.stderr)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"❌ 部署检查失败: {e}")
            return False

    def initialize_database(self):
        """初始化数据库"""
        print("🔍 初始化数据库...")
        venv_python = self.get_venv_python()

        try:
            # 尝试运行一次服务初始化数据库表
            print("📋 正在初始化数据库表...")
            result = subprocess.run(
                [str(venv_python), "-c", "from src.db.models import Base; from src.db.engine import engine; Base.metadata.create_all(engine); print('数据库初始化成功')"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )

            if result.returncode == 0:
                print("✅ 数据库初始化成功")
                return True
            else:
                print("⚠️  数据库初始化失败，服务启动时会自动初始化")
                return True
        except Exception as e:
            print(f"⚠️  数据库初始化异常: {e}")
            print("💡 服务启动时会自动初始化数据库表")
            return True

    def test_service(self):
        """测试服务"""
        print("🔍 测试服务...")
        venv_python = self.get_venv_python()

        try:
            # 运行基础测试
            print("📋 运行基础测试...")
            result = subprocess.run(
                [str(venv_python), "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )

            if result.returncode == 0:
                print("✅ 基础测试通过")
                return True
            else:
                print("⚠️  部分测试失败，但不影响部署")
                return True
        except Exception as e:
            print(f"⚠️  测试运行异常: {e}")
            return True

    def start_service(self):
        """启动服务"""
        print("🔍 启动服务...")
        venv_python = self.get_venv_python()

        try:
            print("🚀 启动服务（按Ctrl+C停止）...")
            subprocess.run(
                [str(venv_python), "main.py", "--web"],
                cwd=str(self.project_root)
            )
        except KeyboardInterrupt:
            print("\n⏹️  服务已停止")
        except Exception as e:
            print(f"❌ 服务启动失败: {e}")

    def deploy(self):
        """执行完整部署流程"""
        total_steps = 8
        current_step = 0

        print("🚀 开始自动化部署流程")
        print(f"📁 项目目录: {self.project_root}")

        # 步骤1: 检查Python环境
        current_step += 1
        self.print_step(current_step, total_steps, "检查Python环境")
        if not self.check_python():
            return False

        # 步骤2: 设置虚拟环境
        current_step += 1
        self.print_step(current_step, total_steps, "设置虚拟环境")
        if not self.setup_virtual_env():
            return False

        # 步骤3: 安装依赖包
        current_step += 1
        self.print_step(current_step, total_steps, "安装依赖包")
        if not self.install_dependencies():
            return False

        # 步骤4: 创建配置文件
        current_step += 1
        self.print_step(current_step, total_steps, "创建配置文件")
        if not self.create_config_files():
            return False

        # 步骤5: 设置数据库
        current_step += 1
        self.print_step(current_step, total_steps, "设置数据库")
        if not self.setup_database():
            return False

        # 步骤6: 运行部署检查（可选）
        if not self.skip_checks:
            current_step += 1
            self.print_step(current_step, total_steps, "运行部署检查")
            if not self.run_deployment_check():
                print("⚠️  部署检查发现问题，建议修复后再继续")
                response = input("是否继续部署？(y/n): ").lower()
                if response != 'y':
                    return False

        # 步骤7: 初始化数据库
        current_step += 1
        self.print_step(current_step, total_steps, "初始化数据库")
        if not self.initialize_database():
            return False

        # 步骤8: 测试服务（可选）
        if not self.skip_checks:
            current_step += 1
            self.print_step(current_step, total_steps, "测试服务")
            self.test_service()

        # 部署完成
        print("\n" + "="*60)
        print("🎉 部署完成！")
        print("="*60)
        print("\n📋 后续步骤:")
        print("1. 编辑 config.yaml 和 .env 文件，配置数据库连接和API密钥")
        print("2. 确保MySQL服务正在运行")
        print("3. 启动服务: python main.py --web")
        print("4. 访问Web界面: http://localhost:5000")
        print("\n💡 快速启动命令:")
        print("   Windows: start.bat")
        print("   Linux/Mac: ./venv/bin/python main.py --web")

        # 如果需要启动服务
        if self.start_service:
            print("\n🚀 正在启动服务...")
            time.sleep(2)  # 给用户时间看到上述信息
            self.start_service()

        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='设备监控服务一键部署脚本')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--skip-checks', action='store_true', help='跳过部署检查')
    parser.add_argument('--start', action='store_true', help='部署完成后启动服务')

    args = parser.parse_args()

    deployer = AutoDeployer(
        config_file=args.config,
        skip_checks=args.skip_checks,
        start_service=args.start
    )

    success = deployer.deploy()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()