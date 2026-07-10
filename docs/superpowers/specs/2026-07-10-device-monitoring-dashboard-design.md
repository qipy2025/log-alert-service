# 设备监控前端页面设计文档

**日期**: 2026-07-10
**项目**: 设备日志AI告警推送系统
**目标**: 为现有监控服务添加Web前端监控页面

## 1. 概述

为现有的设备日志AI告警推送系统添加一个Web前端监控页面，使设备操作人员能够：
- 实时监控设备运行状态
- 启动和暂停特定设备的监控
- 查看实时告警和历史告警记录

**目标用户**: 设备操作人员

**核心功能**:
1. 设备状态实时展示
2. 设备监控控制（启动/暂停）
3. 告警实时展示和历史查询
4. 无需用户认证（内部使用）

## 2. 架构设计

### 2.1 整体架构

采用**集成到现有服务**的架构方案，在现有的 `log-alert-service` 中直接集成Web功能。

```
┌─────────────────────────────────────────────────┐
│         log-alert-service (单一服务)           │
│                                                 │
│  ┌───────────────┐      ┌───────────────┐     │
│  │  现有监控模块  │      │   新增Web模块  │     │
│  │  - 文件监控   │◄────►│  - Flask API  │     │
│  │  - 日志解析   │      │  - 前端静态   │     │
│  │  - 飞书推送   │      │    资源      │     │
│  └───────────────┘      └───────────────┘     │
│         │                       │             │
│         ▼                       ▼             │
│    ┌─────────┐           ┌──────────┐        │
│    │  MySQL  │           │  Redis   │        │
│    └─────────┘           └──────────┘        │
└─────────────────────────────────────────────────┘
```

**优点**:
- 部署简单，只需启动一个服务
- 代码复用率高，共享配置和模块
- 适合中小规模部署（1-10台设备）

### 2.2 技术栈

**后端**:
- Python Flask + Flask-SocketIO
- MySQL（告警存储）
- Redis（状态管理和缓存）

**前端**:
- Vue 3 + TypeScript
- Element Plus（UI组件库）
- Vite（构建工具）
- Socket.IO（实时通信）

## 3. 数据库设计

### 3.1 MySQL表结构

#### 告警记录表 (alarm_records)

```sql
CREATE TABLE alarm_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_name VARCHAR(100) NOT NULL,
    alarm_level VARCHAR(20) NOT NULL,
    alarm_content TEXT NOT NULL,
    ai_analysis TEXT,
    log_timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_name, log_timestamp),
    INDEX idx_level (alarm_level),
    INDEX idx_created (created_at)
);
```

**用途**: 存储所有告警级别的日志，包含AI分析结果

#### 设备状态变更表 (device_status_history)

```sql
CREATE TABLE device_status_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_name VARCHAR(100) NOT NULL,
    old_status VARCHAR(20) NOT NULL,
    new_status VARCHAR(20) NOT NULL,
    changed_by VARCHAR(50),
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    INDEX idx_device (device_name),
    INDEX idx_changed_at (changed_at)
);
```

**用途**: 记录设备监控状态变更历史，支持审计追溯

#### 用户操作日志表 (operation_logs)

```sql
CREATE TABLE operation_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(50),
    operation VARCHAR(50) NOT NULL,
    target_device VARCHAR(100),
    details JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_device (target_device)
);
```

**用途**: 记录用户操作，用于系统行为分析

### 3.2 Redis数据结构

#### 设备实时状态

```
Key: device:status:{device_name}
Type: Hash
Fields:
  - status: "RUNNING" | "PAUSED"
  - last_heartbeat: ISO timestamp
  - last_alarm_time: ISO timestamp
  - paused_reason: string (可选)
  - changed_by: string (用户标识)
```

#### 设备告警计数

```
Key: device:alarm:count:{device_name}
Type: String
Value: 当日告警次数
TTL: 到当天午夜过期
```

#### WebSocket连接管理

```
Key: ws:connections
Type: Set
Members: {connection_id_1, connection_id_2, ...}
```

```
Key: ws:user:{user_id}
Type: Set
Members: {connection_id_1, connection_id_2, ...}
```

## 4. API设计

### 4.1 设备管理

