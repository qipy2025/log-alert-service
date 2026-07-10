# 飞书通知配置开关实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为飞书通知系统添加可配置开关，支持全局开关和告警级别过滤，默认状态为禁用

**架构：** 创建 notification_config 数据库表存储配置，提供 Web API 进行配置管理，在核心告警处理流程中添加配置检查逻辑

**技术栈：** Python 3.8+, Flask, MySQL, SQLAlchemy, WebSocket, pytest

---

## 文件结构

### 新建文件
- `src/models/notification_config.py` - 通知配置数据模型
- `src/db/notification_config_db.py` - 数据库操作层
- `tests/unit/test_notification_config.py` - 单元测试
- `tests/integration/test_notification_flow.py` - 集成测试

### 修改文件
- `src/main.py` - 添加配置检查逻辑
- `src/web/routes.py` - 添加配置管理 API
- `src/web/socketio.py` - 添加配置更新广播

---

## 任务 1：创建数据库表和初始数据

**文件：**
- 创建：`migrations/add_notification_config.sql`
- 修改：无
- 测试：无

- [ ] **步骤 1：编写数据库迁移脚本**

创建文件 `migrations/add_notification_config.sql`：

```sql
-- 创建通知配置表
CREATE TABLE IF NOT EXISTS notification_config (
  id INT PRIMARY KEY AUTO_INCREMENT,
  enabled BOOLEAN DEFAULT FALSE COMMENT '总开关，默认关闭',
  allowed_levels JSON COMMENT '允许的告警级别，如 ["CRITICAL", "WARNING"]',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 插入默认配置：禁用通知，空级别列表
INSERT INTO notification_config (id, enabled, allowed_levels)
VALUES (1, FALSE, '[]')
ON DUPLICATE KEY UPDATE id=id;
```

- [ ] **步骤 2：手动执行迁移脚本验证语法**

在 MySQL 中执行：

```bash
mysql -h localhost -u root -p device_monitoring < migrations/add_notification_config.sql
```

预期：无错误，表创建成功

- [ ] **步骤 3：验证表结构和默认数据**

```bash
mysql -h localhost -u root -p device_monitoring -e "SELECT * FROM notification_config;"
```

预期输出：
```
+----+---------+----------------+---------------------+---------------------+
| id | enabled | allowed_levels | updated_at          | created_at          |
+----+---------+----------------+---------------------+---------------------+
|  1 |       0 | []             | 2026-07-10 xx:xx:xx | 2026-07-10 xx:xx:xx |
+----+---------+----------------+---------------------+---------------------+
```

- [ ] **步骤 4：Commit**

```bash
git add migrations/add_notification_config.sql
git commit -m "feat: add notification_config table with default disabled state"
```

---

## 任务 2：创建通知配置数据模型

**文件：**
- 创建：`src/models/notification_config.py`
- 修改：无
- 测试：`tests/unit/test_notification_config.py`

- [ ] **步骤 1：编写数据模型代码**

创建文件 `src/models/notification_config.py`：

```python
"""通知配置数据模型"""
from dataclasses import dataclass
from typing import Optional, List
import json


@dataclass
class NotificationConfig:
    """通知配置数据模型"""
    id: int
    enabled: bool
    allowed_levels: List[str]
    
    @classmethod
    def from_db(cls, record) -> 'NotificationConfig':
        """从数据库记录创建模型
        
        Args:
            record: 数据库记录对象，包含 id, enabled, allowed_levels 字段
            
        Returns:
            NotificationConfig 实例
        """
        levels = []
        if record and hasattr(record, 'allowed_levels') and record.allowed_levels:
            try:
                # 如果是字符串，解析 JSON
                if isinstance(record.allowed_levels, str):
                    levels = json.loads(record.allowed_levels)
                # 如果已经是列表，直接使用
                elif isinstance(record.allowed_levels, list):
                    levels = record.allowed_levels
            except (json.JSONDecodeError, TypeError):
                # 解析失败，返回空列表
                levels = []
        
        return cls(
            id=record.id if record and hasattr(record, 'id') else 1,
            enabled=record.enabled if record and hasattr(record, 'enabled') else False,
            allowed_levels=levels
        )
```

- [ ] **步骤 2：编写测试验证数据模型**

