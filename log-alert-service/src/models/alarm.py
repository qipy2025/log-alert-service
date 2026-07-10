from sqlalchemy import Column, BigInteger, String, Text, DateTime, Index
from sqlalchemy.sql import func
from src.db.mysql import Base

class AlarmRecord(Base):
    """告警记录表"""
    __tablename__ = 'alarm_records'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_name = Column(String(100), nullable=False, index=True)
    alarm_level = Column(String(20), nullable=False, index=True)
    alarm_content = Column(Text, nullable=False)
    ai_analysis = Column(Text)
    log_timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # 复合索引
    __table_args__ = (
        Index('idx_device_time', 'device_name', 'log_timestamp'),
        Index('idx_created', 'created_at'),
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'device_name': self.device_name,
            'alarm_level': self.alarm_level,
            'alarm_content': self.alarm_content,
            'ai_analysis': self.ai_analysis,
            'log_timestamp': self.log_timestamp.isoformat() if self.log_timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
