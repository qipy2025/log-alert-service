"""设备配置数据模型"""
from sqlalchemy import Column, BigInteger, String, Boolean, Integer, Text
from src.db.base import Base

class DeviceConfig(Base):
    """设备配置表"""
    __tablename__ = 'device_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_name = Column(String(100), nullable=False, unique=True, index=True)
    log_path = Column(String(500), nullable=False)
    auto_notify = Column(Boolean, default=False, nullable=False)
    polling_interval = Column(Integer, default=2, nullable=False)
    encoding = Column(String(20), default='utf-8-sig', nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    log_name_mode = Column(String(20), default='date_subdir')
    smb_username = Column(String(100))
    smb_password = Column(String(200))
    monitor_days = Column(Integer, default=1)
    created_at = Column(String(50))
    updated_at = Column(String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'device_name': self.device_name,
            'log_path': self.log_path,
            'auto_notify': self.auto_notify,
            'polling_interval': self.polling_interval,
            'encoding': self.encoding,
            'enabled': self.enabled,
            'log_name_mode': self.log_name_mode,
            'smb_username': self.smb_username,
            'smb_password': self.smb_password,
            'monitor_days': self.monitor_days
        }