创建文件 `tests/unit/test_notification_config.py`：

```python
"""测试通知配置数据模型"""
import pytest
from unittest.mock import MagicMock
from src.models.notification_config import NotificationConfig


class TestNotificationConfig:
    """测试 NotificationConfig 数据模型"""
    
    def test_from_db_with_valid_data(self):
        """测试从有效数据库记录创建模型"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = True
        mock_record.allowed_levels = '["CRITICAL", "WARNING"]'
        
        config = NotificationConfig.from_db(mock_record)
        
        assert config.id == 1
        assert config.enabled is True
        assert config.allowed_levels == ["CRITICAL", "WARNING"]
    
    def test_from_db_with_list_data(self):
        """测试从列表类型的 allowed_levels 创建模型"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = False
        mock_record.allowed_levels = ["CRITICAL"]  # 已经是列表
        
        config = NotificationConfig.from_db(mock_record)
        
        assert config.allowed_levels == ["CRITICAL"]
    
    def test_from_db_with_empty_array(self):
        """测试空数组配置"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = False
        mock_record.allowed_levels = '[]'
        
        config = NotificationConfig.from_db(mock_record)
        
        assert config.enabled is False
        assert config.allowed_levels == []
    
    def test_from_db_with_null_levels(self):
        """测试 allowed_levels 为 None 的情况"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = True
        mock_record.allowed_levels = None
        
        config = NotificationConfig.from_db(mock_record)
        
        assert config.allowed_levels == []
    
    def test_from_db_with_invalid_json(self):
        """测试无效的 JSON 字符串"""
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.enabled = True
        mock_record.allowed_levels = 'invalid-json'
        
        config = NotificationConfig.from_db(mock_record)
        
        # 解析失败时应该返回空列表
        assert config.allowed_levels == []
    
    def test_from_db_with_none_record(self):
        """测试 record 为 None 的情况"""
        config = NotificationConfig.from_db(None)
        
        assert config.id == 1
        assert config.enabled is False
        assert config.allowed_levels == []
```

- [ ] **步骤 3：运行测试验证失败**

```bash
cd /d/code/LOG/log-alert-service
source venv/Scripts/activate
pytest tests/unit/test_notification_config.py -v
```

预期：FAIL，报错 "ModuleNotFoundError: No module named 'src.models.notification_config'"

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/unit/test_notification_config.py -v
```

预期：PASS，所有 6 个测试通过

- [ ] **步骤 5：Commit**

```bash
git add src/models/notification_config.py tests/unit/test_notification_config.py
git commit -m "feat: add NotificationConfig data model with tests"
```

---

## 任务 3：创建数据库操作层

**文件：**
- 创建：`src/db/notification_config_db.py`
- 修改：无
- 测试：`tests/unit/test_notification_config_db.py`

- [ ] **步骤 1：编写数据库操作代码**

创建文件 `src/db/notification_config_db.py`：

```python
"""通知配置数据库操作层"""
import json
from sqlalchemy import text
from typing import Optional, List

from src.db.mysql import get_db_session
from src.models.notification_config import NotificationConfig


def get_notification_config() -> Optional[NotificationConfig]:
    """获取当前通知配置
    
    Returns:
        NotificationConfig 实例，如果不存在则返回 None
    """
    session = get_db_session()
    try:
        # 使用原生 SQL 查询
        result = session.execute(
            text("SELECT id, enabled, allowed_levels FROM notification_config LIMIT 1")
        ).fetchone()
        
        if result:
            # 创建一个简单的对象来模拟数据库记录
            class Record:
                def __init__(self, id, enabled, allowed_levels):
                    self.id = id
                    self.enabled = enabled
                    self.allowed_levels = allowed_levels
            
            record = Record(result[0], result[1], result[2])
            return NotificationConfig.from_db(record)
        return None
    except Exception as e:
        raise e
    finally:
        session.close()


