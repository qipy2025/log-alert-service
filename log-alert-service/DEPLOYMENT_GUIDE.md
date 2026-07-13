# 测试环境快速部署指南

本指南提供了在其他测试环境快速部署设备日志AI告警推送服务的完整步骤。

## 📋 部署前准备

### 1. 系统要求

**基础环境**:
- Python 3.8+
- MySQL 5.7+
- 网络端口 5000 (Web服务)
- 至少 2GB 内存，推荐 4GB+
- 10GB+ 可用磁盘空间

**软件依赖**:
- Git (用于代码获取)
- pip (Python包管理器)

### 2. 获取代码

```bash
# 克隆代码仓库
git clone <your-repository-url>
cd log-alert-service

# 或者直接复制项目文件夹到目标服务器
```

## 🚀 快速部署步骤

### 方式一：一键自动部署（推荐）

**Windows 环境**:
```cmd
# 运行一键部署脚本
deploy.bat

# 部署完成后启动服务
start.bat
```

**Linux/Mac 环境**:
```bash
# 添加执行权限
chmod +x deploy.sh

# 运行一键部署脚本
./deploy.sh

# 启动服务
./venv/bin/python main.py --web
```

### 方式二：手动部署

如果自动部署失败，可以按照以下步骤手动部署：

#### 步骤1: 环境检查
```bash
# 运行环境检查脚本
python deployment_check.py
```

#### 步骤2: 创建虚拟环境
```bash
# 创建Python虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

#### 步骤3: 安装依赖
```bash
# 安装Python依赖包
pip install -r requirements.txt
```

#### 步骤4: 配置文件设置
```bash
# 复制配置模板
copy config.example.yaml config.yaml     # Windows
cp config.example.yaml config.yaml       # Linux/Mac

copy .env.example .env                   # Windows
cp .env.example .env                     # Linux/Mac
```

#### 步骤5: 编辑配置文件

编辑 `config.yaml`：
```yaml
# 修改数据库配置
mysql:
  host: localhost
  port: 3306
  user: your_username
  password: "your_password"
  database: device_monitoring

# 修改日志路径
log_source:
  path: "/path/to/your/device/logs"
  use_direct_path: false  # 会自动添加日期子目录

# 配置飞书通知
feishu:
  app_id: "your_feishu_app_id"
  app_secret: "your_feishu_app_secret"
  chats:
    - chat_id: "your_chat_id"
      type: test
      name: "测试告警群"

# 配置AI分析
ai_analysis:
  enabled: true
  api_key: "${CLAUDE_API_KEY}"  # 从环境变量读取
  api_base_url: "http://your-api-url"
  model: "your_model_name"
```

编辑 `.env` 文件：
```env
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=device_monitoring

# 飞书配置
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret

# AI分析配置
CLAUDE_API_KEY=your_api_key

# Web服务配置
WEB_HOST=0.0.0.0
WEB_PORT=5000
DEBUG=False
```

#### 步骤6: 数据库准备
```sql
-- 连接到MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE device_monitoring;
USE device_monitoring;

-- 数据表会在服务首次启动时自动创建
```

#### 步骤7: 启动服务
```bash
# 一体化启动（日志监控 + Web服务）
python main.py --web

# 或使用启动脚本
# Windows:
start.bat
# Linux/Mac:
./venv/bin/python main.py --web
```

## ✅ 部署验证

### 自动验证
```bash
# 等待服务启动后，运行验证脚本
python verify_deployment.py

# 或者指定URL和等待时间
python verify_deployment.py --url http://localhost:5000 --wait 10
```

### 手动验证
```bash
# 1. 检查服务状态
curl http://localhost:5000/

# 2. 测试API端点
curl http://localhost:5000/api/devices

# 3. 检查日志文件
tail -f service.log

# 4. 访问Web界面
# 浏览器打开: http://localhost:5000
```

### 功能测试清单

- [ ] **服务访问**: 浏览器能访问 http://localhost:5000
- [ ] **设备管理**: 能查看和管理设备配置
- [ ] **告警查询**: 能查询历史告警记录
- [ ] **实时监控**: WebSocket连接正常
- [ ] **飞书通知**: 测试告警能推送到飞书（可选）
- [ ] **数据库连接**: 能正常读写数据库
- [ ] **日志监控**: 服务能监控日志文件变化

## 🔧 常见问题解决

### 1. 端口冲突
```bash
# 检查端口占用
# Windows:
netstat -ano | findstr :5000

# Linux/Mac:
lsof -i :5000

# 修改端口（编辑.env文件）
WEB_PORT=5001
```

### 2. 数据库连接失败
```bash
# 检查MySQL服务状态
# Windows:
sc query MySQL

# Linux/Mac:
sudo systemctl status mysql

# 测试连接
mysql -u your_username -p -h localhost
```

### 3. 依赖包安装失败
```bash
# 更新pip
pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 单独安装失败的包
pip install package_name
```

### 4. 权限问题
```bash
# Linux/Mac: 给予执行权限
chmod +x deploy.sh
chmod +x venv/bin/python

# 创建日志目录和权限
mkdir -p logs
chmod 755 logs
```

## 📊 部署后配置

### 1. 添加设备监控
通过Web界面或API添加设备：
```bash
# 使用API添加设备
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_name": "测试设备1",
    "log_path": "/path/to/device1/logs/",
    "enabled": true
  }'
```

### 2. 配置通知规则
```bash
# 更新通知配置
curl -X PUT http://localhost:5000/api/notification-config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "allowed_levels": ["CRITICAL", "WARNING"]
  }'
```

### 3. 设置定时任务
如果需要每日汇总报告，确保配置文件中设置了正确的发送时间：
```yaml
daily_report:
  enabled: true
  schedule_time: "22:00"
```

## 🛡️ 安全建议

### 1. 生产环境部署
- 使用HTTPS/WSS加密通信
- 配置防火墙规则
- 使用强密码和密钥
- 限制API访问频率
- 定期更新依赖包

### 2. 配置文件安全
- 不要将 `.env` 文件提交到版本控制
- 使用密钥管理服务存储敏感信息
- 设置适当的文件访问权限

### 3. 运行权限
- 使用专用用户运行服务
- 限制文件系统访问权限
- 定期审计日志文件

## 📈 性能优化

### 1. 数据库优化
- 创建适当的索引
- 定期清理历史数据
- 配置连接池参数

### 2. 日志管理
- 配置日志轮转
- 设置日志保留策略
- 监控磁盘空间使用

### 3. 资源监控
```bash
# 监控服务资源使用
# Windows:
taskmgr

# Linux/Mac:
top
htop
```

## 🆘 获取帮助

如果遇到部署问题：

1. **查看日志**: `tail -f service.log`
2. **运行诊断**: `python deployment_check.py`
3. **检查配置**: 确认 `config.yaml` 和 `.env` 配置正确
4. **查看文档**: 参考 `SERVICE_GUIDE.md` 获取详细说明
5. **检查网络**: 确保能访问外部API服务

---

**文档版本**: 1.0.0  
**最后更新**: 2026-07-13  
**适用环境**: 测试环境、开发环境