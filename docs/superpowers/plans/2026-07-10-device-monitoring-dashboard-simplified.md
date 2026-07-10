# 简化方案：使用SQLite和内存缓存

## 为什么采用这个方案

1. **无需额外安装**：SQLite是Python内置，内存缓存使用Python字典
2. **开发友好**：单文件数据库，易于调试和备份
3. **功能完整**：支持所有计划的SQL查询和缓存操作
4. **易于迁移**：后续需要时可以轻松切换到MySQL/Redis

## 技术调整

### 数据库层
```python
# 原方案：MySQL + pymysql
# 新方案：SQLite + sqlalchemy

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLite连接字符串
DATABASE_URL = "sqlite:///log_alert.db"

引擎配置相同，只需更改连接字符串
```

### 缓存层
```python
# 原方案：Redis
# 新方案：Python内存字典

class SimpleCache:
    def __init__(self):
        self._cache = {}
        self._ttl_cache = {}

    def hset(self, key, mapping):
        if key not in self._cache:
            self._cache[key] = {}
        self._cache[key].update(mapping)

    def hgetall(self, key):
        return self._cache.get(key, {})

    def incr(self, key):
        self._cache[key] = self._cache.get(key, 0) + 1
        return self._cache[key]

    # ... 其他Redis方法映射
```

## API兼容性

所有API接口保持不变，前端无需任何修改。

## 后续迁移

如果需要迁移到MySQL/Redis：

1. 数据库：只需更改连接字符串
2. 缓存：替换SimpleCache为redis.Redis
3. SQL语句：完全兼容（SQLite和MySQL都是SQL）

## 优势总结

- ✅ 零安装配置
- ✅ 立即可用
- ✅ 功能完整
- ✅ 易于部署
- ✅ 便于调试