def update_notification_config(enabled: bool, allowed_levels: List[str]) -> NotificationConfig:
    """更新通知配置
    
    Args:
        enabled: 是否启用通知
        allowed_levels: 允许的告警级别列表
        
    Returns:
        更新后的 NotificationConfig 实例
        
    Raises:
        Exception: 数据库操作失败时抛出异常
    """
    session = get_db_session()
    try:
        # 使用 UPSERT 确保始终有一条记录（id=1）
        session.execute(
            text("""
                INSERT INTO notification_config (id, enabled, allowed_levels)
                VALUES (1, :enabled, :levels)
                ON DUPLICATE KEY UPDATE 
                    enabled = :enabled, 
                    allowed_levels = :levels
            """),
            {"enabled": enabled, "levels": json.dumps(allowed_levels)}
        )
        session.commit()
        
        # 返回更新后的配置
        return get_notification_config()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def init_default_config():
    """初始化默认配置（如果不存在）"""
    session = get_db_session()
    try:
        # 检查是否已存在配置
        existing = session.execute(
            text("SELECT id FROM notification_config WHERE id = 1")
        ).fetchone()
        
        if not existing:
            # 插入默认配置
            session.execute(
                text("""
                    INSERT INTO notification_config (id, enabled, allowed_levels)
                    VALUES (1, FALSE, '[]')
                """)
            )
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
```

- [ ] **步骤 2：编写数据库操作测试**

创建文件 `tests/unit/test_notification_config_db.py`：

```python
"""测试通知配置数据库操作层"""
import pytest
from unittest.mock import patch, MagicMock
from src.db.notification_config_db import get_notification_config, update_notification_config, init_default_config
from src.models.notification_config import NotificationConfig


class TestNotificationConfigDB:
    """测试通知配置数据库操作"""
    
    @patch('src.db.notification_config_db.get_db_session')
    def test_get_notification_config_success(self, mock_get_session):
        """测试成功获取配置"""
        # 模拟数据库返回结果
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__getitem__ = lambda self, key: [1, True, '["CRITICAL"]'][key]
        mock_session.execute().fetchone.return_value = mock_result
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        config = get_notification_config()
        
        assert config is not None
        assert config.enabled is True
        assert config.allowed_levels == ["CRITICAL"]
    
    @patch('src.db.notification_config_db.get_db_session')
    def test_get_notification_config_not_found(self, mock_get_session):
        """测试配置不存在时返回 None"""
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        config = get_notification_config()
        
        assert config is None
    
    @patch('src.db.notification_config_db.get_db_session')
    @patch('src.db.notification_config_db.get_notification_config')
    def test_update_notification_config_success(self, mock_get_config, mock_get_session):
        """测试成功更新配置"""
        # 模拟更新后的配置
        mock_config = NotificationConfig(id=1, enabled=True, allowed_levels=["CRITICAL", "WARNING"])
        mock_get_config.return_value = mock_config
        
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        config = update_notification_config(True, ["CRITICAL", "WARNING"])
        
        assert config.enabled is True
        assert config.allowed_levels == ["CRITICAL", "WARNING"]
        mock_session.commit.assert_called_once()
    
    @patch('src.db.notification_config_db.get_db_session')
    def test_init_default_config_creates_new(self, mock_get_session):
        """测试初始化配置（不存在时创建）"""
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        result = init_default_config()
        
        assert result is True
        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()
    
    @patch('src.db.notification_config_db.get_db_session')
    def test_init_default_config_already_exists(self, mock_get_session):
        """测试初始化配置（已存在时不创建）"""
        mock_session = MagicMock()
        mock_session.execute().fetchone.return_value = MagicMock()  # 存在记录
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        result = init_default_config()
        
        assert result is False
        # 不应该执行 INSERT
        assert mock_session.execute.call_count == 1
```

- [ ] **步骤 3：运行测试验证失败**

```bash
pytest tests/unit/test_notification_config_db.py -v
```

预期：FAIL，报错模块不存在

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/unit/test_notification_config_db.py -v
```

预期：PASS，所有 4 个测试通过

- [ ] **步骤 5：Commit**

```bash
git add src/db/notification_config_db.py tests/unit/test_notification_config_db.py
git commit -m "feat: add notification config database operations layer"
```

---

## 任务 4：添加 Web API 路由

**文件：**
- 修改：`src/web/routes.py`
- 测试：`tests/unit/test_api_notification_config.py`

- [ ] **步骤 1：读取现有路由文件**

```bash
head -50 src/web/routes.py
```

了解现有导入和结构

- [ ] **步骤 2：在 routes.py 顶部添加导入**

在 `src/web/routes.py` 文件顶部的导入区域添加：

