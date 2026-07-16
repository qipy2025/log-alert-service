"""添加设备配置表和告警通知状态字段"""
from datetime import datetime
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def upgrade(session):
    """执行迁移"""
    # 创建设备配置表
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS device_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            device_name VARCHAR(100) UNIQUE NOT NULL,
            log_path VARCHAR(500) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            auto_notify BOOLEAN DEFAULT FALSE,
            polling_interval INT DEFAULT 2,
            encoding VARCHAR(20) DEFAULT 'utf-8-sig',
            log_name_mode VARCHAR(20) DEFAULT 'date_subdir',
            smb_username VARCHAR(100) NULL,
            smb_password VARCHAR(200) NULL,
            monitor_days INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_by VARCHAR(50) DEFAULT 'system',
            INDEX idx_device_name (device_name),
            INDEX idx_enabled (enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """))

    # 为 alarm_records 表添加 notified 字段
    try:
        session.execute(text("ALTER TABLE alarm_records ADD COLUMN notified BOOLEAN DEFAULT FALSE"))
        session.execute(text("ALTER TABLE alarm_records ADD INDEX idx_notified (notified)"))
        logger.info("已为 alarm_records 表添加 notified 字段")
    except Exception as e:
        if "Duplicate column name" in str(e):
            logger.info("notified 字段已存在，跳过")
        else:
            raise

    # 为 device_config 表添加网络共享认证与日志命名模式字段
    new_columns = [
        ("log_name_mode", "VARCHAR(20) DEFAULT 'date_subdir'"),
        ("smb_username", "VARCHAR(100) NULL"),
        ("smb_password", "VARCHAR(200) NULL"),
        ("monitor_days", "INT DEFAULT 1"),
    ]
    for col_name, col_def in new_columns:
        try:
            session.execute(text(f"ALTER TABLE device_config ADD COLUMN {col_name} {col_def}"))
            logger.info(f"已为 device_config 表添加 {col_name} 字段")
        except Exception as e:
            if "Duplicate column name" in str(e):
                logger.info(f"{col_name} 字段已存在，跳过")
            else:
                raise

    session.commit()
    logger.info("数据库迁移完成")


def downgrade(session):
    """回滚迁移"""
    session.execute(text("DROP TABLE IF EXISTS device_config"))
    try:
        session.execute(text("ALTER TABLE alarm_records DROP COLUMN notified"))
        session.execute(text("ALTER TABLE alarm_records DROP INDEX idx_notified"))
    except:
        pass
    session.commit()
    logger.info("数据库迁移已回滚")


def import_existing_devices(session):
    """从 config.yaml 导入现有设备配置"""
    from src.config_manager import ConfigManager

    config = ConfigManager('config.yaml')
    devices_config = config.get('devices', [])

    imported_count = 0
    for device in devices_config:
        device_name = device.get('name')
        log_path = device.get('log_path', '')
        enabled = device.get('enabled', True)

        # 检查是否已存在
        existing = session.execute(
            text("SELECT id FROM device_config WHERE device_name = :name"),
            {"name": device_name}
        ).fetchone()

        if not existing:
            session.execute(
                text("""INSERT INTO device_config (device_name, log_path, enabled)
                   VALUES (:name, :path, :enabled)"""),
                {"name": device_name, "path": log_path, "enabled": enabled}
            )
            imported_count += 1

    session.commit()
    logger.info(f"已导入 {imported_count} 个设备配置")
    return imported_count
