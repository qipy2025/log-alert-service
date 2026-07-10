# 飞书通知配置开关设计规格

**日期**: 2026-07-10
**状态**: 设计完成，等待实现

## 概述

为飞书通知系统添加可配置的开关功能，允许用户通过 Web 界面动态控制通知的发送行为，支持全局开关和告警级别过滤。默认状态下通知功能关闭，避免误发送。

## 需求背景

### 目的
提供灵活的通知控制策略，允许根据告警级别动态控制飞书通知的发送。

### 功能目标
- 支持全局开关控制飞书通知是否启用
- 支持按告警级别（CRITICAL/WARNING/INFO）过滤通知
- 提供 Web 界面进行配置管理
- 配置实时生效，无需重启服务
- 默认状态：禁用通知

## 架构设计

### 系统架构

```
Web UI → API Routes → Config DB Layer → MySQL Database
         ↓              ↓
      WebSocket    Config Cache
         ↓              ↓
   Real-time Update  Core Logic Check
                       ↓
                    Send Notification
```

### 数据库设计

#### notification_config 表

```sql
CREATE TABLE notification_config (
  id INT PRIMARY KEY AUTO_INCREMENT,
  enabled BOOLEAN DEFAULT FALSE,           -- 总开关，默认关闭
  allowed_levels JSON,                     -- 允许的告警级别，如 ["CRITICAL", "WARNING"]
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 初始默认数据
INSERT INTO notification_config (enabled, allowed_levels) 
VALUES (FALSE, '[]');
```

**字段说明**：
- `enabled`: 总开关，`false` 时不发送任何飞书通知
- `allowed_levels`: JSON 数组存储允许的告警级别，为空或 `null` 时表示所有级别都不发送
- 默认状态：`enabled = false`，`allowed_levels = []`，完全禁用

## 组件设计

### 1. 数据模型层

**文件**: `src/models/notification_config.py`

```python
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
        """从数据库记录创建模型"""
        levels = []
        if record.allowed_levels:
            try:
                levels = json.loads(record.allowed_levels) if isinstance(record.allowed_levels, str) else record.allowed_levels
            except:
                levels = []
        return cls(
            id=record.id,
            enabled=record.enabled,
            allowed_levels=levels
        )
```

### 2. 数据库操作层

**文件**: `src/db/notification_config_db.py`

```python
from sqlalchemy import text
from src.db.mysql import get_db_session
from src.models.notification_config import NotificationConfig

def get_notification_config() -> Optional[NotificationConfig]:
    """获取当前通知配置"""
    session = get_db_session()
    try:
        record = session.query(text("id, enabled, allowed_levels")).\
            from_statement(text("SELECT id, enabled, allowed_levels FROM notification_config LIMIT 1")).first()
        return NotificationConfig.from_db(record) if record else None
    finally:
        session.close()

def update_notification_config(enabled: bool, allowed_levels: List[str]) -> NotificationConfig:
    """更新通知配置"""
    session = get_db_session()
    try:
        session.execute(text("""
            INSERT INTO notification_config (id, enabled, allowed_levels)
            VALUES (1, :enabled, :levels)
            ON DUPLICATE KEY UPDATE enabled = :enabled, allowed_levels = :levels
        """), {"enabled": enabled, "levels": json.dumps(allowed_levels)})
        session.commit()
        return get_notification_config()
    finally:
        session.close()
```

### 3. Web API 路由层

**文件**: `src/web/routes.py`（添加新路由）

```python
from src.db.notification_config_db import get_notification_config, update_notification_config
from src.web.socketio import broadcast_config_update

@app.route('/api/notification-config', methods=['GET'])
def get_notification_config_api():
    """获取通知配置"""
    try:
        config = get_notification_config()
        if not config:
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
    """更新通知配置"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        allowed_levels = data.get('allowed_levels', [])
        
        # 验证 allowed_levels 中的值
        valid_levels = {'CRITICAL', 'WARNING', 'INFO'}
        if not isinstance(allowed_levels, list):
            return jsonify({'error': 'allowed_levels must be an array'}), 400
        
        for level in allowed_levels:
            if level not in valid_levels:
                return jsonify({'error': f'Invalid alarm level: {level}'}), 400
        
        config = update_notification_config(enabled, allowed_levels)
        
        # 广播配置更新
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

### 4. WebSocket 广播层

**文件**: `src/web/socketio.py`（添加新函数）

```python
def broadcast_config_update(config):
    """广播通知配置更新"""
    socketio.emit('notification_config_updated', config, namespace='/')
    logger.info(f"配置更新已广播: enabled={config['enabled']}")
```

### 5. 核心逻辑集成

**文件**: `src/main.py`（修改 `_on_alarm` 方法）

```python
def _should_send_notification(self, event) -> bool:
    """检查配置是否允许发送此告警"""
    try:
        from src.db.mysql import get_db_session
        from src.models.notification_config import NotificationConfig
        
        session = get_db_session()
        config = get_notification_config()
        
        if not config or not config.enabled:
            return False
            
        # 检查告警级别是否在允许列表中
        if config.allowed_levels and event.level.value not in config.allowed_levels:
            return False
            
        return True
    except Exception as e:
        logger.error(f"检查通知配置失败: {e}")
        return False  # 安全失败：配置有问题时不发送