#### 获取所有设备状态

```
GET  /api/devices
Response:
{
  "devices": [
    {
      "name": "点胶设备",
      "status": "RUNNING",
      "last_heartbeat": "2026-07-10T10:30:00Z",
      "last_alarm_time": "2026-07-10T10:25:00Z",
      "today_alarm_count": 15,
      "enabled": true
    }
  ]
}
```

#### 启动设备监控

```
POST /api/devices/{device_name}/start
Body:
{
  "reason": "启动监控"
}
Response:
{
  "success": true,
  "message": "设备监控已启动"
}
```

#### 暂停设备监控

```
POST /api/devices/{device_name}/pause
Body:
{
  "reason": "设备维护中"
}
Response:
{
  "success": true,
  "message": "设备监控已暂停"
}
```

### 4.2 告警查询

#### 查询告警列表

```
GET /api/alarms?device=点胶设备&level=ERROR&limit=50&offset=0
Response:
{
  "total": 150,
  "alarms": [
    {
      "id": 1,
      "device_name": "点胶设备",
      "alarm_level": "ERROR",
      "alarm_content": "温度过高：当前85°C，阈值80°C",
      "ai_analysis": "可能原因：冷却系统故障。建议：检查冷却液位，清洁散热器。",
      "log_timestamp": "2026-07-10T10:25:00Z",
      "created_at": "2026-07-10T10:25:05Z"
    }
  ]
}
```

#### 告警统计汇总

```
GET /api/alarms/summary?device=点胶设备&date=2026-07-10
Response:
{
  "date": "2026-07-10",
  "device": "点胶设备",
  "total": 45,
  "by_level": {
    "WARNING": 30,
    "ERROR": 12,
    "CRITICAL": 3
  },
  "peak_hour": "10:00-11:00"
}
```

### 4.3 实时通信

#### WebSocket连接

```
WebSocket /ws/connect
客户端连接后，服务端推送：

新告警事件:
{
  "type": "alarm",
  "data": {
    "device_name": "点胶设备",
    "alarm_level": "ERROR",
    "alarm_content": "温度过高",
    "timestamp": "2026-07-10T10:30:00Z"
  }
}

设备状态变更事件:
{
  "type": "device_status_changed",
  "data": {
    "device_name": "点胶设备",
    "old_status": "RUNNING",
    "new_status": "PAUSED",
    "changed_by": "admin",
    "timestamp": "2026-07-10T10:30:00Z"
  }
}
```

## 5. 前端设计

### 5.1 页面结构

**主要页面**: 单一监控页面 (`/`)

### 5.2 设备监控主页布局

```
┌─────────────────────────────────────────────────┐
│  设备监控平台                      自动刷新: ON │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐  ┌──────────────┐           │
│  │  点胶设备    │  │  设备2      │           │
│  │  ● 运行中    │  │  ○ 已暂停   │           │
│  │  今日告警:15 │  │  今日告警:8 │           │
│  │  [暂停]      │  │  [启动]     │           │
│  └──────────────┘  └──────────────┘           │
│                                                 │
│  告警列表                                       │
│  ┌──────────────────────────────────────────┐ │
│  │ 时间       设备    级别    内容          │ │
│  ├──────────────────────────────────────────┤ │
│  │ 10:30    点胶设备  ERROR  温度过高       │ │
│  │ 10:25    点胶设备  WARN   压力异常       │ │
│  └──────────────────────────────────────────┘ │
│                                                 │
│  [查看更多告警]  [告警统计]                     │
└─────────────────────────────────────────────────┘
```

### 5.3 核心组件

#### DeviceCard.vue - 设备状态卡片
```vue
<template>
  <div class="device-card">
    <div class="status-indicator" :class="statusClass"></div>
    <h3>{{ device.name }}</h3>
    <p>状态: {{ statusText }}</p>
    <p>今日告警: {{ device.today_alarm_count }}</p>
    <el-button @click="toggleDevice" :type="buttonType">
      {{ buttonText }}
    </el-button>
  </div>
</template>
```

