# 设备监控服务部署指南

## 服务概述

设备监控系统包含以下服务：

1. **日志监控服务**：实时监控设备日志，检测告警，AI分析，飞书推送
2. **Web服务**：提供REST API和WebSocket实时通信
3. **数据库服务**：MySQL数据存储和内存缓存

## 启动方式

### 方式1：一体化启动（推荐）

同时启动日志监控和Web服务：

```bash
# 使用默认配置文件 config.yaml
python main.py --web

# 指定配置文件
python main.py --config my_config.yaml --web

# 或者使用专用的启动脚本
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

### 方式3：仅启动Web服务

如果只需要API和WebSocket功能：

```bash
python run_web.py
```

## 环境配置

### 1. 数据库配置

确保MySQL服务运行中，创建数据库：

```sql
CREATE DATABASE device_monitoring;
USE device_monitoring;

-- 数据表会自动创建
```

### 2. 配置文件

编辑 `config.yaml`：

```yaml
# 日志源配置
log_source:
  path: "D:/code/LOG/CD-ADS-1/Log/2025-07-10"  # 日志目录
  use_direct_path: true  # 直接使用路径，不添加日期子目录
  polling_interval: 2  # 轮询间隔（秒）
  encoding: "utf-8-sig"

# 设备配置
devices:
  - name: "CD-ADS-1"
    enabled: true

# AI分析配置
ai_analysis:
  enabled: true
  api_key: "your_api_key"
  api_base_url: "http://model-api.desaysv.com"
  model: "deepseek-v4-flash-anthropic"
  max_tokens: 2048
  temperature: 0.3

# 飞书配置
feishu:
  app_id: "your_app_id"
  app_secret: "your_app_secret"
  chats:
    - "your_chat_id"

# 去重配置
dedup:
  alarm_window: 300  # 告警去重时间窗口（秒）
  max_repeat_count: 99  # 最大重复次数

# 每日汇总
daily_report:
  enabled: true
  schedule_time: "22:00"  # 每日汇总发送时间
```

### 3. 环境变量（可选）

创建 `.env` 文件：

```env
# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=device_monitoring

# Web服务配置
WEB_HOST=0.0.0.0
WEB_PORT=5000
DEBUG=False
SECRET_KEY=your-secret-key

# AI分析配置
AI_API_KEY=your_api_key
AI_API_BASE_URL=http://model-api.desaysv.com
AI_MODEL=deepseek-v4-flash-anthropic
```

## 服务端口

- **Web服务**: `http://localhost:5000`
- **WebSocket**: `ws://localhost:5000`
- **健康检查**: `http://localhost:5000/health`

## API端点

### 设备管理

- `GET /api/devices` - 获取所有设备状态
- `POST /api/devices/{device_name}/start` - 启动设备监控
- `POST /api/devices/{device_name}/pause` - 暂停设备监控

### 告警查询

- `GET /api/alarms` - 获取告警列表
  - 参数: `device`, `level`, `limit`, `offset`
- `GET /api/alarms/summary` - 获取告警统计
  - 参数: `device`, `date`

### 通知配置管理

- `GET /api/notification-config` - 获取通知配置
- `PUT /api/notification-config` - 更新通知配置
  - 请求体:
    ```json
    {
      "enabled": true,
      "allowed_levels": ["CRITICAL", "WARNING"]
    }
    ```
  - `enabled`: 总开关，控制是否启用飞书通知
  - `allowed_levels`: 允许的告警级别列表，可选值：CRITICAL, WARNING, INFO
  - 默认状态：`enabled: false`, `allowed_levels: []`（完全禁用）

### 设备配置管理

- `GET /api/devices/config` - 获取所有设备配置
  - 返回设备配置列表（设备名称、日志路径、轮询间隔、编码、启用状态等）

- `POST /api/devices` - 添加新设备
  - 请求体:
    ```json
    {
      "device_name": "新设备",
      "log_path": "新设备\\日志\\",
      "enabled": true
    }
    ```
  - 返回: `{"success": true, "device": {...}}`