```python
from src.db.notification_config_db import get_notification_config, update_notification_config
from src.web.socketio import broadcast_config_update
```

- [ ] **步骤 3：在 routes.py 中添加配置管理 API**

在 `src/web/routes.py` 文件末尾添加：

```python
@app.route('/api/notification-config', methods=['GET'])
def get_notification_config_api():
    """获取通知配置
    
    返回当前的通知配置，包括总开关状态和允许的告警级别
    """
    try:
        config = get_notification_config()
        if not config:
            # 返回默认配置
            return jsonify({
                'enabled': False,
                'allowed_levels': []
            })
        return jsonify({
            'enabled': config.enabled,
            'allowed_levels': config.allowed_levels
        })
    except Exception as e:
        logger.error(f"获取通知配置失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/notification-config', methods=['PUT'])
def update_notification_config_api():
    """更新通知配置
    
    Request Body:
        enabled: boolean - 是否启用通知
        allowed_levels: array of string - 允许的告警级别列表
        
    Returns:
        更新后的配置信息
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        enabled = data.get('enabled', False)
        allowed_levels = data.get('allowed_levels', [])
        
        # 验证 allowed_levels 必须是列表
        if not isinstance(allowed_levels, list):
            return jsonify({'error': 'allowed_levels must be an array'}), 400
        
        # 验证告警级别的有效性
        valid_levels = {'CRITICAL', 'WARNING', 'INFO'}
        for level in allowed_levels:
            if level not in valid_levels:
                return jsonify({'error': f'Invalid alarm level: {level}. Valid levels are: CRITICAL, WARNING, INFO'}), 400
        
        # 更新配置
        config = update_notification_config(enabled, allowed_levels)
        
        # 广播配置更新到所有 WebSocket 客户端
        broadcast_config_update({
            'enabled': config.enabled,
            'allowed_levels': config.allowed_levels
        })
        
        return jsonify({
            'success': True,
            'config': {
                'enabled': config.enabled,
                'allowed_levels': config.allowed_levels
            }
        })
    except Exception as e:
        logger.error(f"更新通知配置失败: {e}")
        return jsonify({'error': str(e)}), 500
```

- [ ] **步骤 4：编写 API 测试**

创建文件 `tests/unit/test_api_notification_config.py`：

```python
"""测试通知配置 API"""
import pytest
import json
from unittest.mock import patch, MagicMock
from src.models.notification_config import NotificationConfig


class TestNotificationConfigAPI:
    """测试通知配置 API 接口"""
    
    @patch('src.web.routes.get_notification_config')
    def test_get_config_success(self, mock_get_config, client):
        """测试成功获取配置"""
        mock_config = NotificationConfig(id=1, enabled=True, allowed_levels=["CRITICAL"])
        mock_get_config.return_value = mock_config
        
        response = client.get('/api/notification-config')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['enabled'] is True
        assert data['allowed_levels'] == ["CRITICAL"]
    
    @patch('src.web.routes.get_notification_config')
    def test_get_config_returns_default_when_none(self, mock_get_config, client):
        """测试配置不存在时返回默认值"""
        mock_get_config.return_value = None
        
        response = client.get('/api/notification-config')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['enabled'] is False
        assert data['allowed_levels'] == []
    
    @patch('src.web.routes.update_notification_config')
    @patch('src.web.routes.broadcast_config_update')
    def test_update_config_success(self, mock_broadcast, mock_update, client):
        """测试成功更新配置"""
        mock_config = NotificationConfig(id=1, enabled=True, allowed_levels=["CRITICAL", "WARNING"])
        mock_update.return_value = mock_config
        
        response = client.put('/api/notification-config',
                            data=json.dumps({'enabled': True, 'allowed_levels': ['CRITICAL', 'WARNING']}),
                            content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['config']['enabled'] is True
        mock_broadcast.assert_called_once()
    
    def test_update_config_invalid_levels_type(self, client):
        """测试 allowed_levels 类型无效"""
        response = client.put('/api/notification-config',
                            data=json.dumps({'enabled': True, 'allowed_levels': 'INVALID'}),
                            content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_update_config_invalid_level_value(self, client):
        """测试告警级别值无效"""
        response = client.put('/api/notification-config',
                            data=json.dumps({'enabled': True, 'allowed_levels': ['INVALID_LEVEL']}),
                            content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid alarm level' in data['error']
    
    def test_update_config_missing_body(self, client):
        """测试缺少请求体"""
        response = client.put('/api/notification-config')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
```

