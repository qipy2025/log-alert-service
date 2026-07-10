import os
import tempfile
from pathlib import Path
import pytest
import yaml

from src.config_manager import ConfigManager


def test_config_manager_loads_yaml():
    """测试加载基本 yaml 配置"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_data = {"log_source": {"path": "\\test\\path", "polling_interval": 2}}
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        cm = ConfigManager(str(config_path))
        assert cm.get("log_source.path") == "\\test\\path"
        assert cm.get("log_source.polling_interval") == 2


def test_config_manager_env_var_substitution():
    """测试 ${VAR} 占位符能从环境变量读取"""
    os.environ["TEST_SECRET"] = "test_secret_value"
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("feishu:\n  app_secret: \"${TEST_SECRET}\"\n")

        cm = ConfigManager(str(config_path))
        assert cm.get("feishu.app_secret") == "test_secret_value"


def test_config_manager_missing_env_var():
    """测试缺少环境变量时抛出 ValueError"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("feishu:\n  app_secret: \"${MISSING_VAR}\"\n")

        with pytest.raises(ValueError, match="MISSING_VAR"):
            ConfigManager(str(config_path))


def test_config_manager_file_not_found():
    """测试配置文件不存在时抛出 FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        ConfigManager("/nonexistent/path/config.yaml")