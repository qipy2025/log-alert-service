# MySQL和Redis安装指南（Windows）

## 快速安装方案

### 方案1：使用Docker（推荐，最简单）

**前提**：安装Docker Desktop for Windows

```bash
# 启动MySQL和Redis容器
docker run -d --name mysql-log-alert -e MYSQL_ROOT_PASSWORD=root123 -e MYSQL_DATABASE=log_alert -p 3306:3306 mysql:8.0

docker run -d --name redis-log-alert -p 6379:6379 redis:latest

# 验证运行
docker ps
```

**更新.env文件**：
```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root123
MYSQL_DATABASE=log_alert

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

### 方案2：使用便携版MySQL + WSL Redis

#### MySQL安装（便携版）

1. **下载MySQL 8.0便携版**
   - 访问：https://dev.mysql.com/downloads/mysql/
   - 下载：mysql-8.0.34-winx64.zip（约250MB）

2. **解压到目录**
   ```
   D:\MySQL\mysql-8.0.34-winx64\
   ```

3. **创建配置文件** `D:\MySQL\my.ini`
   ```ini
   [mysqld]
   basedir=D:/MySQL/mysql-8.0.34-winx64
   datadir=D:/MySQL/mysql-8.0.34-winx64/data
   port=3306
   character-set-server=utf8mb4
   collation-server=utf8mb4_unicode_ci
   default_authentication_plugin=mysql_native_password
   ```

4. **初始化数据库**
   ```bash
   cd D:\MySQL\mysql-8.0.34-winx64\bin
   mysqld --initialize --console
   # 记住生成的临时密码
   ```

5. **安装并启动服务**
   ```bash
   mysqld --install MySQL80
   net start MySQL80
   ```

6. **修改root密码并创建数据库**
   ```bash
   mysql -u root -p
   # 输入临时密码
   
   ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_password';
   CREATE DATABASE log_alert;
   EXIT;
   ```

#### Redis安装（WSL）

1. **启用WSL**
   ```bash
   wsl --install
   # 重启电脑
   ```

2. **在WSL中安装Redis**
   ```bash
   wsl
   sudo apt update
   sudo apt install redis-server -y
   sudo service redis-server start
   ```

3. **配置Redis允许外部连接**
   ```bash
   sudo nano /etc/redis/redis.conf
   # 修改 bind 127.0.0.1 为 bind 0.0.0.0
   # 或注释掉这行
   
   sudo service redis-server restart
   ```

### 方案3：完全手动安装

1. **MySQL**：下载MySQL Installer并安装
   - https://dev.mysql.com/downloads/installer/

2. **Redis**：下载Memurai（Redis的Windows版本）
   - https://www.memurai.com/get-memurai-developer

## 验证安装

运行验证脚本：
```bash
python verify_services.py
```

或手动测试：
```bash
# 测试MySQL
mysql -u root -p -e "SELECT VERSION();"

# 测试Redis
redis-cli ping
# 应该返回: PONG
```

## 故障排除

### MySQL无法启动
- 检查端口3306是否被占用：`netstat -an | findstr :3306`
- 查看错误日志：`D:\MySQL\mysql-8.0.34-winx64\data\*.err`

### Redis连接失败
- WSL中检查Redis状态：`sudo service redis-server status`
- Windows上检查防火墙设置

### 防火墙配置
确保允许以下端口：
- MySQL: 3306
- Redis: 6379