- [ ] **步骤 5：运行测试验证失败**

```bash
pytest tests/unit/test_api_notification_config.py -v
```

预期：FAIL，报导入错误或路由不存在

- [ ] **步骤 6：运行测试验证通过**

```bash
pytest tests/unit/test_api_notification_config.py -v
```

预期：PASS，所有 7 个测试通过

- [ ] **步骤 7：Commit**

```bash
git add src/web/routes.py tests/unit/test_api_notification_config.py
git commit -m "feat: add notification config management API endpoints"
```

---

## 任务 5：添加 WebSocket 广播功能

**文件：**
- 修改：`src/web/socketio.py`
- 测试：`tests/unit/test_socketio_notification_config.py`

- [ ] **步骤 1：读取现有 socketio 文件**

```bash
cat src/web/socketio.py
```

了解现有结构和导入

- [ ] **步骤 2：在 socketio.py 中添加广播函数**

在 `src/web/socketio.py` 中添加新函数：

```python
def broadcast_config_update(config):
    """广播通知配置更新事件
    
    当通知配置被更新时，向所有连接的 WebSocket 客户端广播更新
    
    Args:
        config: 配置字典，包含 'enabled' 和 'allowed_levels'
    """
    socketio.emit('notification_config_updated', config, namespace='/')
    logger.info(f"通知配置更新已广播: enabled={config['enabled']}, levels={config['allowed_levels']}")
```

- [ ] **步骤 3：编写 WebSocket 测试**

创建文件 `tests/unit/test_socketio_notification_config.py`：

```python
"""测试 WebSocket 配置广播功能"""
import pytest
from unittest.mock import patch, MagicMock


class TestWebSocketConfigBroadcast:
    """测试配置更新广播"""
    
    @patch('src.web.socketio.socketio')
    @patch('src.web.socketio.logger')
    def test_broadcast_config_update(self, mock_logger, mock_socketio):
        """测试成功广播配置更新"""
        from src.web.socketio import broadcast_config_update
        
        config = {'enabled': True, 'allowed_levels': ['CRITICAL']}
        
        broadcast_config_update(config)
        
        mock_socketio.emit.assert_called_once_with(
            'notification_config_updated',
            config,
            namespace='/'
        )
        mock_logger.info.assert_called_once()
    
    @patch('src.web.socketio.socketio')
    @patch('src.web.socketio.logger')
    def test_broadcast_config_update_with_disabled_config(self, mock_logger, mock_socketio):
        """测试广播禁用状态的配置"""
        from src.web.socketio import broadcast_config_update
        
        config = {'enabled': False, 'allowed_levels': []}
        
        broadcast_config_update(config)
        
        mock_socketio.emit.assert_called_once_with(
            'notification_config_updated',
            config,
            namespace='/'
        )
```

- [ ] **步骤 4：运行测试验证失败**

```bash
pytest tests/unit/test_socketio_notification_config.py -v
```

预期：FAIL，报函数不存在

- [ ] **步骤 5：运行测试验证通过**

```bash
pytest tests/unit/test_socketio_notification_config.py -v
```

预期：PASS，所有 2 个测试通过

- [ ] **步骤 6：Commit**

```bash
git add src/web/socketio.py tests/unit/test_socketio_notification_config.py
git commit -m "feat: add WebSocket broadcast for notification config updates"
```

---

## 任务 6：集成到核心告警处理流程

**文件：**
- 修改：`src/main.py`
- 测试：`tests/integration/test_notification_flow.py`

- [ ] **步骤 1：在 main.py 中添加配置检查方法**

在 `AlertService` 类中添加配置检查方法（在 `_on_alarm` 方法之前）：