#### AlarmList.vue - 告警列表
```vue
<template>
  <div class="alarm-list">
    <el-table :data="alarms" stripe>
      <el-table-column prop="time" label="时间" width="180" />
      <el-table-column prop="device" label="设备" width="120" />
      <el-table-column prop="level" label="级别" width="100">
        <template #default="{row}">
          <el-tag :type="getLevelType(row.level)">
            {{ row.level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="content" label="内容" />
    </el-table>
  </div>
</template>
```

### 5.4 实时通信

#### WebSocket Hook
```typescript
// composables/useWebSocket.ts
export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)

  const connect = () => {
    ws.value = new WebSocket('ws://localhost:5000/ws/connect')
    ws.value.onmessage = (event) => {
      const message = JSON.parse(event.data)
      if (message.type === 'alarm') {
        showNotification(message.data)
      }
    }
  }

  return { connect, ws }
}
```

## 6. 服务控制逻辑

### 6.1 设备状态控制流程

**启动/暂停设备的处理逻辑**:

```
用户点击"暂停"
    ↓
前端发送 POST /api/devices/{device_name}/pause
    ↓
后端处理：
    1. 更新Redis状态: device:status:{device_name} → PAUSED
    2. 记录状态变更到MySQL: device_status_history
    3. 通知监控模块停止该设备的飞书推送
    4. 通过WebSocket推送状态变更给所有连接的客户端
    ↓
返回成功响应
    ↓
前端更新UI显示
```

### 6.2 监控模块集成

**在现有监控模块中添加状态检查**:

```python
# src/file_watcher.py（修改）
def check_device_enabled(device_name: str) -> bool:
    """检查设备是否启用监控"""
    # 从Redis获取设备状态
    status = redis_client.hget(f"device:status:{device_name}", "status")
    return status == b"RUNNING" if status else True

# src/feishu_notifier.py（修改）
def send_alarm_notification(device_name: str, alarm_data: dict):
    """发送告警通知前检查设备状态"""
    if not check_device_enabled(device_name):
        logger.info(f"设备 {device_name} 已暂停，跳过飞书推送")
        return
    # 原有的飞书推送逻辑
```

### 6.3 告警存储流程

**当检测到告警时**:

```
监控模块检测到告警
    ↓
1. AI分析告警内容
    ↓
2. 存储到MySQL: alarm_records 表
    ↓
3. 更新Redis计数: device:alarm:count:{device_name} +1
    ↓
4. 检查设备状态：
   - 如果是RUNNING → 推送飞书
   - 如果是PAUSED → 跳过推送
    ↓
5. 通过WebSocket推送到前端
    ↓
前端实时显示新告警
```

### 6.4 状态同步机制

**确保监控模块和Web模块状态一致**:

```python
# 定期同步任务（可选）
def sync_device_status():
    """定期同步设备状态到Redis"""
    for device in config.devices:
        current_status = redis_client.hget(f"device:status:{device['name']}", "status")
        if not current_status:
            # 初始化设备状态
            redis_client.hset(f"device:status:{device['name']}", mapping={
                "status": "RUNNING" if device.get("enabled", True) else "PAUSED",
                "last_heartbeat": datetime.now().isoformat()
            })
```

## 7. 实时通信和部署

### 7.1 WebSocket实时推送

**推送场景**:

1. **新告警推送**
```python
def push_new_alarm(alarm_data):
    message = {
        "type": "alarm",
        "data": {
            "device_name": alarm_data["device_name"],
            "alarm_level": alarm_data["alarm_level"],
            "alarm_content": alarm_data["alarm_content"],
            "timestamp": alarm_data["log_timestamp"]
        }
    }
    broadcast_to_all(message)
```

2. **设备状态变更推送**
```python
def push_device_status_change(device_name, old_status, new_status, changed_by):
    message = {
        "type": "device_status_changed",
        "data": {
            "device_name": device_name,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
            "timestamp": datetime.now().isoformat()
        }
    }
    broadcast_to_all(message)
```

### 7.2 项目结构

**新增文件**:

