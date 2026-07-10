from sqlalchemy import Column, BigInteger, String, Text, DateTime, Index, JSON
from sqlalchemy.sql import func
from src.db.mysql import Base

class DeviceStatusHistory(Base):
    """设备状态变更历史表"""
    __tablename__ = 'device_status_history'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_name = Column(String(100), nullable=False, index=True)
    old_status = Column(String(20), nullable=False)
    new_status = Column(String(20), nullable=False)
    changed_by = Column(String(50))
    reason = Column(Text)
    changed_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'device_name': self.device_name,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'changed_by': self.changed_by,
            'reason': self.reason,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None
        }

class OperationLog(Base):
    """用户操作日志表"""
    __tablename__ = 'operation_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(50), index=True)
    operation = Column(String(50), nullable=False)
    target_device = Column(String(100), index=True)
    details = Column(JSON)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'operation': self.operation,
            'target_device': self.target_device,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