- `PUT /api/devices/{device_name}` - 更新设备配置
  - URL参数: `device_name` - 当前设备名称
  - 请求体:
    ```json
    {
      "device_name": "更新后的名称",
      "log_path": "新路径\\",
      "enabled": false
    }
    ```
  - 可修改设备名称（会自动处理删除旧设备、创建新设备）
  - 返回: `{"success": true, "device": {...}}`

- `DELETE /api/devices/{device_name}` - 删除设备
  - URL参数: `device_name` - 设备名称
  - 删除设备时历史告警记录会被保留
  - 如果设备正在运行，需要先停止监控
  - 返回: `{"success": true, "message": "设备已删除"}`


## WebSocket事件

### 客户端 → 服务器

- `ping` - 心跳测试

### 服务器 → 客户端

- `connected` - 连接确认
- `alarm` - 告警事件
- `device_status_changed` - 设备状态变更
- `pong` - 心跳响应

## 日志文件

- **服务日志**: `service.log`
- **错误日志**: 控制台输出

## 依赖安装

```bash
# 安装Python依赖
pip install -r requirements.txt

# 前端构建（如果需要）
cd frontend
npm install
npm run build
```

## 生产部署

### Windows服务部署

使用NSSM将服务注册为Windows服务：

```bash
# 下载NSSM: https://nssm.cc/download

# 安装服务
nssm install DeviceMonitoring "python.exe" "D:\code\LOG\log-alert-service\main.py" --web

# 设置工作目录
nssm set DeviceMonitoring AppDirectory "D:\code\LOG\log-alert-service"

# 启动服务
nssm start DeviceMonitoring
```

### Linux systemd服务

创建服务文件 `/etc/systemd/system/device-monitoring.service`：

```ini
[Unit]
Description=Device Monitoring Service
After=network.target mysql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/log-alert-service
ExecStart=/usr/bin/python3 main.py --web
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable device-monitoring
sudo systemctl start device-monitoring
sudo systemctl status device-monitoring
```

## 故障排查

### 1. 数据库连接失败

```bash
# 检查MySQL服务状态
# Windows
sc query MySQL

# Linux
sudo systemctl status mysql

# 测试连接
mysql -u root -p123456 -h localhost
```

### 2. Web服务启动失败

```bash
# 检查端口占用
# Windows
netstat -ano | findstr :5000

# Linux
lsof -i :5000

# 更改端口
export WEB_PORT=5001
python main.py --web
```

### 3. 告警不推送

检查配置文件中的以下设置：
- 飞书配置是否正确
- AI分析是否启用
- 日志路径是否存在

### 4. WebSocket连接失败

```bash
# 测试WebSocket连接
python test_websocket.py

# 检查防火墙设置
# 确保端口5000未被阻止
```

## 监控和维护

### 日志轮转

使用logrotate管理日志文件：

```bash
# /etc/logrotate.d/device-monitoring
/path/to/service.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

### 性能监控

- 查看服务日志：`tail -f service.log`
- 监控数据库：检查MySQL慢查询日志
- 资源使用：`top` 或 `htop`

### 备份

**数据库备份**：
```bash
mysqldump -u root -p123456 device_monitoring > backup_$(date +%Y%m%d).sql
```

**配置文件备份**：
```bash
tar -czf config_backup_$(date +%Y%m%d).tar.gz config.yaml .env
```

## 升级指南

1. 备份当前版本和配置
2. 拉取最新代码
3. 更新依赖：`pip install -r requirements.txt`
4. 重启服务

## 开发环境

### 运行测试

```bash
# 单元测试
python -m pytest tests/

# 集成测试
python -m pytest tests/integration/

# WebSocket测试
python test_websocket.py
```

### 前端开发

```bash
cd frontend
npm run dev  # 开发模式
npm run build  # 生产构建
```

## 安全建议

1. **生产环境**：
   - 使用HTTPS/WSS
   - 配置防火墙
   - 使用强密码
   - 限制API访问频率

2. **配置安全**：
   - 不要提交`.env`文件到版本控制
   - 使用密钥管理服务
   - 定期更新依赖

3. **运行权限**：
   - 使用专用用户运行服务
   - 限制文件访问权限

## 联系支持

如有问题，请查看：
- 项目文档：`README.md`
- WebSocket文档：`WEBSOCKET.md`
- API文档：访问 `/api/docs`（如果配置了Swagger）