```
log-alert-service/
├── main.py              # 修改：添加Web服务启动
├── src/
│   ├── web/             # 新增：Web模块
│   │   ├── __init__.py
│   │   ├── app.py       # Flask应用
│   │   ├── routes.py    # API路由
│   │   └── websocket.py # WebSocket处理
│   ├── db/              # 新增：数据库模块
│   │   ├── __init__.py
│   │   ├── mysql.py     # MySQL连接和模型
│   │   └── redis.py     # Redis连接
│   ├── models/          # 新增：数据模型
│   │   ├── __init__.py
│   │   ├── alarm.py     # 告警模型
│   │   └── device.py    # 设备模型
│   ├── file_watcher.py  # 修改：添加状态检查
│   ├── feishu_notifier.py  # 修改：添加状态检查
│   └── ... (其他现有文件保持不变)
├── frontend/            # 新增：前端项目
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── components/
│       │   ├── DeviceCard.vue
│       │   └── AlarmList.vue
│       ├── composables/
│       │   └── useWebSocket.ts
│       └── styles/
│           └── main.css
├── requirements.txt      # 修改：添加Web依赖
└── config.yaml          # 保持不变
```

### 7.3 依赖管理

**Python依赖** (`requirements.txt`):
```
# 现有依赖
watchdog
pyyaml
python-dotenv
requests
feishu-api

# 新增Web依赖
flask[async]
flask-cors
flask-socketio
eventlet
pymysql
redis
```

**前端依赖**:
```json
{
  "dependencies": {
    "vue": "^3.3.0",
    "vue-router": "^4.2.0",
    "element-plus": "^2.3.0",
    "axios": "^1.4.0",
    "socket.io-client": "^2.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^4.3.0"
  }
}
```

### 7.4 部署方式

**单一服务部署**:

```python
# main.py 修改
from src.web.app import create_app
from src.file_watcher import start_monitoring

def main():
    # 启动Web服务（非阻塞）
    app = create_app()
    socketio = app.extensions['socketio']

    # 在后台线程启动监控
    monitoring_thread = Thread(target=start_monitoring)
    monitoring_thread.daemon = True
    monitoring_thread.start()

    # 启动Web服务
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
```

**启动方式不变**:
```bash
python main.py
```

**访问地址**: `http://localhost:5000`

### 7.5 配置管理

**环境变量** (`/.env` 新增):
```bash
# 现有配置
FEISHU_APP_ID=xxx
FEISHU_APP_SECRET=xxx
CLAUDE_API_KEY=xxx

# 新增数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=log_alert

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Web服务配置
WEB_PORT=5000
WEB_HOST=0.0.0.0
```

## 8. 测试计划

### 8.1 单元测试

- 数据库模型测试
- API接口测试
- WebSocket通信测试
- 设备状态控制逻辑测试

### 8.2 集成测试

- 端到端告警流程测试
- 设备启动/暂停流程测试
- 前后端数据同步测试

### 8.3 性能测试

- WebSocket并发连接测试
- 数据库查询性能测试
- 前端页面加载性能测试

## 9. 实施步骤

1. **数据库准备**
   - 安装MySQL和Redis
   - 创建数据库和表结构
   - 配置环境变量

2. **后端开发**
   - 实现数据库连接层
   - 实现Flask API
   - 实现WebSocket服务
   - 修改现有监控模块集成状态检查

3. **前端开发**
   - 初始化Vue项目
   - 实现设备状态卡片组件
   - 实现告警列表组件
   - 实现WebSocket通信

4. **集成测试**
   - 端到端功能测试
   - 性能测试
   - 用户体验测试

5. **部署上线**
   - 配置生产环境
   - 数据备份策略
   - 监控告警

## 10. 风险和注意事项

### 10.1 技术风险

- **数据库性能**: 大量告警数据可能影响查询性能，需要定期清理历史数据
- **WebSocket稳定性**: 需要处理连接断开重连机制
- **状态同步**: 确保Redis和MySQL数据一致性

### 10.2 运维风险

- **服务可用性**: 单一服务故障会影响监控和Web功能
- **数据备份**: 需要定期备份MySQL数据
- **安全性**: 虽然无需认证，但需要限制网络访问范围

### 10.3 扩展性考虑

- 未来可能需要添加用户认证
- 可能需要支持更多设备
- 可能需要添加更多监控维度

---

**文档版本**: 1.0
**状态**: 待审查
**下一步**: 创建实现计划
