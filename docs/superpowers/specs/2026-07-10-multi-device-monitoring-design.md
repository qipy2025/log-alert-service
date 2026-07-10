# 多设备监控系统重构设计文档

**日期**: 2026-07-10  
**项目**: 设备日志AI告警推送系统  
**目标**: 重构监控系统，支持同时监控多个设备，配置完全迁移到数据库

## 1. 概述

### 1.1 问题分析

**当前系统限制：**
- 监控系统只创建 **1 个 LogWatcher** 实例
- 只监控 **1 个日志目录**（`log_source.path`）
- `config.yaml` 中的 `devices` 配置未被用于启动监控
- 数据库 `device_config` 表与监控系统完全分离

**证据：**
```python
# main.py 第 289-295 行
self.watcher = LogWatcher(
    log_dir=target_dir,  # ← 单一路径
    on_alarm=self._on_alarm,
    ...
)
# 只创建一个 LogWatcher！
```

**用户需求：**
- ✅ 同时监控多个设备的日志目录
- ✅ 完全迁移到数据库（不用 config.yaml）
- ✅ Web 界面添加的设备立即生效，无需重启服务

### 1.2 解决方案概述

**方案：集中式多设备监控**

创建 `MultiDeviceWatcher` 管理器，为每个启用的设备创建独立的 LogWatcher 实例，实现真正的并行监控。

**核心架构：**
```
┌─────────────────────────────────────────────────┐
│         AlertService (主服务)                     │
│  - 从数据库读取启用的设备列表                   │
│  - 创建 MultiDeviceWatcher 管理器               │
└─────────────────────────────────────────────────┘
                      │
           ┌─────────┴───────────────────────┐
           ▼                              ▼
      ┌─────────────────┐         ┌──────────────────┐
      │ LogWatcher #1   │         │ LogWatcher #2   │
      │ 点胶设备        │         │ 打螺丝设备      │
      │ 监控:           │         │ 监控:           │
      │ - Default.log    │         │ - Default.log    │
      │ - 告警检测       │         │ - 告警检测       │
      └─────────────────┘         └───────────┴──────┘
              │                           │
         告警事件 ←───────────┘
```

## 2. 架构设计

### 2.1 核心组件

#### 组件 1：MultiDeviceWatcher（新增）

**职责：**
- 从数据库读取启用的设备列表
- 为每个设备创建独立的 LogWatcher 实例
- 管理所有 LogWatcher 的生命周期（启动/停止）
- 分发告警事件到主服务

**接口设计：**
```python
class MultiDeviceWatcher:
    def __init__(self, on_alarm: Callable):
        """初始化多设备监控器"""
    
    def load_devices_from_db(self) -> List[Dict]:
        """从数据库加载启用的设备配置"""
        
    def start_device(self, device_config: Dict):
        """为单个设备启动监控"""
        
    def stop_device(self, device_name: str):
        """停止单个设备的监控"""
        
    def start_all(self, devices: List[Dict]):
        """启动所有设备的监控"""
        
    def stop_all(self):
        """停止所有监控"""
        
    def get_active_devices(self) -> List[str]:
        """获取当前正在监控的设备名称列表"""
        
    def get_device_status(self, device_name: str) -> Dict:
        """获取单个设备的监控状态"""
```

#### 组件 2：DeviceMonitorInfo（新增）

**职责：**
- 存储单个设备的监控信息
- 管理 LogWatcher 实例和线程

**数据结构：**
```python
class DeviceMonitorInfo:
    device_config: Dict           # 设备配置
    watcher: LogWatcher            # LogWatcher 实例
    thread: Thread                # 监控线程
    is_running: bool              # 是否正在运行
    last_heartbeat: datetime      # 最后心跳时间
    alarm_count: int              # 告警计数
```

### 2.2 数据流程

#### 启动流程

```
1. AlertService.start() 被调用
   ↓
2. MultiDeviceWatcher.load_devices_from_db()
   ├─ SELECT * FROM device_config WHERE enabled = 1
   ↓
3. MultiDeviceWatcher.start_all(devices)
   ├─ 为每个设备创建 DeviceMonitorInfo
   ├─ 为每个设备创建独立的 LogWatcher
   ├─ 启动监控线程
   └─ 更新缓存状态为 RUNNING
```

#### 告警流程

```
1. 某设备的 LogWatcher 检测到告警
   ↓
2. LogWatcher 调用 on_alarm 回调
   ↓
3. MultiDeviceWatcher 分发到 AlertService._on_alarm
   ↓
4. 告警去重、AI 分析、飞书推送
```

#### 设备管理流程

