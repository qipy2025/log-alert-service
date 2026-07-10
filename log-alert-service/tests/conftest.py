"""pytest 配置和共享 fixtures"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import yaml

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 设置测试环境
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """测试环境初始化"""
    os.environ["ENV"] = "test"
    # 确保测试环境变量存在
    if not os.path.exists(".env.test"):
        # 创建临时测试环境变量
        os.environ["FEISHU_TEST_APP_ID"] = "test_app_id"
        os.environ["FEISHU_TEST_APP_SECRET"] = "test_secret"
        os.environ["FEISHU_TEST_CHAT_ID"] = "test_chat_id"
        os.environ["CLAUDE_API_KEY"] = "test_api_key"
        os.environ["CLAUDE_API_BASE"] = "http://test.api"
    yield
    # 清理
    pass

@pytest.fixture
def test_config_path(tmp_path):
    """提供测试配置文件路径"""
    config_path = tmp_path / "config.test.yaml"
    config_data = {
        "log_source": {
            "type": "local",
            "path": str(tmp_path / "logs"),
            "polling_interval": 1,
            "encoding": "utf-8-sig",
            "max_context_lines": 10,
            "functional_log_window": 3,
        },
        "feishu": {
            "app_id": "${FEISHU_TEST_APP_ID}",
            "app_secret": "${FEISHU_TEST_APP_SECRET}",
            "chats": [
                {
                    "chat_id": "${FEISHU_TEST_CHAT_ID}",
                    "type": "test",
                    "name": "测试群"
                }
            ]
        },
        "ai_analysis": {
            "enabled": True,
            "api_key": "${CLAUDE_API_KEY}",
            "api_base_url": "${CLAUDE_API_BASE}",
            "model": "deepseek-v4-flash-anthropic",
            "max_tokens": 1024,
            "temperature": 0.3,
        },
        "dedup": {
            "alarm_window": 10,
            "max_repeat_count": 3,
        },
        "daily_report": {
            "enabled": True,
            "schedule_time": "00:00",
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)
    return str(config_path)

@pytest.fixture
def temp_log_dir(tmp_path):
    """临时日志目录"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir

@pytest.fixture
def mock_feishu_success():
    """飞书 API 成功响应 mock"""
    with patch('src.feishu_notifier.requests.post') as mock:
        mock.return_value = MagicMock(
            status_code=200,
            json=lambda: {"code": 0, "tenant_access_token": "test_token"}
        )
        yield mock

@pytest.fixture
def mock_ai_timeout():
    """AI API 超时响应 mock"""
    import requests
    with patch('src.ai_analyzer.requests.post') as mock:
        mock.side_effect = requests.exceptions.Timeout("AI API timeout")
        yield mock

@pytest.fixture
def sample_alarm_event():
    """示例告警事件"""
    from datetime import datetime
    from src.models import AlarmEvent, AlarmLevel, AlarmSource
    return AlarmEvent(
        timestamp=datetime(2026, 7, 9, 10, 30, 0),
        alarm_text="右点胶阀缺胶报警_人工请马上更换",
        module_name="DesaySV.Presentation.Core.FrmMain",
        level=AlarmLevel.CRITICAL,
        source=AlarmSource.DEFAULT_LOG,
        line_number=319,
        log_file="Default.log",
        raw_line="2026-07-09 10:30:00,000 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换",
        context_lines=[],
        functional_log_context=[],
        daily_count=1,
    )
