import pytest
from datetime import datetime
from src.db.mysql import get_db_session
from src.models.alarm import AlarmRecord

def test_alarm_record_notified_field():
    """测试 AlarmRecord 的 notified 字段"""
    session = get_db_session()

    try:
        # 创建测试记录
        alarm = AlarmRecord(
            device_name="测试设备",
            alarm_level="CRITICAL",
            alarm_content="测试告警",
            log_timestamp=datetime.now(),
            notified=False
        )
        session.add(alarm)
        session.commit()

        # 查询并验证
        retrieved = session.query(AlarmRecord).filter_by(id=alarm.id).first()
        assert retrieved is not None
        assert retrieved.notified is False

        # 更新 notified 状态
        retrieved.notified = True
        session.commit()

        # 再次验证
        retrieved = session.query(AlarmRecord).filter_by(id=alarm.id).first()
        assert retrieved is not None
        assert retrieved.notified is True

        # 清理
        session.delete(retrieved)
        session.commit()

    finally:
        session.close()
