"""通知配置数据库操作层"""
import json
from sqlalchemy import text
from typing import Optional, List

from src.db.mysql import get_db_session
from src.models.notification_config import NotificationConfig


def get_notification_config() -> Optional[NotificationConfig]:
    """获取当前通知配置

    Returns:
        NotificationConfig 实例，如果不存在则返回 None
    """
    session = get_db_session()
    try:
        # 使用原生 SQL 查询
        result = session.execute(
            text("SELECT id, enabled, allowed_levels FROM notification_config LIMIT 1")
        ).fetchone()

        if result:
            # 创建一个简单的对象来模拟数据库记录
            class Record:
                def __init__(self, id, enabled, allowed_levels):
                    self.id = id
                    self.enabled = enabled
                    self.allowed_levels = allowed_levels

            record = Record(result[0], result[1], result[2])
            return NotificationConfig.from_db(record)
        return None
    except Exception as e:
        raise e
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
        Exception: 数据库操作失败时抛出异常
    """
    session = get_db_session()
    try:
        # 使用 UPSERT 确保始终有一条记录（id=1）
        session.execute(
            text("""
                INSERT INTO notification_config (id, enabled, allowed_levels)
                VALUES (1, :enabled, :levels)
                ON DUPLICATE KEY UPDATE
                    enabled = :enabled,
                    allowed_levels = :levels
            """),
            {"enabled": enabled, "levels": json.dumps(allowed_levels)}
        )
        session.commit()

        # 返回更新后的配置
        return get_notification_config()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def init_default_config():
    """初始化默认配置（如果不存在）"""
    session = get_db_session()
    try:
        # 检查是否已存在配置
        existing = session.execute(
            text("SELECT id FROM notification_config WHERE id = 1")
        ).fetchone()

        if not existing:
            # 插入默认配置
            session.execute(
                text("""
                    INSERT INTO notification_config (id, enabled, allowed_levels)
                    VALUES (1, FALSE, '[]')
                """)
            )
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