def _on_alarm(self, event):
    """告警回调"""
    try:
        # ... 现有的逻辑（去重、上下文收集、AI分析等）...
        
        # 7. 推送飞书（添加配置检查）
        if self._should_send_notification(event):
            success = self.notifier.send_alarm(event, analysis)
            if success:
                logger.info(f"告警推送成功: {event.alarm_text}")
            else:
                logger.error(f"告警推送失败: {event.alarm_text}")
        else:
            logger.debug(f"告警被配置过滤: {event.alarm_text}")
            
    except Exception as e:
        logger.exception(f"处理告警时出错: {e}")
```

## API 接口规格

### 获取通知配置

**请求**
```
GET /api/notification-config
```

**响应**
```json
{
  "enabled": false,
  "allowed_levels": ["CRITICAL", "WARNING"]
}
```

### 更新通知配置

**请求**
```
PUT /api/notification-config
Content-Type: application/json

{
  "enabled": true,
  "allowed_levels": ["CRITICAL", "WARNING"]
}
```

**响应**
```json
{
  "success": true,
  "config": {
    "enabled": true,
    "allowed_levels": ["CRITICAL", "WARNING"]
  }
}
```

**错误响应**
```json
{
  "error": "Invalid alarm level: INVALID_LEVEL"
}
```

### WebSocket 事件

**事件名**: `notification_config_updated`

**数据**:
```json
{
  "enabled": true,
  "allowed_levels": ["CRITICAL", "WARNING"]
}
```

## 数据流设计

### 配置读取流程

```
告警事件 → _should_send_notification() 
         → get_notification_config() 
         → 检查 enabled 和 allowed_levels
         → 返回 True/False
         → 决定是否发送飞书通知
```

### 配置更新流程

```
Web UI → PUT /api/notification-config
       → 验证输入
       → update_notification_config()
       → 数据库更新
       → broadcast_config_update()
       → 所有 WebSocket 客户端收到更新
       → 新配置立即生效
```

## 错误处理策略

### 1. 数据库连接失败
- **行为**: 安全失败，返回 `False`，不发送通知
- **日志**: 记录错误但不抛出异常
- **理由**: 数据库问题不应影响告警检测和存储

### 2. 配置表不存在
- **行为**: 在服务启动时自动创建表和默认数据
- **降级**: 如果创建失败，默认不发送通知

### 3. 配置数据损坏
- **行为**: `allowed_levels` 解析失败时，视为空数组
- **验证**: Web API 更新时验证 JSON 格式和级别值

### 4. 并发更新
- **行为**: 使用数据库事务和 UPSERT，最后更新生效
- **无需锁**: 配置更新不频繁，乐观锁即可

## 边界情况处理

### 情况 1: 配置为空数组
```
enabled = true, allowed_levels = []
行为: 所有级别都被过滤，不发送任何通知
```

### 情况 2: 只开启总开关，allowed_levels 为 null
```
enabled = true, allowed_levels = null
行为: 发送所有级别的通知（不过滤）
```

### 情况 3: 告警级别未在允许列表中
```
enabled = true, allowed_levels = ["CRITICAL"]
当前告警: WARNING
行为: 不发送，被过滤
```

### 情况 4: 配置完全禁用
```
enabled = false
行为: 无论告警级别如何，都不发送通知
```

## 测试策略

### 单元测试

**文件**: `tests/unit/test_notification_config.py`

- `test_create_notification_config`: 测试配置表创建和默认值
- `test_update_notification_config`: 测试配置更新功能
- `test_invalid_allowed_levels`: 测试无效告警级别验证

### 集成测试

**文件**: `tests/integration/test_notification_flow.py`

- `test_notification_disabled`: 测试通知禁用时不发送
- `test_notification_level_filtering`: 测试级别过滤功能
- `test_notification_enabled`: 测试配置启用时正常发送
- `test_config_cache_invalidation`: 测试配置缓存失效

### 端到端测试

- 通过 Web 界面修改配置
- 触发告警并验证通知行为符合预期

## 性能考虑

### 配置缓存（可选优化）
- 首次加载后缓存配置 30 秒
- 避免每次通知都查询数据库
- 配置更新时清除缓存

### 数据库连接
- 使用连接池避免频繁建立连接
- 查询和更新操作非常轻量

## 安全考虑

### 输入验证
- `allowed_levels` 必须是数组
- 只接受有效的告警级别值（CRITICAL/WARNING/INFO）

### 权限控制（未来扩展）
- 目前暂不需要认证（与现有 API 保持一致）
- 可考虑添加简单的 API 密钥验证

## 部署注意事项

### 数据库迁移
- 首次部署时需要创建 `notification_config` 表
- 插入默认配置数据

### 向后兼容
- 现有的告警检测、存储、WebSocket 推送功能不受影响
- 只是飞书通知发送增加了配置检查

### 降级方案
- 如果配置读取失败，系统继续运行，只是不发送飞书通知
- 不影响核心的告警检测和存储功能

## 实现检查清单

- [ ] 创建数据库迁移脚本
- [ ] 实现数据模型 `NotificationConfig`
- [ ] 实现数据库操作层
- [ ] 添加 Web API 路由
- [ ] 实现 WebSocket 广播
- [ ] 修改核心告警处理逻辑
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] 验证端到端功能
- [ ] 更新 API 文档

## 未来扩展方向

### 短期扩展
- 添加配置历史记录（谁在何时修改了配置）
- 支持配置导出/导入

### 长期扩展
- 设备级配置覆盖
- 时间段控制（工作时间/非工作时间）
- 通知频率限制
- 多渠道独立配置（飞书、邮件、短信分别控制）

---

**设计版本**: 1.0
**最后更新**: 2026-07-10
**设计师**: Claude (Brainstorming Skill)
