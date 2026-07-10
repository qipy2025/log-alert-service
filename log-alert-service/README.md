# 设备日志AI告警推送服务

实时监控点胶设备上位机日志，检测报警后通过AI分析、飞书推送通知，并提供Web界面进行设备管理和告警查询。

## 系统架构

```
┌─────────────────┐
│  设备日志文件    │
└────────┬────────┘
         │ 实时监控
         ▼
┌─────────────────┐
│  日志监控服务    │
│  - 告警检测      │
│  - 去重处理      │
│  - AI分析       │
└────────┬────────┘
         │
         ├──────────────┐
         ▼              ▼
┌──────────────┐  ┌──────────────┐
│  MySQL数据库  │  │  飞书通知      │
│  - 告警记录   │  │  - 实时推送    │
│  - 设备状态   │  │  - 每日汇总    │
└──────────────┘  └──────────────┘
         │
         ▼
┌─────────────────┐
│  Web服务        │
│  - REST API     │
│  - WebSocket    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Web前端        │
│  - 设备管理      │
│  - 告警查询      │
│  - 实时监控      │
└─────────────────┘
```

## 主要功能

### 1. 日志监控
- 实时监控设备日志文件
- 自动检测告警信息
- 支持多种告警级别
- 智能去重处理

### 2. AI分析
- 智能分析告警原因
- 提供处理建议
- 识别相关模块
- 评估严重程度

### 3. 多渠道推送
- **飞书**：实时推送告警通知
- **WebSocket**：Web界面实时更新
- **每日汇总**：每天定时发送告警统计

### 4. Web管理界面
- 设备状态管理
- 告警查询和统计
- 实时监控仪表板
- 操作日志记录

### 5. 数据存储
- MySQL数据库持久化存储
- 内存缓存提升性能
- 设备状态历史记录
- 操作审计日志

## 快速开始

### 1. 环境要求

- Python 3.8+
- MySQL 5.7+
- Node.js 14+ (前端构建)

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装Python依赖
pip install -r requirements.txt
```

### 3. 配置数据库

```sql
CREATE DATABASE device_monitoring;
USE device_monitoring;
```

### 4. 配置文件

编辑 `config.yaml`：

```yaml
log_source:
  path: "D:/path/to/logs"
  use_direct_path: true

mysql:
  host: localhost
  port: 3306
  user: root
  password: "123456"
  database: device_monitoring

feishu:
  app_id: "your_app_id"
  app_secret: "your_app_secret"
  chats:
    - "your_chat_id"

ai_analysis:
  enabled: true
  api_key: "your_api_key"
  api_base_url: "http://model-api.example.com"
  model: "deepseek-v4-flash-anthropic"
```

### 5. 启动服务

```bash
# 一体化启动（推荐）
python main.py --web

# 或使用快速启动脚本
start.bat
```

服务启动后：
- Web界面：http://localhost:5000
- WebSocket：ws://localhost:5000
- API文档：http://localhost:5000/api

## 详细文档

- 📖 [服务部署指南](SERVICE_GUIDE.md) - 详细的部署和配置说明
- 🔌 [WebSocket使用说明](WEBSOCKET.md) - WebSocket实时通信文档
- 🧪 [测试指南](#测试) - 测试运行和覆盖率

## 项目结构

```
log-alert-service/
├── src/                    # 源代码
│   ├── alarm_dedup.py      # 告警去重和存储
│   ├── ai_analyzer.py     # AI分析
│   ├── config_manager.py  # 配置管理
│   ├── context_collector.py # 上下文收集
│   ├── daily_reporter.py  # 每日汇总
│   ├── feishu_notifier.py # 飞书通知
│   ├── file_watcher.py    # 文件监控
│   ├── log_parser.py      # 日志解析
│   ├── models/            # 数据模型
│   ├── db/                # 数据库层
│   └── web/               # Web服务
├── frontend/              # 前端项目
├── tests/                 # 测试
├── scripts/               # 脚本工具
├── config.yaml           # 配置文件
├── main.py               # 主程序
└── requirements.txt      # Python依赖
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest -v

# 只运行单元测试
pytest tests/unit/ -v

# 只运行集成测试
pytest tests/integration/ -v

# 运行端到端测试
python tests/e2e/test_e2e.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 验证安装

```bash
# 验证环境和依赖
python verify_setup.py

# 测试WebSocket连接
python test_websocket.py
```

### 测试覆盖

- ✅ 完整告警流程（3个场景）
- ✅ 边界场景测试（4个场景）
- ✅ 异常恢复测试（4个场景）
- ✅ 每日汇总测试（2个场景）
- ✅ 单元测试（34个测试）
- ✅ 端到端测试（7个场景）

## API文档

### 设备管理

**获取设备列表**
```http
GET /api/devices
```

**启动设备监控**
```http
POST /api/devices/{device_name}/start
Content-Type: application/json

{
  "reason": "手动启动"
}
```

### 告警查询

**获取告警列表**
```http
GET /api/alarms?device=Device-001&level=critical&limit=50&offset=0
```

**获取告警统计**
```http
GET /api/alarms/summary?device=Device-001&date=2026-07-10
```

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

**配置说明：**
- `enabled`: 总开关，控制是否启用飞书通知
- `allowed_levels`: 允许的告警级别列表，可选值：CRITICAL, WARNING, INFO
- 默认状态：`enabled: false`, `allowed_levels: []`（完全禁用）

**WebSocket 事件：**
- `notification_config_updated` - 配置更新时实时推送到所有连接的客户端

## 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查MySQL服务是否运行
   - 验证配置文件中的数据库设置

2. **Web服务启动失败**
   - 检查端口5000是否被占用
   - 尝试使用其他端口：`export WEB_PORT=5001`

3. **告警不推送**
   - 检查配置文件路径
   - 验证飞书配置
   - 查看服务日志 `service.log`

详细排查指南请查看 [SERVICE_GUIDE.md](SERVICE_GUIDE.md)

## 许可证

[项目许可证]

---

**文档版本**: 2.0.0
**最后更新**: 2026-07-10