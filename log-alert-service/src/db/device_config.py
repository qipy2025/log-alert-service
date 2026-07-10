"""设备配置数据库操作"""
from typing import Optional, List
from sqlalchemy import text
from src.db.mysql import get_db_session
import logging

logger = logging.getLogger(__name__)

class DeviceConfig:
    """设备配置数据访问对象"""

    @staticmethod
    def create(device_name: str, log_path: str, auto_notify: bool = False,
               polling_interval: int = 2, encoding: str = 'utf-8-sig',
               enabled: bool = True) -> dict:
        """创建设备配置"""
        session = get_db_session()
        try:
            session.execute(
                text("""INSERT INTO device_config
                   (device_name, log_path, auto_notify, polling_interval, encoding, enabled)
                   VALUES (:name, :path, :auto_notify, :interval, :encoding, :enabled)"""),
                {
                    "name": device_name,
                    "path": log_path,
                    "auto_notify": auto_notify,
                    "interval": polling_interval,
                    "encoding": encoding,
                    "enabled": enabled
                }
            )
            session.commit()

            # 获取新创建的设备
            result = session.execute(
                text("SELECT * FROM device_config WHERE device_name = :name"),
                {"name": device_name}
            ).fetchone()

            return dict(result._mapping)
        except Exception as e:
            session.rollback()
            logger.error(f"创建设备配置失败: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def delete(device_name: str) -> bool:
        """删除设备配置"""
        session = get_db_session()
        try:
            result = session.execute(
                text("DELETE FROM device_config WHERE device_name = :name"),
                {"name": device_name}
            )
            session.commit()
            return result.rowcount > 0
        except Exception as e:
            session.rollback()
            logger.error(f"删除设备配置失败: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def get_by_name(device_name: str) -> Optional[dict]:
        """根据名称获取设备配置"""
        session = get_db_session()
        try:
            result = session.execute(
                text("SELECT * FROM device_config WHERE device_name = :name"),
                {"name": device_name}
            ).fetchone()
            return dict(result._mapping) if result else None
        finally:
            session.close()

    @staticmethod
    def get_all() -> List[dict]:
        """获取所有设备配置"""
        session = get_db_session()
        try:
            results = session.execute(text("SELECT * FROM device_config")).fetchall()
            return [dict(row._mapping) for row in results]
        finally:
            session.close()

    @staticmethod
    def update_auto_notify(device_name: str, auto_notify: bool) -> bool:
        """更新设备的自动发送设置"""
        session = get_db_session()
        try:
            result = session.execute(
                text("UPDATE device_config SET auto_notify = :auto_notify WHERE device_name = :name"),
                {"auto_notify": auto_notify, "name": device_name}
            )
            session.commit()
            return result.rowcount > 0
        except Exception as e:
            session.rollback()
            logger.error(f"更新自动发送设置失败: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def exists(device_name: str) -> bool:
        """检查设备是否存在"""
        return DeviceConfig.get_by_name(device_name) is not None
