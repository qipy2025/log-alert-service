"""
数据库管理器 - 自动在MySQL和SQLite之间切换
"""
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

def init_database():
    """
    初始化数据库，优先使用MySQL，如果不可用则使用SQLite
    """
    # 检查MySQL配置是否完整
    mysql_configured = all([
        os.getenv('MYSQL_HOST'),
        os.getenv('MYSQL_USER'),
        os.getenv('MYSQL_PASSWORD'),
        os.getenv('MYSQL_DATABASE')
    ])

    if mysql_configured:
        try:
            logger.info("尝试连接MySQL数据库...")
            from .mysql import init_db, get_db_session, engine, SessionLocal, Base
            # 导入所有模型以确保表被创建
            from src.models.alarm import AlarmRecord
            from src.models.device import DeviceStatusHistory, OperationLog
            from src.models.device_config import DeviceConfig
            from src.models.notification_config_model import NotificationConfigModel
            init_db()
            logger.info("✅ MySQL数据库初始化成功")

            # 返回MySQL的接口
            return {
                'init_db': init_db,
                'get_db_session': get_db_session,
                'engine': engine,
                'SessionLocal': SessionLocal,
                'Base': Base,
                'type': 'mysql'
            }
        except Exception as e:
            logger.warning(f"MySQL连接失败: {e}")
            logger.info("回退到SQLite数据库...")
    else:
        logger.info("MySQL配置不完整，使用SQLite数据库")

    # 使用SQLite作为备选方案
    try:
        from .sqlite import init_db, get_db_session, engine, SessionLocal, Base
        # 导入所有模型以确保表被创建
        from src.models.alarm import AlarmRecord
        from src.models.device import DeviceStatusHistory, OperationLog
        from src.models.device_config import DeviceConfig
        from src.models.notification_config_model import NotificationConfigModel
        init_db()
        logger.info("✅ SQLite数据库初始化成功")

        # 返回SQLite的接口
        return {
            'init_db': init_db,
            'get_db_session': get_db_session,
            'engine': engine,
            'SessionLocal': SessionLocal,
            'Base': Base,
            'type': 'sqlite'
        }
    except Exception as e:
        logger.error(f"SQLite数据库初始化失败: {e}")
        raise

# 全局数据库接口
db_interface = None

def get_db_interface():
    """
    获取数据库接口
    """
    global db_interface
    if db_interface is None:
        db_interface = init_database()
    return db_interface

def get_session():
    """获取数据库会话"""
    interface = get_db_interface()
    return interface['get_db_session']()

# 重新导出常用的数据库接口
__all__ = ['get_db_interface', 'get_session', 'init_database']