```python
def _should_send_notification(self, event) -> bool:
    """检查配置是否允许发送此告警
    
    Args:
        event: 告警事件对象
        
    Returns:
        True 如果允许发送，False 如果不允许发送
    """
    try:
        from src.db.notification_config_db import get_notification_config
        from src.models.notification_config import NotificationConfig
        
        config = get_notification_config()
        
        # 如果配置不存在或总开关关闭，不发送
        if not config or not config.enabled:
            return False
        
        # 检查告警级别是否在允许列表中
        # 如果 allowed_levels 为空，则所有级别都被过滤
        if config.allowed_levels and event.level.value not in config.allowed_levels:
            return False
        
        return True
    except Exception as e:
        logger.error(f"检查通知配置失败: {e}")
        # 安全失败：配置有问题时不发送通知
        return False
```

- [ ] **步骤 2：修改 _on_alarm 方法中的飞书通知部分**

找到 `main.py` 中 `_on_alarm` 方法的第 7 步（约第 143 行），替换为：

```python
# 7. 推送飞书（添加配置检查）
if self._should_send_notification(event):
    success = self.notifier.send_alarm(event, analysis)
    if success:
        logger.info(f"告警推送成功: {event.alarm_text}")
    else:
        logger.error(f"告警推送失败: {event.alarm_text}")
else:
    logger.debug(f"告警被配置过滤: {event.alarm_text}")
```

- [ ] **步骤 3：编写集成测试**

创建文件 `tests/integration/test_notification_flow.py`：

```python
"""测试通知流程集成"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.data_models import AlarmEvent, AlarmLevel, AlarmSource


class TestNotificationFlow:
    """测试通知发送流程"""
    
    @patch('src.main.get_notification_config')
    @patch('src.main.AlertService.notifier')
    def test_notification_disabled_no_send(self, mock_notifier, mock_get_config):
        """测试通知禁用时不发送"""
        from src.main import AlertService
        from src.models.notification_config import NotificationConfig
        
        # 配置：禁用通知
        mock_config = NotificationConfig(id=1, enabled=False, allowed_levels=[])
        mock_get_config.return_value = mock_config
        
        service = AlertService()
        event = AlarmEvent(
            timestamp=datetime.now(),
            alarm_text='测试告警',
            module_name='测试设备',
            level=AlarmLevel.CRITICAL,
            source=AlarmSource.DEFAULT_LOG,
            line_number=100,
            log_file='test.log',
            raw_line='test line'
        )
        
        # 调用配置检查
        result = service._should_send_notification(event)
        
        assert result is False
    
    @patch('src.main.get_notification_config')
    def test_notification_level_filtering(self, mock_get_config):
        """测试按级别过滤通知"""
        from src.main import AlertService
        from src.models.notification_config import NotificationConfig
        
        # 配置：只允许 CRITICAL 级别
        mock_config = NotificationConfig(id=1, enabled=True, allowed_levels=['CRITICAL'])
        mock_get_config.return_value = mock_config
        
        service = AlertService()
        
        # 测试 CRITICAL 级别 - 应该发送
        critical_event = AlarmEvent(
            timestamp=datetime.now(),
            alarm_text='严重告警',
            module_name='测试设备',
            level=AlarmLevel.CRITICAL,
            source=AlarmSource.DEFAULT_LOG,
            line_number=100,
            log_file='test.log',
            raw_line='test line'
        )
        assert service._should_send_notification(critical_event) is True
        
        # 测试 WARNING 级别 - 不应该发送
        warning_event = AlarmEvent(
            timestamp=datetime.now(),
            alarm_text='警告告警',
            module_name='测试设备',
            level=AlarmLevel.WARNING,
            source=AlarmSource.DEFAULT_LOG,
            line_number=100,
            log_file='test.log',
            raw_line='test line'
        )
        assert service._should_send_notification(warning_event) is False
    
    @patch('src.main.get_notification_config')
    def test_notification_enabled_with_allowed_levels(self, mock_get_config):
        """测试启用通知且有允许级别"""
        from src.main import AlertService
        from src.models.notification_config import NotificationConfig
        
        # 配置：启用通知，允许 CRITICAL 和 WARNING
        mock_config = NotificationConfig(id=1, enabled=True, allowed_levels=['CRITICAL', 'WARNING'])
        mock_get_config.return_value = mock_config
        
        service = AlertService()
        event = AlarmEvent(
            timestamp=datetime.now(),
            alarm_text='测试告警',
            module_name='测试设备',
            level=AlarmLevel.CRITICAL,
            source=AlarmSource.DEFAULT_LOG,
            line_number=100,
            log_file='test.log',
            raw_line='test line'
        )
        
        result = service._should_send_notification(event)
        
        assert result is True
    
    @patch('src.main.get_notification_config')
    def test_notification_config_none(self, mock_get_config):
        """测试配置不存在时返回 False"""
        from src.main import AlertService
        
        mock_get_config.return_value = None
        
        service = AlertService()
        event = AlarmEvent(
            timestamp=datetime.now(),
            alarm_text='测试告警',
            module_name='测试设备',
            level=AlarmLevel.CRITICAL,
            source=AlarmSource.DEFAULT_LOG,
            line_number=100,
            log_file='test.log',
            raw_line='test line'
        )
        
        result = service._should_send_notification(event)
        
        assert result is False
    
    @patch('src.main.get_notification_config')
    def test_notification_empty_allowed_levels(self, mock_get_config):
        """测试 allowed_levels 为空时过滤所有通知"""
        from src.main import AlertService
        from src.models.notification_config import NotificationConfig
        
        # 配置：启用但 allowed_levels 为空
        mock_config = NotificationConfig(id=1, enabled=True, allowed_levels=[])
        mock_get_config.return_value = mock_config
        
        service = AlertService()
        event = AlarmEvent(
            timestamp=datetime.now(),
            alarm_text='测试告警',
            module_name='测试设备',
            level=AlarmLevel.CRITICAL,
            source=AlarmSource.DEFAULT_LOG,
            line_number=100,
            log_file='test.log',
            raw_line='test line'
        )
        
        result = service._should_send_notification(event)
        
        # 空数组意味着所有级别都被过滤
        assert result is False
```

