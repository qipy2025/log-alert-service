import pytest
from src.db.mysql import get_db_session, init_db
from src.db.cache import get_cache_client
from datetime import datetime

def test_mysql_connection():
    """测试MySQL连接"""
    session = get_db_session()
    assert session is not None
    session.close()

def test_cache_connection():
    """测试内存缓存连接"""
    cache = get_cache_client()
    assert cache is not None

def test_cache_set_get():
    """测试内存缓存读写"""
    cache = get_cache_client()
    cache.hset("test_key", {"field1": "value1"})
    value = cache.hgetall("test_key")
    assert value == {"field1": "value1"}
    cache.delete("test_key")
