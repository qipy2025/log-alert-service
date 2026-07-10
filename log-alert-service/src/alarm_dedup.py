import time
from typing import Optional
from src.data_models import AlarmEvent
from src.models.alarm import AlarmRecord
import logging

logger = logging.getLogger(__name__)


def store_alarm_to_db(event: AlarmEvent, analysis=None) -> None:
    """存储告警到数据库"""
    from src.db.mysql import get_db_session
    from src.db.cache import increment_alarm_count

    session = get_db_session()
    try:
        # 映射AlarmEvent到AlarmRecord
        device_name = event.module_name  # 使用module_name作为设备名
        alarm_level = str(event.level.value).upper()  # 转换为字符串

        # 构建AI分析JSON
        ai_analysis_json = None
        if analysis:
            import json
            ai_analysis_json = json.dumps({
                'root_cause': analysis.root_cause,
                'severity': analysis.severity,
                'suggestion': analysis.suggestion,
                'related_module': analysis.related_module,
                'probable_time_to_resolve': analysis.probable_time_to_resolve
            }, ensure_ascii=False)

        alarm = AlarmRecord(
            device_name=device_name,
            alarm_level=alarm_level,
            alarm_content=event.alarm_text,
            ai_analysis=ai_analysis_json,
            log_timestamp=event.timestamp
        )
        session.add(alarm)
        session.commit()

        # 更新内存缓存计数
        increment_alarm_count(device_name)

        logger.info(f"告警已存储: {device_name} - {alarm_level}")
    except Exception as e:
        logger.error(f"存储告警失败: {e}")
        session.rollback()
    finally:
        session.close()


class AlarmDedup:
    """告警去重器：相同 (告警文本摘要, 模块名) 在窗口内合并"""

    def __init__(self, window_seconds: int = 300, max_repeat: int = 99):
        self.window = window_seconds
        self.max_repeat = max_repeat
        # { dedup_key: (first_timestamp, count, last_notified_count) }
        self._cache: dict[str, tuple[float, int, int]] = {}

    def _make_key(self, event: AlarmEvent) -> str:
        """生成去重键：告警文本前 20 字 + 模块名"""
        text_key = event.alarm_text[:20]
        return f"{text_key}|{event.module_name}"

    def should_notify(self, event: AlarmEvent) -> bool:
        """
        判断是否应该推送此告警。
        返回 True 表示需要推送（首次出现或窗口超时）。
        返回 False 表示在去重窗口内。
        """
        key = self._make_key(event)
        now = time.time()

        if key not in self._cache:
            self._cache[key] = (now, 1, 1)
            return True

        first_time, count, last_notified = self._cache[key]
        elapsed = now - first_time

        if elapsed > self.window:
            # 窗口超时，重置
            self._cache[key] = (now, count + 1, 1)
            return True

        # 窗口内
        self._cache[key] = (first_time, count + 1, last_notified)

        # 如果超过最大重复次数，强制推送
        if count + 1 >= self.max_repeat:
            self._cache[key] = (first_time, count + 1, count + 1)
            return True

        return False

    def get_repeat_count(self, event: AlarmEvent) -> int:
        """获取当前告警的重复次数"""
        key = self._make_key(event)
        if key not in self._cache:
            return 0
        return self._cache[key][1]

    def cleanup(self, max_age: float = 3600) -> None:
        """清理超过 max_age 秒的缓存"""
        now = time.time()
        stale = [k for k, v in self._cache.items() if now - v[0] > max_age]
        for k in stale:
            del self._cache[k]