- [ ] **步骤 4：运行测试验证失败**

```bash
pytest tests/integration/test_notification_flow.py -v
```

预期：FAIL，报方法不存在

- [ ] **步骤 5：运行测试验证通过**

```bash
pytest tests/integration/test_notification_flow.py -v
```

预期：PASS，所有 5 个测试通过

- [ ] **步骤 6：Commit**

```bash
git add src/main.py tests/integration/test_notification_flow.py
git commit -m "feat: integrate notification config check into alarm handling flow"
```

---

## 任务 7：添加启动时初始化默认配置

**文件：**
- 修改：`src/main.py`
- 测试：无

- [ ] **步骤 1：在 AlertService.__init__ 中添加初始化调用**

找到 `src/main.py` 中的 `AlertService.__init__` 方法，在 `_init_components()` 调用后添加：

```python
# 初始化通知配置（如果不存在）
self._init_notification_config()
```

- [ ] **步骤 2：添加初始化方法**

在 `AlertService` 类中添加方法：

```python
def _init_notification_config(self):
    """初始化通知配置（确保默认配置存在）"""
    try:
        from src.db.notification_config_db import init_default_config
        created = init_default_config()
        if created:
            logger.info("已创建默认通知配置：禁用状态")
    except Exception as e:
        logger.warning(f"初始化通知配置失败（不影响服务启动）: {e}")
```

- [ ] **步骤 3：验证服务启动**

```bash
python main.py --web > /tmp/service_startup.log 2>&1 &
SERVICE_PID=$!
sleep 5
cat /tmp/service_startup.log | grep "通知配置"
kill $SERVICE_PID 2>/dev/null || true
```

预期输出包含：
```
INFO - 已创建默认通知配置：禁用状态
```

或如果已存在：
```
WARNING - 初始化通知配置失败（不影响服务启动）
```

- [ ] **步骤 4：Commit**

```bash
git add src/main.py
git commit -m "feat: add automatic notification config initialization on startup"
```

---

## 任务 8：运行完整测试套件验证

**文件：**
- 测试：所有测试文件

- [ ] **步骤 1：运行所有单元测试**

```bash
pytest tests/unit/ -v
```

预期：所有测试通过（包括新增的 4 个测试文件）

- [ ] **步骤 2：运行所有集成测试**

```bash
pytest tests/integration/ -v
```

预期：所有测试通过（包括新增的 notification_flow 测试）

- [ ] **步骤 3：运行所有测试**

```bash
pytest tests/ -v --tb=short
```

预期：至少 85+ 个测试全部通过

- [ ] **步骤 4：检查测试覆盖率**

