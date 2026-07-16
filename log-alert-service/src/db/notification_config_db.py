"""通知配置数据库操作层"""
import json
from sqlalchemy import text
from typing import Optional, List

from src.db.manager import get_session
from src.models.notification_config import NotificationConfig

# 常量定义
DEFAULT_CONFIG_ID = 1


class DBRecord:
    """数据库记录对象"""
    def __init__(self, id, enabled, allowed_levels):
        self.id = id
        self.enabled = enabled
        self.allowed_levels = allowed_levels


def get_notification_config() -> Optional[NotificationConfig]:
    """获取当前通知配置

    Returns:
        NotificationConfig 实例，如果不存在则返回 None

    Raises:
        RuntimeError: 数据库操作失败时抛出
    """
    session = get_session()
    try:
        # 使用原生 SQL 查询
        result = session.execute(
            text("SELECT id, enabled, allowed_levels FROM notification_config LIMIT 1")
        ).fetchone()

        if result:
            record = DBRecord(result[0], result[1], result[2])
            return NotificationConfig.from_db(record)
        return None
    except Exception as e:
        # 添加有意义的上下文信息，保留原始堆栈
        raise RuntimeError(f"Failed to get notification config: {e}") from e
    finally:
        session.close()


def update_notification_config(enabled: bool, allowed_levels: List[str]) -> NotificationConfig:
    """更新通知配置

    Args:
        enabled: 是否启用通知
        allowed_levels: 允许的告警级别列表

    Returns:
        更新后的 NotificationConfig 实例

    Raises:
        RuntimeError: 数据库操作失败时抛出
    """
    session = get_session()
    try:
        # 先判断记录是否存在，再 UPDATE 或 INSERT（SQLite/MySQL 兼容）
        levels_json = json.dumps(allowed_levels)
        existing = session.execute(
            text("SELECT id FROM notification_config WHERE id = 1")
        ).fetchone()
        if existing:
            session.execute(
                text("UPDATE notification_config SET enabled = :enabled, allowed_levels = :levels WHERE id = 1"),
                {"enabled": enabled, "levels": levels_json}
            )
        else:
            session.execute(
                text("INSERT INTO notification_config (id, enabled, allowed_levels) VALUES (1, :enabled, :levels)"),
                {"enabled": enabled, "levels": levels_json}
            )
        session.commit()

        # 直接构建返回对象，避免重复查询
        return NotificationConfig(
            id=DEFAULT_CONFIG_ID,
            enabled=enabled,
            allowed_levels=allowed_levels
        )
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to update notification config: {e}") from e
    finally:
        session.close()


def init_default_config() -> bool:
    """初始化默认配置（如果不存在）

    Returns:
            True 如果创建了新配置
            False 如果配置已存在

    Raises:
        RuntimeError: 数据库操作失败时抛出
    """
    session = get_session()
    try:
        # 检查是否已存在配置
        existing = session.execute(
            text("SELECT id FROM notification_config WHERE id = 1")
        ).fetchone()

        if not existing:
            # 插入默认配置（SQLite/MySQL 兼容：enabled=0，allowed_levels='[]'）
            session.execute(
                text("INSERT INTO notification_config (id, enabled, allowed_levels) VALUES (1, 0, '[]')")
            )
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to init default config: {e}") from e
    finally:
        session.close()
