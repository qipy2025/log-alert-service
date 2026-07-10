from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, BigInteger, String, Text, DateTime, Index
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# 基类
Base = declarative_base()

# 引擎配置
DATABASE_URL = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
    f"?charset=utf8mb4"
)

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
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
    global engine, SessionLocal
    try:
        # 先连接到MySQL服务器（不指定数据库）
        temp_engine = create_engine(
            f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
            f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}",
            echo=False
        )

        # 测试数据库连接
        with temp_engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            logger.info(f"MySQL连接成功: {version}")

            # 创建数据库（如果不存在）
            conn.execute(text("CREATE DATABASE IF NOT EXISTS log_alert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
            logger.info("数据库log_alert创建成功")

        # 重新连接到log_alert数据库
        engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

        from src.models.alarm import AlarmRecord
        from src.models.device import DeviceStatusHistory, OperationLog

        Base.metadata.create_all(bind=engine)
        logger.info("数据库表初始化完成")

        # 验证表已创建
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            logger.info(f"已创建的表: {tables}")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
