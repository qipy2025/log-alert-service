import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigManager:
    """管理配置文件和环境变量"""

    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = f.read()
        # 替换 ${VAR} 占位符为环境变量
        import re

        def _env_replace(match: re.Match) -> str:
            var_name = match.group(1)
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(f"Environment variable {var_name} is not set")
            return value

        resolved = re.sub(r"\$\{(\w+)\}", _env_replace, raw)
        self._config = yaml.safe_load(resolved)

    def get(self, key: str, default: Any = None) -> Any:
        """通过点号路径获取配置，如 'feishu.app_id'"""
        parts = key.split(".")
        value = self._config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def raw(self) -> dict[str, Any]:
        return self._config