```
用户在 Web 界面点击"启用":
  ↓
Web API 调用 POST /api/devices/{device_name}/start
  ↓
routes.py 更新数据库 enabled=true
  ↓
MultiDeviceWatcher 检测到变更（轮询或事件机制）
  ↓
MultiDeviceWatcher.start_device()
  ↓
设备开始监控
```

## 3. 数据库集成

### 3.1 设备配置表

**当前表结构（保持不变）：**
```sql
CREATE TABLE device_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_name VARCHAR(100) UNIQUE NOT NULL,
    log_path VARCHAR(500) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    auto_notify BOOLEAN DEFAULT FALSE,
    polling_interval INT DEFAULT 2,
    encoding VARCHAR(20) DEFAULT 'utf-8-sig',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT 'system',
    INDEX idx_device_name (device_name),
    INDEX idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
```

**字段说明：**
- `log_path`: 设备的基础日志路径（例如：`打螺丝设备\上位机日志\`）
- 系统会自动添加日期子目录：`{log_path}\YYYY-MM-DD\Default.log`
- `polling_interval`: 轮询间隔（秒）
- `encoding`: 日志文件编码

### 3.2 日期子目录处理

**当前系统的日期处理：**
- config.yaml 的 `log_source.path` 包含完整路径
- 系统根据日期自动选择子目录

**多设备时的处理：**
- 每个设备有独立的 `log_path`
- 系统为每个设备独立添加当前日期子目录
- 例如：
  - 设备1：`点胶设备\上位机日志\` → `点胶设备\上位机日志\2026-07-10\Default.log`
  - 设备2：`打螺丝设备\上位机日志\` → `打螺丝设备\上位机日志\2026-07-10\Default.log`

**日期变更处理：**
- 凌晨 00:00，自动切换到新日期的日志文件
- 先完成旧文件的最终扫描，再切换新文件
- 确保不丢失跨天告警

### 3.3 设备启用/禁用逻辑

**启动设备：**
1. 用户在 Web 界面点击"启用"
2. API 更新数据库：`UPDATE device_config SET enabled=1`
3. MultiDeviceWatcher 检测到变更（轮询或事件机制）
4. 调用 `start_device(device_config)`
5. 设备开始监控

**停止设备：**
1. 用户在 Web 界面点击"暂停"
2. API 更新数据库：`UPDATE device_config SET enabled=0`
3. MultiDeviceWatcher 检测到变更
4. 调用 `stop_device(device_name)`
5. 设备停止监控，释放资源

## 4. 设备管理

### 4.1 设备发现机制

**启动时：**
- MultiDeviceWatcher 从数据库查询：`SELECT * FROM device_config WHERE enabled = 1`
- 为每个启用的设备启动监控

**运行时：**
- **轮询检测**（推荐）：每 30 秒检查一次数据库
- **事件通知**（未来）：数据库触发器通知变更

### 4.2 动态设备管理

**添加新设备：**
- 无需重启服务
- 轮询检测到新设备后自动启动监控
- Web 界面添加设备后 30 秒内生效

**编辑设备配置：**
- 修改日志路径：需要停止旧监控，启动新监控
- 修改轮询间隔/编码：下次重启监控时生效
- 修改设备名称：需要停止旧设备，创建新设备

**删除设备：**
- 确认设备未在运行中（或自动停止）
- 删除数据库记录
- MultiDeviceWatcher 清理资源

## 5. 生命周期管理

### 5.1 优雅启动

**启动顺序：**
1. 加载配置
2. 初始化组件（AI 分析器、飞书通知器等）
3. **创建 MultiDeviceWatcher**
4. **从数据库加载设备列表**
5. **启动所有启用的设备**
6. 启动 Web 服务

### 5.2 优雅停止

**停止顺序：**
1. 停止接受新告警
2. **停止所有设备监控**
3. 停止 LogWatcher
4. 停止其他组件
5. 清理资源

### 5.3 错误处理

**设备启动失败：**
- 记录错误日志
- 跳过该设备，继续启动其他设备
- 更新缓存状态为 `ERROR`

**监控运行中错误：**
- 捕获异常，记录日志
- 尝试重启该设备的监控
- 失败 3 次后标记设备为 `ERROR` 状态

**文件访问错误：**
- 日志文件不存在：记录警告，等待文件创建
- 编码错误：记录错误，暂停该设备监控
- 权限错误：记录错误，标记设备为 `ERROR`

## 6. 性能考虑

### 6.1 资源限制

**文件描述符限制：**
- 每个设备的 LogWatcher 需要 1 个文件描述符
- 假设系统最多支持 10-20 个设备同时监控

**内存占用：**
- 每个 LogWatcher 约 10-20 MB 内存
- 10 个设备约 200 MB 内存占用

**CPU 占用：**
- 轮询间隔 2 秒，CPU 占用较低
- 告警处理可能增加 CPU 峰值

### 6.2 优化建议

**设备数量限制：**
- 硬编码最多 10 个设备（可配置）
- 防止资源耗尽

**负载均衡：**
- 每个设备独立轮询，避免集中 IO
- 告警处理使用线程池

## 7. 测试计划

### 7.1 单元测试

```python
# tests/unit/test_multi_device_watcher.py
def test_load_devices_from_db():
    """测试从数据库加载设备"""
    # 创建测试设备
    # 调用 load_devices_from_db()
    # 验证返回的设备列表

