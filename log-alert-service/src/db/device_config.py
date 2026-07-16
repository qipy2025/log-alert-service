"""设备配置数据库操作"""
from typing import Optional, List
from sqlalchemy import text
from src.db.manager import get_session
import logging

logger = logging.getLogger(__name__)

class DeviceConfig:
    """设备配置数据访问对象"""

    @staticmethod
    def create(device_name: str, log_path: str, auto_notify: bool = False,
               polling_interval: int = 2, encoding: str = 'utf-8-sig',
               enabled: bool = True, log_name_mode: str = 'date_subdir',
               smb_username: str = None, smb_password: str = None,
               monitor_days: int = 1) -> dict:
        """创建设备配置"""
        session = get_session()
        try:
            session.execute(
                text("""INSERT INTO device_config
                   (device_name, log_path, auto_notify, polling_interval, encoding, enabled,
                    log_name_mode, smb_username, smb_password, monitor_days)
                   VALUES (:name, :path, :auto_notify, :interval, :encoding, :enabled,
                    :log_name_mode, :smb_username, :smb_password, :monitor_days)"""),
                {
                    "name": device_name,
                    "path": log_path,
                    "auto_notify": auto_notify,
                    "interval": polling_interval,
                    "encoding": encoding,
                    "enabled": enabled,
                    "log_name_mode": log_name_mode,
                    "smb_username": smb_username,
                    "smb_password": smb_password,
                    "monitor_days": monitor_days
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
        session = get_session()
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
        session = get_session()
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
        session = get_session()
        try:
            results = session.execute(text("SELECT * FROM device_config")).fetchall()
            return [dict(row._mapping) for row in results]
        finally:
            session.close()

    @staticmethod
    def update_auto_notify(device_name: str, auto_notify: bool) -> bool:
        """更新设备的自动发送设置"""
        session = get_session()
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
    def update(device_name: str, log_path: str = None, auto_notify: bool = None,
               polling_interval: int = None, encoding: str = None, enabled: bool = None,
               log_name_mode: str = None, smb_username: str = None,
               smb_password: str = None, monitor_days: int = None) -> bool:
        """更新设备配置

        Args:
            device_name: 设备名称
            log_path: 新的日志路径（可选）
            auto_notify: 新的自动通知设置（可选）
            polling_interval: 新的轮询间隔（可选）
            encoding: 新的编码（可选）
            enabled: 新的启用状态（可选）
            log_name_mode: 日志命名模式（可选）
            smb_username: 网络共享用户名（可选）
            smb_password: 网络共享密码（Base64，可选）
            monitor_days: 监控天数（可选）

        Returns:
            是否更新成功
        """
        session = get_session()
        try:
            # 构建更新字段字典
            update_fields = {}
            if log_path is not None:
                update_fields['log_path'] = log_path
            if auto_notify is not None:
                update_fields['auto_notify'] = auto_notify
            if polling_interval is not None:
                update_fields['polling_interval'] = polling_interval
            if encoding is not None:
                update_fields['encoding'] = encoding
            if enabled is not None:
                update_fields['enabled'] = enabled
            if log_name_mode is not None:
                update_fields['log_name_mode'] = log_name_mode
            if smb_username is not None:
                update_fields['smb_username'] = smb_username
            if smb_password is not None:
                update_fields['smb_password'] = smb_password
            if monitor_days is not None:
                update_fields['monitor_days'] = monitor_days

            if not update_fields:
                return False

            # 构建 SET 子句
            set_clause = ', '.join(f"{field} = :{field}" for field in update_fields.keys())
            update_fields['name'] = device_name

            result = session.execute(
                text(f"UPDATE device_config SET {set_clause} WHERE device_name = :name"),
                update_fields
            )
            session.commit()
            return result.rowcount > 0
        except Exception as e:
            session.rollback()
            logger.error(f"更新设备配置失败: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def exists(device_name: str) -> bool:
        """检查设备是否存在"""
        return DeviceConfig.get_by_name(device_name) is not None
