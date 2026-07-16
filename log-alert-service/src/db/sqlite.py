from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, BigInteger, String, Text, DateTime, Index
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

# 基类
Base = declarative_base()

# SQLite数据库文件路径
DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/sqlite.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 引擎配置
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db_session():
    """获取数据库会话"""
    session = SessionLocal()
    try:
        return session
    except Exception as e:
        session.close()
        logger.error(f"获取数据库会话失败: {e}")
        raise e

def init_db():
    """初始化数据库表"""
    try:
        # 创建数据库文件和表
        from src.models.alarm import AlarmRecord
        from src.models.device import DeviceStatusHistory, OperationLog
        from src.models.device_config import DeviceConfig
        from src.models.notification_config_model import NotificationConfigModel

        Base.metadata.create_all(bind=engine)
        logger.info(f"SQLite数据库初始化完成: {DB_PATH}")

        # 验证表已创建
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            logger.info(f"已创建的表: {tables}")

        # 初始化默认通知配置
        init_default_config()

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

def init_default_config():
    """初始化默认通知配置"""
    try:
        from src.models.notification_config_model import NotificationConfigModel
        from sqlalchemy import text

        # 检查是否已有配置
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM notification_config")).scalar()
            if result == 0:
                # 插入默认配置
                conn.execute(
                    text("INSERT INTO notification_config (enabled, allowed_levels) VALUES (:enabled, :levels)"),
                    {"enabled": False, "levels": '["CRITICAL", "WARNING", "INFO"]'}
                )
                conn.commit()
                logger.info("默认通知配置已创建")
    except Exception as e:
        logger.warning(f"创建默认配置失败: {e}")
