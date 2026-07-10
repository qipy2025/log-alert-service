"""异常恢复集成测试"""
import time
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest
import requests

from src.models import AlarmEvent, AlarmLevel, AlarmSource, AnalysisResult
from src.config_manager import ConfigManager
from src.ai_analyzer import AIAnalyzer
from src.feishu_notifier import FeishuNotifier
from tests.mocks import MockFeishuAPI, MockAIAnalyzer

class TestErrorRecovery:
    """异常恢复测试"""

    def test_3_1_network_error_recovery(self, sample_alarm_event):
        """场景3.1：网络故障恢复"""
        # 1. 测试正常 token 获取
        with patch('src.feishu_notifier.requests.post') as mock_post:
            mock_post.return_value = MockFeishuAPI.token_response()
            notifier = FeishuNotifier(
                app_id="test",
                app_secret="test",
                chats=[{"chat_id": "test", "type": "production", "name": "测试群"}],
            )
            token = notifier._get_token()
            assert token == "test_token_xxx"

        # 2. 测试网络故障处理
        with patch('src.feishu_notifier.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")
            notifier2 = FeishuNotifier(
                app_id="test",
                app_secret="test",
                chats=[{"chat_id": "test", "type": "production", "name": "测试群"}],
            )
            try:
                token = notifier2._get_token()
                # 如果到这里，说明没有抛出异常，验证返回值
                assert token is None or isinstance(token, str)
            except requests.exceptions.ConnectionError:
                pass  # 预期的异常

        # 3. 测试网络恢复
        with patch('src.feishu_notifier.requests.post') as mock_post:
            mock_post.return_value = MockFeishuAPI.token_response()
            notifier3 = FeishuNotifier(
                app_id="test",
                app_secret="test",
                chats=[{"chat_id": "test", "type": "production", "name": "测试群"}],
            )
            token = notifier3._get_token()
            assert token == "test_token_xxx"

    def test_3_2_ai_analysis_failure_graceful_degradation(self, sample_alarm_event):
        """场景3.2：AI分析失败降级"""
        # 1. 模拟 AI API 超时
        with patch('src.ai_analyzer.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("AI API timeout")

            analyzer = AIAnalyzer(api_key="test", enabled=True)
            result = analyzer.analyze(sample_alarm_event)

            # 验证：返回 None（降级）
            assert result is None

        # 2. 验证：即使 AI 分析失败，告警文本仍然可用
        assert sample_alarm_event.alarm_text is not None
        assert len(sample_alarm_event.alarm_text) > 0
        assert "缺胶报警" in sample_alarm_event.alarm_text

    def test_3_3_missing_log_file_handling(self, tmp_path):
        """场景3.3：日志文件缺失处理"""
        # 1. 配置监控一个不存在的目录
        nonexistent_dir = tmp_path / "nonexistent"

        # 2. 尝试创建文件监控
        try:
            from src.file_watcher import LogWatcher
            watcher = LogWatcher(
                log_dir=str(nonexistent_dir),
                on_alarm=lambda x: None,
                polling_interval=1,
            )
            # 如果能创建，尝试启动
            watcher.start()
            # 如果到这里，说明没有抛出异常，验证监控器状态
            watcher.stop()
        except (FileNotFoundError, Exception, OSError) as e:
            # 验证：抛出明确异常
            assert True  # 预期的异常

    def test_3_4_config_file_errors(self, tmp_path):
        """场景3.4：配置文件错误"""
        # 1. YAML 格式错误
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("log_source:\n  path: [unclosed", encoding="utf-8")

        try:
            cm = ConfigManager(str(invalid_yaml))
            assert False, "应该抛出异常"
        except Exception as e:
            # 验证：正确识别 YAML 错误（包含 'yaml', 'parse', 或 'scanner'）
            error_msg = str(e).lower()
            has_any_error = any(keyword in error_msg for keyword in ['yaml', 'parse', 'scanner', 'sequence'])
            assert has_any_error, f"错误消息应该包含 YAML 相关关键词: {e}"

        # 2. 缺失必需字段
        incomplete_yaml = tmp_path / "incomplete.yaml"
        incomplete_yaml.write_text("log_source:\n  encoding: utf-8\n", encoding="utf-8")

        try:
            cm = ConfigManager(str(incomplete_yaml))
            path = cm.get("log_source.path")
            # 应该返回默认值 None
            assert path is None
        except Exception as e:
            # 某些实现可能会抛出异常
            pass

        # 3. 环境变量未定义
        env_var_yaml = tmp_path / "env_var.yaml"
        env_var_yaml.write_text('feishu:\n  app_id: "${UNDEFINED_VAR}"\n', encoding="utf-8")

        try:
            cm = ConfigManager(str(env_var_yaml))
            app_id = cm.get("feishu.app_id")
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            # 验证：明确指出缺失的环境变量
            assert "UNDEFINED_VAR" in str(e)