```bash
pytest tests/ --cov=src --cov-report=term-missing
```

预期：新增代码覆盖率 > 90%

- [ ] **步骤 5：Commit 无需（测试验证步骤）**

---

## 任务 9：手动端到端测试

**文件：**
- 测试：手动验证

- [ ] **步骤 1：启动服务**

```bash
python main.py --web
```

服务启动在后台，输出日志到 `service.log`

- [ ] **步骤 2：验证配置 API 可访问**

```bash
# 获取当前配置
curl http://localhost:5000/api/notification-config
```

预期输出：
```json
{"enabled": false, "allowed_levels": []}
```

- [ ] **步骤 3：更新配置**

```bash
# 启用通知，只允许 CRITICAL 级别
curl -X PUT http://localhost:5000/api/notification-config \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "allowed_levels": ["CRITICAL"]}'
```

预期输出：
```json
{
  "success": true,
  "config": {
    "enabled": true,
    "allowed_levels": ["CRITICAL"]
  }
}
```

- [ ] **步骤 4：验证 WebSocket 广播**

通过浏览器控制台或 WebSocket 客户端监听 `notification_config_updated` 事件，应该能收到配置更新消息

- [ ] **步骤 5：测试告警过滤**

通过以下方式测试：
1. 向监控的日志文件写入一个 WARNING 级别告警
2. 验证飞书通知不被发送
3. 向日志文件写入一个 CRITICAL 级别告警
4. 验证飞书通知被发送（如果飞书配置正确）

- [ ] **步骤 6：禁用通知**

```bash
curl -X PUT http://localhost:5000/api/notification-config \
  -H "Content-Type: application/json" \
  -d '{"enabled": false, "allowed_levels": []}'
```

- [ ] **步骤 7：停止服务**

按 Ctrl+C 停止服务

- [ ] **步骤 8：Commit 无需（手动测试步骤）**

---

## 任务 10：更新文档

**文件：**
- 修改：`README.md`, `SERVICE_GUIDE.md`

- [ ] **步骤 1：更新 README.md 添加通知配置说明**

在 `README.md` 的"API文档"章节添加：

```markdown
### 通知配置管理

**获取通知配置**
```http
GET /api/notification-config
```

**更新通知配置**
```http
PUT /api/notification-config
Content-Type: application/json

{
  "enabled": true,
  "allowed_levels": ["CRITICAL", "WARNING"]
}
```

配置说明：
- `enabled`: 总开关，控制是否启用飞书通知
- `allowed_levels`: 允许发送的告警级别列表，可选值：CRITICAL, WARNING, INFO
- 默认状态：`enabled: false`, `allowed_levels: []`（完全禁用）

WebSocket 事件：`notification_config_updated` - 配置更新时实时推送
```

- [ ] **步骤 2：更新 SERVICE_GUIDE.md**

在配置章节添加通知配置的说明和使用场景

- [ ] **步骤 3：Commit**

```bash
git add README.md SERVICE_GUIDE.md
git commit -m "docs: add notification config management documentation"
```

---

## 验收标准

完成所有任务后：

✅ 数据库表 `notification_config` 已创建，默认状态为禁用
✅ Web API `/api/notification-config` 可以读取和更新配置
✅ 配置更新通过 WebSocket 实时广播
✅ 核心告警处理流程正确检查配置
✅ 所有单元测试和集成测试通过
✅ 手动端到端测试验证功能正常
✅ 文档已更新

---

## 实现检查清单

按照顺序完成所有任务，每完成一个任务打勾：

- [ ] 任务 1: 创建数据库表和初始数据
- [ ] 任务 2: 创建通知配置数据模型
- [ ] 任务 3: 创建数据库操作层
- [ ] 任务 4: 添加 Web API 路由
- [ ] 任务 5: 添加 WebSocket 广播功能
- [ ] 任务 6: 集成到核心告警处理流程
- [ ] 任务 7: 添加启动时初始化默认配置
- [ ] 任务 8: 运行完整测试套件验证
- [ ] 任务 9: 手动端到端测试
- [ ] 任务 10: 更新文档

---

**计划版本**: 1.0
**创建日期**: 2026-07-10
**设计规格**: [2026-07-10-notification-config-toggle-design.md](../specs/2026-07-10-notification-config-toggle-design.md)
