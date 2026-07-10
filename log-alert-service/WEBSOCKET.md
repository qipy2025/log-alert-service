# WebSocket实时通信使用说明

## 概述

设备监控系统支持WebSocket实时通信，可以实时推送告警事件和设备状态变更。

## 服务启动

### 方式1：启动所有服务（推荐）

同时启动日志监控服务和Web服务：

```bash
python run_all.py
```

### 方式2：分别启动

**终端1 - 启动日志监控服务：**
```bash
python main.py
```

**终端2 - 启动Web服务：**
```bash
python run_web.py
```

## WebSocket连接

### 服务地址

- WebSocket服务：`ws://localhost:5000`
- HTTP服务：`http://localhost:5000`

### 客户端连接示例

**JavaScript (前端)：**
```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:5000', {
  transports: ['websocket', 'polling']
});

socket.on('connect', () => {
  console.log('已连接');
});

socket.on('alarm', (data) => {
  console.log('收到告警:', data);
});

socket.on('device_status_changed', (data) => {
  console.log('状态变更:', data);
});
```

**Python测试：**
```bash
python test_websocket.py
```

## 事件类型

### 1. 连接事件

**客户端连接**
```javascript
socket.on('connect', () => {
  // 连接成功
});
```

**服务器响应**
```json
{
  "message": "连接成功"
}
```

### 2. 告警事件

**服务器推送**
```json
{
  "type": "alarm",
  "data": {
    "device_name": "Device-001",
    "alarm_level": "critical",
    "alarm_text": "报警：温度过高",
    "timestamp": "2026-07-10T10:30:00",
    "daily_count": 3,
    "analysis": {
      "root_cause": "传感器故障",
      "severity": "高",
      "suggestion": "检查温度传感器连接",
      "related_module": "温度监控"
    }
  }
}
```

**客户端监听**
```javascript
socket.on('alarm', (message) => {
  if (message.type === 'alarm') {
    const alarm = message.data;
    console.log(`告警设备: ${alarm.device_name}`);
    console.log(`告警级别: ${alarm.alarm_level}`);
    console.log(`告警内容: ${alarm.alarm_text}`);
    console.log(`当日次数: ${alarm.daily_count}`);
  }
});
```

### 3. 设备状态变更事件

**服务器推送**
```json
{
  "type": "device_status_changed",
  "data": {
    "device_name": "Device-001",
    "old_status": "RUNNING",
    "new_status": "PAUSED",
    "changed_by": "user",
    "timestamp": "2026-07-10T10:30:00"
  }
}
```

**客户端监听**
```javascript
socket.on('device_status_changed', (message) => {
  if (message.type === 'device_status_changed') {
    const data = message.data;
    console.log(`设备: ${data.device_name}`);
    console.log(`状态: ${data.old_status} → ${data.new_status}`);
    console.log(`操作者: ${data.changed_by}`);
  }
});
```

### 4. 心跳事件

**客户端发送**
```javascript
socket.emit('ping');
```

**服务器响应**
```json
{
  "timestamp": "2026-07-10T10:30:00"
}
```

## 前端集成

前端已经集成了WebSocket composable，在组件中使用：

```vue
<script setup>
import { useWebSocket } from '@/composables/useWebSocket';

const { connected } = useWebSocket();

// 监听自定义事件来接收告警
window.addEventListener('new-alarm', (event) => {
  const alarm = event.detail;
  console.log('收到告警:', alarm);
});
</script>
```

## 测试

### 运行WebSocket测试脚本

```bash
# 确保Web服务正在运行
python run_web.py

# 在另一个终端运行测试
python test_websocket.py
```

### 模拟告警事件

1. 启动所有服务：
```bash
python run_all.py
```

2. 在监控的日志目录中创建测试日志：
```bash
echo "2026-07-10 10:30:00 [ERROR] 报警：测试告警事件" >> /path/to/logs/Default.log
```

3. 观察WebSocket客户端是否收到告警消息

### 模拟设备状态变更

```bash
# 启动设备
curl -X POST http://localhost:5000/api/devices/Device-001/start \
  -H "Content-Type: application/json" \
  -d '{"reason": "测试启动"}'

# 暂停设备
curl -X POST http://localhost:5000/api/devices/Device-001/pause \
  -H "Content-Type: application/json" \
  -d '{"reason": "测试暂停"}'
```

## 故障排查

### 连接失败

1. 检查Web服务是否启动：
```bash
curl http://localhost:5000/health
```

2. 检查端口是否被占用：
```bash
# Windows
netstat -ano | findstr :5000

# Linux/Mac
lsof -i :5000
```

### 无法接收消息

1. 检查WebSocket连接状态
2. 查看服务器日志：`service.log`
3. 确认事件已正确触发

### 心跳超时

- 前端会自动重连
- 检查网络连接
- 查看服务器负载

## 性能优化

1. **消息压缩**：对于大量消息，启用压缩
2. **连接池管理**：限制最大连接数
3. **消息队列**：使用消息队列处理高并发

## 安全建议

1. **生产环境**：使用WSS（WebSocket Secure）
2. **认证机制**：添加身份验证
3. **访问控制**：限制来源地址
4. **消息加密**：敏感数据加密传输