def test_start_single_device():
    """测试启动单个设备"""
    # 创建 DeviceMonitorInfo
    # 验证 watcher 和 thread 创建成功

def test_stop_device():
    """测试停止设备"""
    # 启动设备
    # 调用 stop_device()
    # 验证资源释放
```

### 7.2 集成测试

```python
# tests/integration/test_multi_device_monitoring.py
def test_add_device_runtime():
    """测试运行时添加设备"""
    # 启动服务（监控 1 个设备）
    # 通过 API 添加新设备
    # 验证 30 秒内新设备开始监控

def test_disable_device_runtime():
    """测试运行时禁用设备"""
    # 启动服务（监控 2 个设备）
    # 通过 API 禁用 1 个设备
    # 验证设备停止监控

def test_log_file_rotation:
    """测试日志文件按日期切换"""
    # 创建跨天的日志文件
    # 验证系统能正确切换
```

### 7.3 压力测试

```python
# tests/integration/test_multi_device_stress.py
def test_max_devices():
    """测试最大设备数量"""
    # 添加 10 个设备
    # 验证系统稳定运行

def test_alarm_dedup_multi_device():
    """测试多设备告警去重"""
    # 多个设备同时产生告警
    # 验证去重逻辑正确
```

## 8. 实施步骤

### 8.1 后端实施步骤

**阶段 1：创建新组件**
1. 创建 `src/multi_device_watcher.py` - MultiDeviceWatcher 类
2. 创建 `src/device_monitor_info.py` - DeviceMonitorInfo 类
3. 添加单元测试

**阶段 2：集成到主服务**
1. 修改 `main.py` 的 `start()` 方法
2. 替换单 LogWatcher 为 MultiDeviceWatcher
3. 测试基本功能

**阶段 3：设备管理集成**
1. 实现运行时设备检测（轮询机制）
2. 集成设备启动/停止逻辑
3. 集成测试

**阶段 4：优化和错误处理**
1. 添加配置验证
2. 添加错误处理和恢复
3. 性能测试和优化

### 8.2 前端实施步骤

**无需修改** - 前端的设备管理功能已经实现！

## 9. 风险和注意事项

### 9.1 技术风险

**文件描述符耗尽：**
- 风险：监控设备过多导致文件描述符耗尽
- 缓解：限制最大设备数量（10 个）

**内存泄漏：**
- 风险：LogWatcher 瓁程未正确清理
- 缓解：严格的资源生命周期管理

**数据库连接池：**
- 风险：多设备同时查询数据库连接池
- 缓解：使用会话复用，避免频繁创建连接

### 9.2 运维风险

**配置错误：**
- 风险：数据库中的设备配置有误
- 缓解：启动时验证，记录警告，跳过有问题的设备

**日志文件缺失：**
- 风险：设备日志路径不存在或无日志文件
- 缓解：记录警告，等待文件创建

### 9.3 扩展性考虑

**设备分组：**
- 未来可能需要支持设备分组管理
- 当前设计支持（可通过 SQL 查询扩展）

**性能监控：**
- 未来可能需要监控各设备的 CPU/内存使用
- 当前设计可通过扩展 DeviceMonitorInfo 实现

**配置版本控制：**
- 未来可能需要设备配置版本管理
- 当前数据库设计支持（updated_at 字段）

## 10. 验收标准

### 10.1 功能验收

- [ ] 可以同时监控多个设备
- [ ] Web 界面添加的设备立即生效（无需重启）
- [ ] 可以通过 Web 界面启用/禁用设备
- [ ] 每个设备的告警独立处理
- [ ] 设备配置错误不影响其他设备监控

### 10.2 性能验收

- [ ] 10 个设备同时运行正常
- [ ] 告警延迟 < 5 秒
- [ ] 内存占用 < 500 MB（10 个设备）
- [ ] CPU 占用 < 30%（空闲时）

### 10.3 可用性验收

- [ ] 启动服务时自动加载所有启用的设备
- [ ] 监控服务异常退出时能优雅停止
- [ ] 错误日志清晰明确
- [ ] 可以通过 API 动态管理设备

---

**文档版本**: 1.0  
**状态**: 待用户审查  
**创建日期**: 2026-07-10
EOF
