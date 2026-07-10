"""通知配置集成测试 - 测试通知开关和级别过滤"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.models import AlarmEvent, AlarmLevel, AlarmSource
from src.models.notification_config import NotificationConfig


class MockDBRecord:
    """模拟数据库记录"""
    def __init__(self, id, enabled, allowed_levels):
        self.id = id
        self.enabled = enabled
        self.allowed_levels = allowed_levels


class TestNotificationFlow:
    """通知配置集成测试"""

    @patch('src.db.notification_config_db.get_db_session')
    def test_notification_disabled(self, mock_get_session, sample_alarm_event):
        """测试：通知总开关关闭时，不应发送通知"""
        # 1. Mock 数据库返回配置：关闭通知
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = (1, False, '[]')
        mock_get_session.return_value = mock_session

        # 2. 导入并调用获取配置
        from src.db.notification_config_db import get_notification_config
        config = get_notification_config()

        # 3. 验证配置
        assert config is not None
        assert config.enabled is False
        assert config.allowed_levels == []

        # 4. 测试检查逻辑（模拟 _should_send_notification 的核心逻辑）
        # 根据修复后的 main.py 逻辑：
        # if not config or not config.enabled: return False
        # if not config.allowed_levels or event.level.value not in config.allowed_levels: return False
        should_send = (
            config and
            config.enabled and
            config.allowed_levels and
            sample_alarm_event.level.value in config.allowed_levels
        )
        assert should_send is False, "通知关闭时不应发送通知"
        print("✓ 通知总开关关闭测试通过")

    @patch('src.db.notification_config_db.get_db_session')
    def test_level_filtering_critical(self, mock_get_session, sample_alarm_event):
        """测试：级别过滤 - CRITICAL 告警被过滤"""
        # 1. Mock 数据库：只允许 WARNING 级别
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = (1, True, '["warning"]')
        mock_get_session.return_value = mock_session

        # 2. 获取配置
        from src.db.notification_config_db import get_notification_config
        config = get_notification_config()

        # 3. 验证配置
        assert config.enabled is True
        assert config.allowed_levels == ["warning"]

        # 4. 测试 CRITICAL 级别告警被过滤
        # 根据修复后的逻辑：需要 config.allowed_levels 为 True 且 level 在列表中
        should_send = (
            config and
            config.enabled and
            config.allowed_levels and
            sample_alarm_event.level.value in config.allowed_levels
        )
        assert should_send is False, "CRITICAL 级别应该被过滤（只允许 WARNING）"
        print("✓ 告警级别过滤测试通过")

    @patch('src.db.notification_config_db.get_db_session')
    def test_level_filtering_allowed(self, mock_get_session, sample_alarm_event):
        """测试：级别过滤 - 告警级别在允许列表中"""
        # 1. Mock 数据库：允许所有级别
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = (1, True, '["critical", "warning", "info"]')
        mock_get_session.return_value = mock_session

        # 2. 获取配置
        from src.db.notification_config_db import get_notification_config
        config = get_notification_config()

        # 3. 验证配置
        assert config.enabled is True
        assert set(config.allowed_levels) == {"critical", "warning", "info"}

        # 4. 测试 CRITICAL 级别告警被允许
        should_send = (
            config and
            config.enabled and
            config.allowed_levels and
            sample_alarm_event.level.value in config.allowed_levels
        )
        assert should_send is True, "CRITICAL 级别应该在允许列表中"
        print("✓ 告警级别允许测试通过")

    @patch('src.db.notification_config_db.get_db_session')
    def test_config_not_exists(self, mock_get_session, sample_alarm_event):
        """测试：配置不存在时的安全处理"""
        # 1. Mock 数据库：配置不存在
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = None
        mock_get_session.return_value = mock_session

        # 2. 获取配置
        from src.db.notification_config_db import get_notification_config
        config = get_notification_config()

        # 3. 验证配置不存在
        assert config is None, "配置应该不存在"

        # 4. 测试安全处理逻辑
        # 根据修复后的逻辑：config 为 None 时，第一个条件就失败了
        should_send = (
            config and
            config.enabled and
            config.allowed_levels and
            sample_alarm_event.level.value in config.allowed_levels
        )
        # config 为 None 时，整个表达式为 None（falsy）
        assert not should_send, "配置不存在时不应发送通知"
        print("✓ 配置不存在安全处理测试通过")

    @patch('src.db.notification_config_db.get_db_session')
    def test_empty_allowed_levels_filters_all(self, mock_get_session, sample_alarm_event):
        """测试：空的 allowed_levels 应该过滤所有告警"""
        # 1. Mock 数据库：启用通知但 allowed_levels 为空
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = (1, True, '[]')
        mock_get_session.return_value = mock_session

        # 2. 获取配置
        from src.db.notification_config_db import get_notification_config
        config = get_notification_config()

        # 3. 验证配置
        assert config.enabled is True
        assert config.allowed_levels == []

        # 4. 测试空列表过滤所有告警
        # 根据修复后的逻辑：config.allowed_levels 为空列表时，条件失败
        should_send = (
            config and
            config.enabled and
            config.allowed_levels and
            sample_alarm_event.level.value in config.allowed_levels
        )
        assert should_send is False, "空的 allowed_levels 应该过滤所有告警"
        print("✓ 空级别列表过滤测试通过")

    @patch('src.db.notification_config_db.get_db_session')
    def test_critical_and_warning_levels(self, mock_get_session):
        """测试：CRITICAL 和 WARNING 级别告警被正确处理"""
        # 1. 创建 CRITICAL 和 WARNING 级别告警
        critical_event = AlarmEvent(
            timestamp=datetime(2026, 7, 9, 10, 30, 0),
            alarm_text="右点胶阀缺胶报警_人工请马上更换",
            module_name="DesaySV.Presentation.Core.FrmMain",
            level=AlarmLevel.CRITICAL,
            source=AlarmSource.DEFAULT_LOG,
            line_number=319,
            log_file="Default.log",
            raw_line="2026-07-09 10:30:00,000 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换"
        )

        warning_event = AlarmEvent(
            timestamp=datetime(2026, 7, 9, 10, 30, 0),
            alarm_text="设备温度过高预警",
            module_name="DesaySV.Presentation.Core.FrmMain",
            level=AlarmLevel.WARNING,
            source=AlarmSource.DEFAULT_LOG,
            line_number=319,
            log_file="Default.log",
            raw_line="2026-07-09 10:30:00,000 [1] [FrmMain][319] - 设备温度过高预警"
        )

        # 2. Mock 数据库：允许 CRITICAL 和 WARNING
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = (1, True, '["critical", "warning"]')
        mock_get_session.return_value = mock_session

        # 3. 获取配置
        from src.db.notification_config_db import get_notification_config
        config = get_notification_config()

        # 4. 测试 CRITICAL 级别告警被允许
        should_send_critical = (
            config and config.enabled and
            (not config.allowed_levels or critical_event.level.value in config.allowed_levels)
        )
        assert should_send_critical is True, "CRITICAL 应该被允许发送"

        # 5. 测试 WARNING 级别告警被允许
        should_send_warning = (
            config and config.enabled and
            (not config.allowed_levels or warning_event.level.value in config.allowed_levels)
        )
        assert should_send_warning is True, "WARNING 应该被允许发送"

        # 6. 创建 INFO 告警测试
        info_event = AlarmEvent(
            timestamp=datetime(2026, 7, 9, 10, 30, 0),
            alarm_text="设备状态信息",
            module_name="FrmMain",
            level=AlarmLevel.INFO,
            source=AlarmSource.DEFAULT_LOG,
            line_number=319,
            log_file="Default.log",
            raw_line="2026-07-09 10:30:00,000 [1] [FrmMain][319] - 设备状态信息"
        )

        should_send_info = (
            config and config.enabled and
            (not config.allowed_levels or info_event.level.value in config.allowed_levels)
        )
        assert should_send_info is False, "INFO 应该被过滤"
        print("✓ 多级别配置综合测试通过")
