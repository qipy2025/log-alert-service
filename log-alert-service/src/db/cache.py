"""简单的内存缓存实现，替代Redis"""
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleCache:
    """简单的内存缓存，支持Redis常用操作"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl_cache: Dict[str, float] = {}
        self._lock = threading.Lock()

    def hset(self, key: str, mapping: Dict[str, Any]):
        """设置哈希字段"""
        with self._lock:
            if key not in self._cache:
                self._cache[key] = {}
            self._cache[key].update(mapping)
            logger.debug(f"缓存设置: {key} = {mapping}")

    def hget(self, key: str, field: str) -> Optional[Any]:
        """获取哈希字段"""
        with self._lock:
            if key in self._cache:
                return self._cache[key].get(field)
            return None

    def hgetall(self, key: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        with self._lock:
            return self._cache.get(key, {})

    def hdel(self, key: str, *fields):
        """删除哈希字段"""
        with self._lock:
            if key in self._cache:
                for field in fields:
                    self._cache[key].pop(field, None)
                if not self._cache[key]:
                    del self._cache[key]

    def delete(self, key: str):
        """删除键"""
        with self._lock:
            self._cache.pop(key, None)
            self._ttl_cache.pop(key, None)
            logger.debug(f"缓存删除: {key}")

    def incr(self, key: str, amount: int = 1) -> int:
        """增加计数"""
        with self._lock:
            current = self._cache.get(key, 0)
            if isinstance(current, dict):
                current = 0
            new_value = int(current) + amount
            self._cache[key] = new_value
            logger.debug(f"计数增加: {key} = {new_value}")
            return new_value

    def get(self, key: str) -> Optional[Any]:
        """获取键值"""
        with self._lock:
            # 检查TTL
            if key in self._ttl_cache:
                if time.time() > self._ttl_cache[key]:
                    self.delete(key)
                    return None
            return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置键值"""
        with self._lock:
            self._cache[key] = value
            if ttl:
                self._ttl_cache[key] = time.time() + ttl
            logger.debug(f"缓存设置: {key} = {value}")

    def expire(self, key: str, ttl: int):
        """设置过期时间"""
        with self._lock:
            if key in self._cache:
                self._ttl_cache[key] = time.time() + ttl
                logger.debug(f"设置TTL: {key} = {ttl}秒")

    def ping(self) -> bool:
        """测试连接"""
        return True

    def keys(self, pattern: str = "*") -> list:
        """获取所有匹配的键"""
        with self._lock:
            if pattern == "*":
                return list(self._cache.keys())
            # 简单的通配符匹配
            import fnmatch
            return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]

# 单例实例
_cache_client = None

def get_cache_client() -> SimpleCache:
    """获取缓存客户端（单例）"""
    global _cache_client
    if _cache_client is None:
        _cache_client = SimpleCache()
        logger.info("内存缓存初始化完成")
    return _cache_client

# 便捷函数，模仿Redis API
def set_device_status(device_name: str, status: str, changed_by: str = "system", reason: str = ""):
    """设置设备状态"""
    cache = get_cache_client()
    key = f"device:status:{device_name}"

    data = {
        "status": status,
        "last_heartbeat": datetime.now().isoformat(),
        "changed_by": changed_by
    }
    if reason:
        data["paused_reason"] = reason

    cache.hset(key, data)

def get_device_status(device_name: str) -> dict:
    """获取设备状态"""
    cache = get_cache_client()
    key = f"device:status:{device_name}"
    data = cache.hgetall(key)

    if not data:
        # 默认状态
        return {
            "status": "RUNNING",
            "last_heartbeat": None,
            "changed_by": "system"
        }
    return data

def increment_alarm_count(device_name: str) -> int:
    """增加设备告警计数"""
    cache = get_cache_client()
    key = f"device:alarm:count:{device_name}"

    # 设置到当天午夜过期
    tonight_midnight = (datetime.now().replace(hour=23, minute=59, second=59)
                       - datetime.now()).total_seconds()

    count = cache.incr(key)
    cache.expire(key, int(tonight_midnight))
    return count

def get_alarm_count(device_name: str) -> int:
    """获取设备今日告警计数"""
    cache = get_cache_client()
    key = f"device:alarm:count:{device_name}"
    value = cache.get(key)
    return int(value) if value else 0
