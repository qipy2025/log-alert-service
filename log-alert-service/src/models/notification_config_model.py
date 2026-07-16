"""通知配置数据模型"""
from sqlalchemy import Column, BigInteger, Boolean, String, Text
from sqlalchemy.orm import column_property
from src.db.base import Base

class NotificationConfigModel(Base):
    """通知配置表"""
    __tablename__ = 'notification_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, default=False, nullable=False)
    allowed_levels = Column(String(500), default='[]', nullable=False)
    created_at = Column(String(50))
    updated_at = Column(String(50))

    def to_dict(self):
        import json
        levels = []
        if self.allowed_levels:
            try:
                if isinstance(self.allowed_levels, str):
                    levels = json.loads(self.allowed_levels)
                elif isinstance(self.allowed_levels, list):
                    levels = self.allowed_levels
            except (json.JSONDecodeError, TypeError):
                levels = []

        return {
            'id': self.id,
            'enabled': self.enabled,
            'allowed_levels': levels
        }
