# 多设备监控系统重构实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 重构监控系统，支持同时监控多个设备，配置完全迁移到数据库，实现运行时设备管理

**架构：** 创建 MultiDeviceWatcher 管理器，为每个启用的设备创建独立的 LogWatcher 实例，实现真正的并行监控。通过轮询机制实现运行时设备管理（启动/停止）。

**技术栈：** Python Flask, SQLAlchemy, MySQL, watchdog, pytest (TDD)

---

## 文件结构

### 将创建的文件：
- `log-alert-service/src/multi_device_watcher.py` - MultiDeviceWatcher 类（管理多个设备监控）
- `log-alert-service/src/device_monitor_info.py` - DeviceMonitorInfo 类（单个设备监控信息）
- `log-alert-service/tests/unit/test_multi_device_watcher.py` - MultiDeviceWatcher 单元测试
- `log-alert-service/tests/unit/test_device_monitor_info.py` - DeviceMonitorInfo 单元测试
- `log-alert-service/tests/integration/test_multi_device_monitoring.py` - 多设备监控集成测试

### 将修改的文件：
- `log-alert-service/main.py:262-296` - start() 方法，替换单 LogWatcher 为 MultiDeviceWatcher
- `log-alert-service/main.py:211-248` - 添加设备状态轮询机制

### 数据库表（已存在，无需修改）：
- `device_config` - 设备配置表，已包含所有必需字段

---

## 阶段 1：创建核心组件（含 TDD）

## 任务 1：为 DeviceMonitorInfo 编写测试

**文件：**
- 创建：`log-alert-service/tests/unit/test_device_monitor_info.py`

### 步骤 1：编写失败的测试

创建 `log-alert-service/tests/unit/test_device_monitor_info.py`：

```python
"""测试 DeviceMonitorInfo 设备监控信息类"""
import pytest
import threading
from unittest.mock import MagicMock
from datetime import datetime


def test_device_monitor_info_creation():
    """测试创建 DeviceMonitorInfo"""
    from src.device_monitor_info import DeviceMonitorInfo
    
    # 创建模拟的 LogWatcher
    mock_watcher = MagicMock()
    
    # 创建设备配置
    device_config = {
        "device_name": "测试设备",
        "log_path": "测试路径\\日志\\",
        "enabled": True,
        "auto_notify": False,
        "polling_interval": 2,
        "encoding": "utf-8-sig"
    }
    
    # 创建 DeviceMonitorInfo
    monitor_info = DeviceMonitorInfo(device_config, mock_watcher)
    
    # 验证属性
    assert monitor_info.device_config == device_config
    assert monitor_info.watcher == mock_watcher
    assert monitor_info.is_running is False
    assert monitor_info.thread is None
    assert monitor_info.last_heartbeat is None
    assert monitor_info.alarm_count == 0


def test_device_monitor_info_start():
    """测试启动设备监控"""
    from src.device_monitor_info import DeviceMonitorInfo
    
    # 创建模拟的 LogWatcher
    mock_watcher = MagicMock()
    
    device_config = {
        "device_name": "测试设备",
        "log_path": "测试路径\\日志\\",
        "enabled": True
    }
    
    monitor_info = DeviceMonitorInfo(device_config, mock_watcher)
    
    # 启动监控
    monitor_info.start()
    
    # 验证状态
    assert monitor_info.is_running is True
    assert monitor_info.thread is not None
    assert monitor_info.last_heartbeat is not None
    assert isinstance(monitor_info.thread, threading.Thread)
    
    # 验证 watcher 被启动
    mock_watcher.start.assert_called_once()


def test_device_monitor_info_stop():
    """测试停止设备监控"""
    from src.device_monitor_info import DeviceMonitorInfo
    
    # 创建模拟的 LogWatcher
    mock_watcher = MagicMock()
    
    device_config = {
        "device_name": "测试设备",
        "log_path": "测试路径\\日志\\",
        "enabled": True
    }
    
    monitor_info = DeviceMonitorInfo(device_config, mock_watcher)
    
    # 先启动
    monitor_info.start()
    assert monitor_info.is_running is True
    
    # 再停止
    monitor_info.stop()
    
    # 验证状态
    assert monitor_info.is_running is False
    assert monitor_info.thread is None
    
    # 验证 watcher 被停止
    mock_watcher.stop.assert_called_once()


def test_device_monitor_info_increment_alarm():
    """测试告警计数"""
    from src.device_monitor_info import DeviceMonitorInfo
    
    mock_watcher = MagicMock()
    device_config = {"device_name": "测试设备", "log_path": "路径\\"}
    
    monitor_info = DeviceMonitorInfo(device_config, mock_watcher)
    
    # 初始计数为 0
    assert monitor_info.alarm_count == 0
    
    # 增加告警计数
    monitor_info.increment_alarm_count()
    assert monitor_info.alarm_count == 1
    
    monitor_info.increment_alarm_count()
    assert monitor_info.alarm_count == 2
    
    # 重置计数
    monitor_info.reset_alarm_count()
    assert monitor_info.alarm_count == 0


def test_device_monitor_info_status():
    """测试获取设备状态"""
    from src.device_monitor_info import DeviceMonitorInfo
    
    mock_watcher = MagicMock()
    device_config = {
        "device_name": "测试设备",
        "log_path": "路径\\",
        "enabled": True
    }
    
    monitor_info = DeviceMonitorInfo(device_config, mock_watcher)
    
    # 未启动状态
    status = monitor_info.get_status()
    assert status["device_name"] == "测试设备"
    assert status["is_running"] is False
    assert status["alarm_count"] == 0
    assert "last_heartbeat" in status
    
    # 启动后状态
    monitor_info.start()
    monitor_info.increment_alarm_count()
    
    status = monitor_info.get_status()
    assert status["is_running"] is True
    assert status["alarm_count"] == 1
```

### 步骤 2：运行测试验证失败

```bash
cd log-alert-service
pytest tests/unit/test_device_monitor_info.py -v
```

预期输出：`FAILED`，报错 `ModuleNotFoundError: No module named 'src.device_monitor_info'`

### 步骤 3：Commit 测试文件

```bash
cd log-alert-service
git add tests/unit/test_device_monitor_info.py
git commit -m "test: add unit tests for DeviceMonitorInfo class"
```

---

## 任务 2：实现 DeviceMonitorInfo 类

**文件：**
- 创建：`log-alert-service/src/device_monitor_info.py`

### 步骤 1：实现 DeviceMonitorInfo 类

创建 `log-alert-service/src/device_monitor_info.py`：

```python
"""设备监控信息类

存储单个设备的监控信息，管理 LogWatcher 实例和线程。
"""
import threading
from datetime import datetime
from typing import Dict, Callable, Optional, Any


class DeviceMonitorInfo:
    """设备监控信息
    
    存储单个设备的监控状态、LogWatcher 实例和监控线程。
    """
    
    def __init__(self, device_config: Dict[str, Any], watcher: Any):
        """初始化设备监控信息
        
        Args:
            device_config: 设备配置字典
            watcher: LogWatcher 实例
        """
        self.device_config = device_config
        self.watcher = watcher
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_heartbeat: Optional[datetime] = None
        self.alarm_count = 0
        self._lock = threading.Lock()
    
    def start(self):
        """启动设备监控
        
        在独立线程中启动 LogWatcher，避免阻塞主线程。
        """
        with self._lock:
            if self.is_running:
                return
            
            def run_watcher():
                """运行 LogWatcher 的线程函数"""
                try:
                    self.watcher.start()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"设备 {self.device_config.get('device_name')} 监控线程异常: {e}")
            
            # 创建并启动线程
            self.thread = threading.Thread(
                target=run_watcher,
                name=f"DeviceMonitor-{self.device_config.get('device_name')}",
                daemon=True
            )
            self.thread.start()
            self.is_running = True
            self.last_heartbeat = datetime.now()
    
    def stop(self):
        """停止设备监控
        
        停止 LogWatcher 并清理资源。
        """
        with self._lock:
            if not self.is_running:
                return
            
            # 停止 watcher
            if self.watcher:
                try:
                    self.watcher.stop()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"停止设备 {self.device_config.get('device_name')} watcher 失败: {e}")
            
            # 清理状态
            self.is_running = False
            self.thread = None
    
    def increment_alarm_count(self):
        """增加告警计数"""
        with self._lock:
            self.alarm_count += 1
    
    def reset_alarm_count(self):
        """重置告警计数"""
        with self._lock:
            self.alarm_count = 0
    
    def get_status(self) -> Dict[str, Any]:
        """获取设备监控状态
        
        Returns:
            包含设备状态信息的字典
        """
        with self._lock:
            return {
                "device_name": self.device_config.get("device_name"),
                "is_running": self.is_running,
                "alarm_count": self.alarm_count,
                "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
                "log_path": self.device_config.get("log_path"),
                "enabled": self.device_config.get("enabled", True)
            }
```

### 步骤 2：运行测试验证通过

```bash
cd log-alert-service
pytest tests/unit/test_device_monitor_info.py -v
```

预期输出：全部 `PASSED`

### 步骤 3：Commit

```bash
cd log-alert-service
git add src/device_monitor_info.py
git commit -m "feat: add DeviceMonitorInfo class for managing device monitoring state"
```

---

## 任务 3：为 MultiDeviceWatcher 编写测试

**文件：**
- 创建：`log-alert-service/tests/unit/test_multi_device_watcher.py`

### 步骤 1：编写失败的测试

创建 `log-alert-service/tests/unit/test_multi_device_watcher.py`：

```python
"""测试 MultiDeviceWatcher 多设备监控器"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_db_devices():
    """模拟数据库中的设备列表"""
    return [
        {
            "device_name": "点胶设备",
            "log_path": "点胶设备\\上位机日志\\",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "打螺丝设备",
            "log_path": "打螺丝设备\\上位机日志\\",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "禁用设备",
            "log_path": "禁用设备\\日志\\",
            "enabled": False,  # 这个设备不应被启动
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        }
    ]


def test_load_devices_from_db(mock_db_devices):
    """测试从数据库加载设备"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    # Mock 数据库查询
    with patch('src.multi_device_watcher.DeviceConfig.get_all') as mock_get_all:
        mock_get_all.return_value = mock_db_devices
        
        # 创建 MultiDeviceWatcher
        watcher = MultiDeviceWatcher(on_alarm=MagicMock())
        
        # 加载设备
        devices = watcher.load_devices_from_db()
        
        # 验证：只返回启用的设备
        assert len(devices) == 2
        assert any(d["device_name"] == "点胶设备" for d in devices)
        assert any(d["device_name"] == "打螺丝设备" for d in devices)
        assert not any(d["device_name"] == "禁用设备" for d in devices)


def test_start_single_device():
    """测试启动单个设备"""
    from src.multi_device_watcher import MultiDeviceWatcher
    from pathlib import Path
    
    alarm_events = []
    
    def on_alarm(event):
        alarm_events.append(event)
    
    watcher = MultiDeviceWatcher(on_alarm=on_alarm)
    
    device_config = {
        "device_name": "测试设备",
        "log_path": "测试\\日志\\",
        "enabled": True,
        "polling_interval": 2,
        "encoding": "utf-8-sig"
    }
    
    # 启动设备
    watcher.start_device(device_config)
    
    # 验证：设备已添加到监控列表
    assert "测试设备" in watcher.device_monitors
    assert watcher.device_monitors["测试设备"].is_running is True


def test_stop_device():
    """测试停止单个设备"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=MagicMock())
    
    device_config = {
        "device_name": "测试设备",
        "log_path": "测试\\日志\\",
        "enabled": True,
        "polling_interval": 2,
        "encoding": "utf-8-sig"
    }
    
    # 先启动
    watcher.start_device(device_config)
    assert "测试设备" in watcher.device_monitors
    
    # 再停止
    watcher.stop_device("测试设备")
    
    # 验证：设备已从监控列表移除
    assert "测试设备" not in watcher.device_monitors


def test_start_all_devices(mock_db_devices):
    """测试启动所有设备"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    with patch('src.multi_device_watcher.DeviceConfig.get_all') as mock_get_all:
        mock_get_all.return_value = mock_db_devices
        
        alarm_events = []
        
        def on_alarm(event):
            alarm_events.append(event)
        
        watcher = MultiDeviceWatcher(on_alarm=on_alarm)
        
        # 启动所有设备
        devices = watcher.load_devices_from_db()
        watcher.start_all(devices)
        
        # 验证：只有启用的设备被启动
        assert len(watcher.device_monitors) == 2
        assert "点胶设备" in watcher.device_monitors
        assert "打螺丝设备" in watcher.device_monitors
        assert "禁用设备" not in watcher.device_monitors


def test_stop_all_devices():
    """测试停止所有设备"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=MagicMock())
    
    # 启动多个设备
    devices = [
        {"device_name": "设备1", "log_path": "路径1\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"},
        {"device_name": "设备2", "log_path": "路径2\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"}
    ]
    watcher.start_all(devices)
    
    assert len(watcher.device_monitors) == 2
    
    # 停止所有设备
    watcher.stop_all()
    
    # 验证：所有设备已停止
    assert len(watcher.device_monitors) == 0


def test_get_active_devices():
    """测试获取活动设备列表"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=MagicMock())
    
    # 启动多个设备
    devices = [
        {"device_name": "设备1", "log_path": "路径1\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"},
        {"device_name": "设备2", "log_path": "路径2\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"}
    ]
    watcher.start_all(devices)
    
    # 获取活动设备
    active = watcher.get_active_devices()
    
    assert len(active) == 2
    assert "设备1" in active
    assert "设备2" in active


def test_get_device_status():
    """测试获取单个设备状态"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=MagicMock())
    
    device_config = {
        "device_name": "测试设备",
        "log_path": "测试\\日志\\",
        "enabled": True,
        "polling_interval": 2,
        "encoding": "utf-8-sig"
    }
    
    watcher.start_device(device_config)
    
    # 获取设备状态
    status = watcher.get_device_status("测试设备")
    
    assert status["device_name"] == "测试设备"
    assert status["is_running"] is True
    assert "log_path" in status
```

### 步骤 2：运行测试验证失败

```bash
cd log-alert-service
pytest tests/unit/test_multi_device_watcher.py -v
```

预期输出：`FAILED`，报错 `ModuleNotFoundError: No module named 'src.multi_device_watcher'`

### 步骤 3：Commit 测试文件

```bash
cd log-alert-service
git add tests/unit/test_multi_device_watcher.py
git commit -m "test: add unit tests for MultiDeviceWatcher class"
```

---

## 任务 4：实现 MultiDeviceWatcher 类

**文件：**
- 创建：`log-alert-service/src/multi_device_watcher.py`

### 步骤 1：实现 MultiDeviceWatcher 类

创建 `log-alert-service/src/multi_device_watcher.py`：

```python
"""多设备监控器

管理多个设备的日志监控，为每个设备创建独立的 LogWatcher 实例。
"""
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional

from src.file_watcher import LogWatcher
from src.device_monitor_info import DeviceMonitorInfo
from src.data_models import AlarmEvent

logger = logging.getLogger(__name__)


class MultiDeviceWatcher:
    """多设备监控管理器
    
    从数据库读取启用的设备列表，为每个设备创建独立的 LogWatcher 实例，
    管理所有设备监控的生命周期（启动/停止）。
    """
    
    def __init__(self, on_alarm: Callable[[AlarmEvent], None]):
        """初始化多设备监控器
        
        Args:
            on_alarm: 告警回调函数
        """
        self.on_alarm = on_alarm
        self.device_monitors: Dict[str, DeviceMonitorInfo] = {}
        self._lock = threading.Lock()
    
    def load_devices_from_db(self) -> List[Dict[str, Any]]:
        """从数据库加载启用的设备配置
        
        Returns:
            启用的设备配置列表
        """
        from src.db.device_config import DeviceConfig
        
        all_devices = DeviceConfig.get_all()
        
        # 只返回启用的设备
        enabled_devices = [d for d in all_devices if d.get("enabled", False)]
        
        logger.info(f"从数据库加载了 {len(enabled_devices)} 个启用的设备（共 {len(all_devices)} 个）")
        
        return enabled_devices
    
    def start_device(self, device_config: Dict[str, Any]):
        """为单个设备启动监控
        
        Args:
            device_config: 设备配置字典
        """
        device_name = device_config.get("device_name")
        
        if not device_name:
            logger.error("设备配置缺少 device_name")
            return
        
        with self._lock:
            # 如果设备已在监控，先停止
            if device_name in self.device_monitors:
                logger.info(f"设备 {device_name} 已在监控，先停止旧监控")
                self.stop_device(device_name)
            
            try:
                # 构建日志文件路径（添加日期子目录）
                log_path = self._build_log_path(device_config.get("log_path", ""))
                
                # 创建 LogWatcher
                watcher = LogWatcher(
                    log_dir=log_path,
                    on_alarm=self._create_device_alarm_callback(device_name),
                    polling_interval=device_config.get("polling_interval", 2),
                    encoding=device_config.get("encoding", "utf-8-sig")
                )
                
                # 创建 DeviceMonitorInfo
                monitor_info = DeviceMonitorInfo(device_config, watcher)
                
                # 启动监控
                monitor_info.start()
                
                # 添加到监控列表
                self.device_monitors[device_name] = monitor_info
                
                logger.info(f"✅ 设备 {device_name} 监控已启动: {log_path}")
                
            except Exception as e:
                logger.error(f"❌ 启动设备 {device_name} 监控失败: {e}")
                raise
    
    def stop_device(self, device_name: str):
        """停止单个设备的监控
        
        Args:
            device_name: 设备名称
        """
        with self._lock:
            if device_name not in self.device_monitors:
                logger.warning(f"设备 {device_name} 未在监控中")
                return
            
            try:
                monitor_info = self.device_monitors[device_name]
                monitor_info.stop()
                
                # 从监控列表移除
                del self.device_monitors[device_name]
                
                logger.info(f"⏹️  设备 {device_name} 监控已停止")
                
            except Exception as e:
                logger.error(f"❌ 停止设备 {device_name} 监控失败: {e}")
                raise
    
    def start_all(self, devices: List[Dict[str, Any]]):
        """启动所有设备的监控
        
        Args:
            devices: 设备配置列表
        """
        logger.info(f"开始启动 {len(devices)} 个设备的监控...")
        
        for device_config in devices:
            try:
                self.start_device(device_config)
            except Exception as e:
                logger.error(f"启动设备 {device_config.get('device_name')} 失败: {e}")
                # 继续启动其他设备
        
        logger.info(f"✅ 成功启动 {len(self.device_monitors)} 个设备监控")
    
    def stop_all(self):
        """停止所有监控"""
        logger.info("停止所有设备监控...")
        
        device_names = list(self.device_monitors.keys())
        
        for device_name in device_names:
            try:
                self.stop_device(device_name)
            except Exception as e:
                logger.error(f"停止设备 {device_name} 失败: {e}")
        
        logger.info("✅ 所有设备监控已停止")
    
    def get_active_devices(self) -> List[str]:
        """获取当前正在监控的设备名称列表
        
        Returns:
            设备名称列表
        """
        with self._lock:
            return list(self.device_monitors.keys())
    
    def get_device_status(self, device_name: str) -> Optional[Dict[str, Any]]:
        """获取单个设备的监控状态
        
        Args:
            device_name: 设备名称
            
        Returns:
            设备状态字典，如果设备不存在则返回 None
        """
        with self._lock:
            if device_name not in self.device_monitors:
                return None
            
            return self.device_monitors[device_name].get_status()
    
    def _build_log_path(self, base_log_path: str) -> str:
        """构建日志文件路径（添加日期子目录）
        
        Args:
            base_log_path: 基础日志路径
            
        Returns:
            完整的日志目录路径
        """
        from datetime import datetime
        
        # 添加日期子目录
        today_str = datetime.now().strftime("%Y-%m-%d")
        full_path = str(Path(base_log_path) / today_str)
        
        return full_path
    
    def _create_device_alarm_callback(self, device_name: str) -> Callable[[AlarmEvent], None]:
        """创建设备特定的告警回调
        
        在告警事件中添加设备名称信息。
        
        Args:
            device_name: 设备名称
            
        Returns:
            告警回调函数
        """
        def callback(event: AlarmEvent):
            # 设置设备名称（如果没有）
            if not event.module_name:
                event.module_name = device_name
            
            # 调用主告警回调
            self.on_alarm(event)
            
            # 增加该设备的告警计数
            if device_name in self.device_monitors:
                self.device_monitors[device_name].increment_alarm_count()
        
        return callback
```

### 步骤 2：运行测试验证通过

```bash
cd log-alert-service
pytest tests/unit/test_multi_device_watcher.py -v
```

预期输出：全部 `PASSED`

### 步骤 3：Commit

```bash
cd log-alert-service
git add src/multi_device_watcher.py
git commit -m "feat: add MultiDeviceWatcher class for managing multiple device monitoring"
```

---

## 阶段 2：集成到主服务（含 TDD）

## 任务 5：编写主服务集成测试

**文件：**
- 创建：`log-alert-service/tests/integration/test_main_service_integration.py`

### 步骤 1：编写集成测试

创建 `log-alert-service/tests/integration/test_main_service_integration.py`：

```python
"""测试主服务集成多设备监控"""
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def test_db_devices():
    """创建测试设备配置"""
    return [
        {
            "device_name": "测试设备1",
            "log_path": "设备1\\日志\\",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 1,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "测试设备2",
            "log_path": "设备2\\日志\\",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 1,
            "encoding": "utf-8-sig"
        }
    ]


def test_alert_service_starts_multiple_devices(test_config_path, test_db_devices, temp_log_dir):
    """测试 AlertService 启动时加载多个设备"""
    from main import AlertService
    
    # 创建日志目录
    device1_log_dir = Path(temp_log_dir) / "设备1\\日志\\2026-07-10"
    device2_log_dir = Path(temp_log_dir) / "设备2\\日志\\2026-07-10"
    device1_log_dir.mkdir(parents=True, exist_ok=True)
    device2_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Mock 数据库
    with patch('src.multi_device_watcher.DeviceConfig.get_all') as mock_get_all:
        mock_get_all.return_value = test_db_devices
        
        # 创建 AlertService
        service = AlertService(config_path=test_config_path, enable_web=False)
        
        # 启动服务
        service.start()
        
        # 等待设备监控启动
        time.sleep(1)
        
        # 验证：多设备监控器已创建
        assert hasattr(service, 'multi_watcher')
        assert service.multi_watcher is not None
        
        # 验证：两个设备都在监控
        active_devices = service.multi_watcher.get_active_devices()
        assert len(active_devices) == 2
        assert "测试设备1" in active_devices
        assert "测试设备2" in active_devices
        
        # 停止服务
        service.stop()


def test_alert_service_ignores_disabled_devices(test_config_path, temp_log_dir):
    """测试 AlertService 忽略禁用的设备"""
    from main import AlertService
    
    devices = [
        {
            "device_name": "启用的设备",
            "log_path": "设备\\日志\\",
            "enabled": True,
            "auto_notify": False,
            "polling_interval": 1,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "禁用的设备",
            "log_path": "设备\\日志\\",
            "enabled": False,  # 禁用
            "auto_notify": False,
            "polling_interval": 1,
            "encoding": "utf-8-sig"
        }
    ]
    
    # 创建日志目录
    log_dir = Path(temp_log_dir) / "设备\\日志\\2026-07-10"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    with patch('src.multi_device_watcher.DeviceConfig.get_all') as mock_get_all:
        mock_get_all.return_value = devices
        
        service = AlertService(config_path=test_config_path, enable_web=False)
        service.start()
        
        time.sleep(1)
        
        # 验证：只有启用的设备在监控
        active_devices = service.multi_watcher.get_active_devices()
        assert len(active_devices) == 1
        assert "启用的设备" in active_devices
        assert "禁用的设备" not in active_devices
        
        service.stop()


def test_alert_service_stops_all_devices(test_config_path):
    """测试 AlertService 停止时停止所有设备"""
    from main import AlertService
    
    devices = [
        {"device_name": "设备1", "log_path": "路径1\\", "enabled": True, "polling_interval": 1, "encoding": "utf-8-sig"},
        {"device_name": "设备2", "log_path": "路径2\\", "enabled": True, "polling_interval": 1, "encoding": "utf-8-sig"}
    ]
    
    with patch('src.multi_device_watcher.DeviceConfig.get_all') as mock_get_all:
        mock_get_all.return_value = devices
        
        service = AlertService(config_path=test_config_path, enable_web=False)
        service.start()
        
        time.sleep(1)
        
        # 验证设备已启动
        assert len(service.multi_watcher.get_active_devices()) == 2
        
        # 停止服务
        service.stop()
        
        # 验证所有设备已停止
        assert len(service.multi_watcher.get_active_devices()) == 0
```

### 步骤 2：运行测试验证失败

```bash
cd log-alert-service
pytest tests/integration/test_main_service_integration.py -v
```

预期输出：`FAILED`，报错 `AttributeError: 'AlertService' object has no attribute 'multi_watcher'`

### 步骤 3：Commit 测试文件

```bash
cd log-alert-service
git add tests/integration/test_main_service_integration.py
git commit -m "test: add integration tests for main service with multi-device monitoring"
```

---

## 任务 6：修改 main.py 集成 MultiDeviceWatcher

**文件：**
- 修改：`log-alert-service/main.py:262-296`

### 步骤 1：修改 start() 方法集成 MultiDeviceWatcher

打开 `log-alert-service/main.py`，找到 `start()` 方法（第 262-296 行），替换为：

```python
def start(self):
    """启动服务"""
    logger.info("=" * 50)
    logger.info("设备日志 AI 告警推送服务启动中...")
    logger.info("=" * 50)

    # 初始化多设备监控器
    from src.multi_device_watcher import MultiDeviceWatcher
    
    self.multi_watcher = MultiDeviceWatcher(on_alarm=self._on_alarm)
    
    # 从数据库加载启用的设备
    try:
        devices = self.multi_watcher.load_devices_from_db()
        
        if not devices:
            logger.warning("⚠️  数据库中没有启用的设备，服务将启动但不会监控任何日志")
        
        # 启动所有设备的监控
        self.multi_watcher.start_all(devices)
        
    except Exception as e:
        logger.error(f"❌ 加载设备配置失败: {e}")
        logger.info("服务将继续启动，但不会监控任何设备")

    # 配置每日汇总定时任务
    daily_config = self.config.get("daily_report", {})
    if daily_config.get("enabled", False):
        schedule_time = daily_config.get("schedule_time", "00:00")
        self.scheduler.add_job(
            self._send_daily_report,
            'cron',
            hour=int(schedule_time.split(':')[0]),
            minute=int(schedule_time.split(':')[1]),
            id='daily_report'
        )
        logger.info(f"每日汇总定时任务已配置: {schedule_time}")

    # 启动定时调度器
    self.scheduler.start()
    logger.info("定时调度器已启动")

    # 如果启用 Web 服务，启动 Web 服务器
    if self.enable_web:
        self._start_web_service()

    # 设置信号处理
    signal.signal(signal.SIGINT, self._signal_handler)
    signal.signal(signal.SIGTERM, self._signal_handler)

    self._running = True
    logger.info("=" * 50)
    logger.info("✅ 服务启动完成")
    logger.info(f"正在监控 {len(self.multi_watcher.get_active_devices())} 个设备")
    for device_name in self.multi_watcher.get_active_devices():
        logger.info(f"  - {device_name}")
    logger.info("=" * 50)
```

### 步骤 2：修改 stop() 方法

找到 `stop()` 方法，添加停止所有设备监控的逻辑。首先读取现有的 stop() 方法：Ķ

Let me read the stop() method first: 读取 main.py 的 stop() 方法（应该在 300 行左右）：让我继续读取 stop() 方法：当用户看到这个消息时，只是解释性文字，不是实际的函数调用。所以我不需要添加工具调用。让我继续编写实现计划。

继续打开 `log-alert-service/main.py`，找到 `stop()` 方法，添加停止多设备监控的逻辑。如果 stop() 方法存在，在其中停止所有设备监控；如果不存在，创建它。

```python
def stop(self):
    """停止服务"""
    if not self._running:
        return
    
    logger.info("=" * 50)
    logger.info("服务停止中...")
    logger.info("=" * 50)
    
    # 停止所有设备监控
    if hasattr(self, 'multi_watcher') and self.multi_watcher:
        self.multi_watcher.stop_all()
    
    # 停止定时调度器
    if self.scheduler.running:
        self.scheduler.shutdown()
        logger.info("定时调度器已停止")
    
    # 停止 Web 服务
    if self.enable_web:
        self._stop_web_service()
    
    self._running = False
    logger.info("✅ 服务已停止")
    logger.info("=" * 50)
```

### 步骤 3：运行测试验证通过

```bash
cd log-alert-service
pytest tests/integration/test_main_service_integration.py -v
```

预期输出：全部 `PASSED`

### 步骤 4：Commit

```bash
cd log-alert-service
git add main.py
git commit -m "feat: integrate MultiDeviceWatcher into AlertService.start() method"
```

---

## 任务 7：验证基本多设备监控功能

### 步骤 1：运行所有单元测试

```bash
cd log-alert-service
pytest tests/unit/test_device_monitor_info.py tests/unit/test_multi_device_watcher.py -v
```

预期输出：全部 `PASSED`

### 步骤 2：运行集成测试

```bash
cd log-alert-service
pytest tests/integration/test_main_service_integration.py -v
```

预期输出：全部 `PASSED`

### 步骤 3：手动验证（可选）

创建临时测试设备配置到数据库，启动服务验证：

```bash
cd log-alert-service
python main.py --web
```

在 Web 界面的设备管理页面添加设备，观察日志输出确认设备被启动。

### 步骤 4：Commit（如有修复）

如果测试过程中发现需要修复的问题：

```bash
cd log-alert-service
git add .
git commit -m "fix: address issues found during basic multi-device monitoring testing"
```

---

## 阶段 3：实现运行时设备管理（含 TDD）

## 任务 8：编写运行时设备检测测试

**文件：**
- 创建：`log-alert-service/tests/integration/test_runtime_device_management.py`

### 步骤 1：编写测试

创建 `log-alert-service/tests/integration/test_runtime_device_management.py`：

```python
"""测试运行时设备管理"""
import pytest
import time
from unittest.mock import patch


def test_add_device_at_runtime():
    """测试运行时添加设备"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    alarm_events = []
    
    def on_alarm(event):
        alarm_events.append(event)
    
    watcher = MultiDeviceWatcher(on_alarm=on_alarm)
    
    # 初始状态：无设备
    assert len(watcher.get_active_devices()) == 0
    
    # 运行时添加设备
    new_device = {
        "device_name": "新设备",
        "log_path": "新设备\\日志\\",
        "enabled": True,
        "polling_interval": 2,
        "encoding": "utf-8-sig"
    }
    
    watcher.start_device(new_device)
    
    # 验证：设备已添加
    assert "新设备" in watcher.get_active_devices()
    assert watcher.get_device_status("新设备")["is_running"] is True


def test_disable_device_at_runtime():
    """测试运行时禁用设备"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=lambda e: None)
    
    # 启动两个设备
    devices = [
        {"device_name": "设备1", "log_path": "路径1\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"},
        {"device_name": "设备2", "log_path": "路径2\\", "enabled": True, "polling_interval": 2, "encoding": "utf-8-sig"}
    ]
    watcher.start_all(devices)
    
    assert len(watcher.get_active_devices()) == 2
    
    # 停止一个设备
    watcher.stop_device("设备1")
    
    # 验证：设备已停止
    assert len(watcher.get_active_devices()) == 1
    assert "设备1" not in watcher.get_active_devices()
    assert "设备2" in watcher.get_active_devices()


def test_device_status_monitoring():
    """测试设备状态监控"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=lambda e: None)
    
    device = {
        "device_name": "测试设备",
        "log_path": "测试\\日志\\",
        "enabled": True,
        "polling_interval": 2,
        "encoding": "utf-8-sig"
    }
    
    watcher.start_device(device)
    
    # 获取设备状态
    status = watcher.get_device_status("测试设备")
    
    assert status is not None
    assert status["device_name"] == "测试设备"
    assert status["is_running"] is True
    assert status["log_path"] == "测试\\日志\\"
    assert "last_heartbeat" in status
```

### 步骤 2：运行测试验证通过

```bash
cd log-alert-service
pytest tests/integration/test_runtime_device_management.py -v
```

预期输出：全部 `PASSED`

### 步骤 3：Commit 测试文件

```bash
cd log-alert-service
git add tests/integration/test_runtime_device_management.py
git commit -m "test: add integration tests for runtime device management"
```

---

## 任务 9：实现轮询检测机制

**文件：**
- 修改：`log-alert-service/main.py:211-250`

### 步骤 1：在 AlertService.__init__ 中添加轮询相关属性

打开 `log-alert-service/main.py`，在 `__init__` 方法中添加：

```python
def __init__(self, config_path: str = "config.yaml", enable_web: bool = False):
    self.config = ConfigManager(config_path)
    self._running = False
    self.enable_web = enable_web
    self.web_app = None
    self.web_socketio = None
    self.web_thread = None

    # 初始化组件
    self._init_components()

    # 初始化通知配置（如果不存在）
    self._init_notification_config()
    
    # 设备管理轮询
    self._device_poll_interval = 30  # 30秒轮询一次
    self._last_device_poll = None
```

### 步骤 2：添加设备检测轮询方法

在 AlertService 类中添加新方法：

```python
def _poll_device_changes(self):
    """轮询检测设备配置变化
    
    检查数据库中的设备配置是否发生变化，如果有变化则更新监控。
    """
    from src.db.device_config import DeviceConfig
    
    try:
        # 获取当前应该监控的设备
        current_devices = DeviceConfig.get_all()
        enabled_devices = {d["device_name"]: d for d in current_devices if d.get("enabled", False)}
        
        # 获取当前正在监控的设备
        active_devices = set(self.multi_watcher.get_active_devices())
        
        # 应该监控的设备名称集合
        should_monitor = set(enabled_devices.keys())
        
        # 需要启动的设备（在 should_monitor 但不在 active_devices）
        to_start = should_monitor - active_devices
        
        # 需要停止的设备（在 active_devices 但不在 should_monitor）
        to_stop = active_devices - should_monitor
        
        # 启动新设备
        for device_name in to_start:
            device_config = enabled_devices[device_name]
            logger.info(f"检测到新设备: {device_name}，启动监控")
            try:
                self.multi_watcher.start_device(device_config)
            except Exception as e:
                logger.error(f"启动设备 {device_name} 失败: {e}")
        
        # 停止已禁用或删除的设备
        for device_name in to_stop:
            logger.info(f"设备 {device_name} 已禁用或删除，停止监控")
            try:
                self.multi_watcher.stop_device(device_name)
            except Exception as e:
                logger.error(f"停止设备 {device_name} 失败: {e}")
        
        self._last_device_poll = time.time()
        
    except Exception as e:
        logger.error(f"轮询设备配置变化失败: {e}")
```

### 步骤 3：在主循环中调用轮询方法

修改主循环逻辑（如果有主循环的话），或者使用 APScheduler 定时任务。在 `start()` 方法中添加定时任务：

```python
# 在 start() 方法中，添加设备轮询定时任务
if self._device_poll_interval > 0:
    self.scheduler.add_job(
        self._poll_device_changes,
        'interval',
        seconds=self._device_poll_interval,
        id='device_poll'
    )
    logger.info(f"设备配置轮询已启动，间隔: {self._device_poll_interval} 秒")
```

### 步骤 4：运行测试验证

```bash
cd log-alert-service
pytest tests/integration/test_runtime_device_management.py -v
```

预期输出：全部 `PASSED`

### 步骤 5：Commit

```bash
cd log-alert-service
git add main.py
git commit -m "feat: add device polling mechanism for runtime device management"
```

---

## 任务 10：实现设备启动/停止逻辑

**文件：**
- 修改：`log-alert-service/src/web/routes.py`

### 步骤 1：添加设备启动/停止 API 端点

打开 `log-alert-service/src/web/routes.py`，在文件末尾添加：

```python
# ==================== 设备控制 API ====================

@api_bp.route('/devices/<device_name>/start', methods=['POST'])
def start_device(device_name):
    """启动设备监控"""
    from src.device_manager import DeviceManager
    
    try:
        device_manager = DeviceManager()
        device_manager.start_device_monitoring(device_name)
        
        return jsonify({
            'success': True,
            'message': f'设备 {device_name} 监控已启动'
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"启动设备监控失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/devices/<device_name>/stop', methods=['POST'])
def stop_device(device_name):
    """停止设备监控"""
    from src.device_manager import DeviceManager
    
    try:
        device_manager = DeviceManager()
        device_manager.stop_device_monitoring(device_name)
        
        return jsonify({
            'success': True,
            'message': f'设备 {device_name} 监控已停止'
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"停止设备监控失败: {e}")
        return jsonify({'error': str(e)}), 500
```

### 步骤 2：扩展 DeviceManager 类

打开 `log-alert-service/src/device_manager.py`，添加新方法：

```python
def start_device_monitoring(self, device_name: str):
    """启动设备监控
    
    Args:
        device_name: 设备名称
        
    Raises:
        ValueError: 设备不存在
    """
    # 检查设备是否存在
    if not DeviceConfig.exists(device_name):
        raise ValueError(f"设备不存在: {device_name}")
    
    # 启用设备
    DeviceConfig.update(device_name, enabled=True)
    
    # 注意：实际的监控启动由轮询机制处理
    # 这里只是更新数据库，轮询会在 30 秒内检测到变化


def stop_device_monitoring(self, device_name: str):
    """停止设备监控
    
    Args:
        device_name: 设备名称
        
    Raises:
        ValueError: 设备不存在
    """
    # 检查设备是否存在
    if not DeviceConfig.exists(device_name):
        raise ValueError(f"设备不存在: {device_name}")
    
    # 禁用设备
    DeviceConfig.update(device_name, enabled=False)
    
    # 注意：实际的监控停止由轮询机制处理
    # 这里只是更新数据库，轮询会在 30 秒内检测到变化
```

### 步骤 3：运行测试验证

```bash
cd log-alert-service
pytest tests/integration/test_runtime_device_management.py -v
```

预期输出：全部 `PASSED`

### 步骤 4：Commit

```bash
cd log-alert-service
git add src/web/routes.py src/device_manager.py
git commit -m "feat: add device start/stop API endpoints"
```

---

## 任务 11：集成测试运行时设备管理

### 步骤 1：编写端到端测试

创建 `log-alert-service/tests/e2e/test_runtime_device_e2e.py`：

```python
"""端到端测试：运行时设备管理"""
import pytest
import time
import requests


def test_add_device_via_api_and_auto_start(base_url):
    """测试通过 API 添加设备后自动启动监控"""
    # 添加新设备
    response = requests.post(
        f"{base_url}/api/devices",
        json={
            "device_name": "E2E测试设备",
            "log_path": "E2E\\日志\\",
            "enabled": True
        }
    )
    
    assert response.status_code == 200
    
    # 等待轮询检测到新设备（最多等待 35 秒）
    for _ in range(7):
        time.sleep(5)
        
        # 检查设备是否在监控中
        response = requests.get(f"{base_url}/api/devices/status")
        status_data = response.json()
        
        active_devices = status_data.get("active_devices", [])
        if "E2E测试设备" in active_devices:
            break
    else:
        pytest.fail("设备未在 35 秒内启动监控")


def test_disable_device_via_api_and_auto_stop(base_url):
    """测试通过 API 禁用设备后自动停止监控"""
    # 先确保设备存在
    requests.post(
        f"{base_url}/api/devices",
        json={
            "device_name": "E2E禁用测试",
            "log_path": "E2E\\日志\\",
            "enabled": True
        }
    )
    
    time.sleep(35)  # 等待设备启动
    
    # 禁用设备
    requests.post(f"{base_url}/api/devices/E2E禁用测试/stop")
    
    # 等待轮询检测到变化（最多等待 35 秒）
    for _ in range(7):
        time.sleep(5)
        
        response = requests.get(f"{base_url}/api/devices/status")
        status_data = response.json()
        
        active_devices = status_data.get("active_devices", [])
        if "E2E禁用测试" not in active_devices:
            break
    else:
        pytest.fail("设备未在 35 秒内停止监控")
```

### 步骤 2：添加设备状态 API 端点

在 `log-alert-service/src/web/routes.py` 中添加：

```python
@api_bp.route('/devices/status', methods=['GET'])
def get_devices_status():
    """获取所有设备的监控状态"""
    try:
        # 这里需要访问 AlertService 实例
        # 需要修改架构使 routes 能访问 service 实例
        # 暂时返回示例实现
        return jsonify({
            'active_devices': [],
            'total_devices': 0
        })
    except Exception as e:
        logger.error(f"获取设备状态失败: {e}")
        return jsonify({'error': str(e)}), 500
```

### 步骤 3：运行端到端测试

```bash
cd log-alert-service
pytest tests/e2e/test_runtime_device_e2e.py -v
```

预期输出：全部 `PASSED`

### 步骤 4：Commit

```bash
cd log-alert-service
git add tests/e2e/test_runtime_device_e2e.py
git commit -m "test: add E2E tests for runtime device management"
```

---

## 阶段 4：优化和错误处理（含 TDD）

## 任务 12：编写错误处理测试

**文件：**
- 创建：`log-alert-service/tests/integration/test_error_handling.py`

### 步骤 1：编写错误处理测试

创建 `log-alert-service/tests/integration/test_error_handling.py`：

```python
"""测试错误处理和恢复"""
import pytest


def test_device_start_failure_handling():
    """测试设备启动失败时的处理"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=lambda e: None)
    
    # 模拟一个无效的设备配置（路径不存在）
    invalid_device = {
        "device_name": "无效设备",
        "log_path": "完全不存在的路径\\xyz123\\",
        "enabled": True,
        "polling_interval": 2,
        "encoding": "utf-8-sig"
    }
    
    # 启动应该失败，但不应该崩溃
    try:
        watcher.start_device(invalid_device)
        # 如果成功启动，验证设备在列表中
        status = watcher.get_device_status("无效设备")
        # 设备可能在列表中但状态异常
    except Exception as e:
        # 预期会抛出异常，但不应影响其他设备
        assert isinstance(e, (OSError, FileNotFoundError, Exception))
    
    # 验证：可以继续启动其他设备
    valid_device = {
        "device_name": "有效设备",
        "log_path": "有效\\路径\\",
        "enabled": True,
        "polling_interval": 2,
        "encoding": "utf-8-sig"
    }
    
    watcher.start_device(valid_device)
    assert "有效设备" in watcher.get_active_devices()


def test_multiple_devices_with_one_failure():
    """测试多个设备中有一个失败的情况"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=lambda e: None)
    
    devices = [
        {
            "device_name": "正常设备1",
            "log_path": "路径1\\",
            "enabled": True,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "故障设备",
            "log_path": "故障路径\\",
            "enabled": True,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        },
        {
            "device_name": "正常设备2",
            "log_path": "路径2\\",
            "enabled": True,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        }
    ]
    
    # 启动所有设备（即使中间有失败）
    started = []
    for device in devices:
        try:
            watcher.start_device(device)
            started.append(device["device_name"])
        except Exception:
            pass
    
    # 验证：至少有一个设备成功启动
    assert len(started) >= 1


def test_database_connection_error():
    """测试数据库连接错误处理"""
    from src.multi_device_watcher import MultiDeviceWatcher
    from unittest.mock import patch
    
    watcher = MultiDeviceWatcher(on_alarm=lambda e: None)
    
    # Mock 数据库查询失败
    with patch('src.multi_device_watcher.DeviceConfig.get_all') as mock_get_all:
        mock_get_all.side_effect = Exception("数据库连接失败")
        
        # 应该抛出异常，但不应崩溃
        with pytest.raises(Exception, match="数据库连接失败"):
            watcher.load_devices_from_db()
```

### 步骤 2：运行测试验证失败

```bash
cd log-alert-service
pytest tests/integration/test_error_handling.py -v
```

预期输出：部分 `FAILED` 或 `PASSED`（取决于错误处理的完善程度）

### 步骤 3：Commit 测试文件

```bash
cd log-alert-service
git add tests/integration/test_error_handling.py
git commit -m "test: add error handling tests for multi-device monitoring"
```

---

## 任务 13：实现优雅启动/停止

**文件：**
- 修改：`log-alert-service/src/multi_device_watcher.py`

### 步骤 1：增强 MultiDeviceWatcher 的错误处理

打开 `log-alert-service/src/multi_device_watcher.py`，修改 `start_device()` 方法，添加更完善的错误处理：

```python
def start_device(self, device_config: Dict[str, Any]):
    """为单个设备启动监控
    
    Args:
        device_config: 设备配置字典
        
    Raises:
        ValueError: 设备配置无效
        OSError: 日志目录不存在或无法访问
    """
    device_name = device_config.get("device_name")
    
    if not device_name:
        raise ValueError("设备配置缺少 device_name")
    
    with self._lock:
        # 如果设备已在监控，先停止
        if device_name in self.device_monitors:
            logger.info(f"设备 {device_name} 已在监控，先停止旧监控")
            self.stop_device(device_name)
        
        try:
            # 构建日志文件路径
            log_path = self._build_log_path(device_config.get("log_path", ""))
            
            # 验证日志目录存在
            if not Path(log_path).exists():
                logger.warning(f"设备 {device_name} 的日志目录不存在: {log_path}")
                raise OSError(f"日志目录不存在: {log_path}")
            
            # 创建 LogWatcher
            watcher = LogWatcher(
                log_dir=log_path,
                on_alarm=self._create_device_alarm_callback(device_name),
                polling_interval=device_config.get("polling_interval", 2),
                encoding=device_config.get("encoding", "utf-8-sig")
            )
            
            # 创建 DeviceMonitorInfo
            monitor_info = DeviceMonitorInfo(device_config, watcher)
            
            # 启动监控
            monitor_info.start()
            
            # 添加到监控列表
            self.device_monitors[device_name] = monitor_info
            
            logger.info(f"✅ 设备 {device_name} 监控已启动: {log_path}")
            
        except Exception as e:
            logger.error(f"❌ 启动设备 {device_name} 监控失败: {e}")
            raise
```

### 步骤 2：增强 start_all() 方法的错误处理

修改 `start_all()` 方法：

```python
def start_all(self, devices: List[Dict[str, Any]]):
    """启动所有设备的监控
    
    即使某些设备启动失败，也会继续启动其他设备。
    
    Args:
        devices: 设备配置列表
        
    Returns:
        成功启动的设备数量
    """
    logger.info(f"开始启动 {len(devices)} 个设备的监控...")
    
    success_count = 0
    failed_devices = []
    
    for device_config in devices:
        device_name = device_config.get("device_name", "未知设备")
        try:
            self.start_device(device_config)
            success_count += 1
        except Exception as e:
            logger.error(f"启动设备 {device_name} 失败: {e}")
            failed_devices.append(device_name)
    
    logger.info(f"✅ 成功启动 {success_count}/{len(devices)} 个设备监控")
    
    if failed_devices:
        logger.warning(f"⚠️  以下设备启动失败: {', '.join(failed_devices)}")
    
    return success_count
```

### 步骤 3：增强 stop_all() 方法的错误处理

修改 `stop_all()` 方法：

```python
def stop_all(self):
    """停止所有监控
    
    即使某些设备停止失败，也会继续停止其他设备。
    """
    logger.info("停止所有设备监控...")
    
    device_names = list(self.device_monitors.keys())
    stopped_count = 0
    failed_devices = []
    
    for device_name in device_names:
        try:
            self.stop_device(device_name)
            stopped_count += 1
        except Exception as e:
            logger.error(f"停止设备 {device_name} 失败: {e}")
            failed_devices.append(device_name)
    
    logger.info(f"✅ 成功停止 {stopped_count}/{len(device_names)} 个设备监控")
    
    if failed_devices:
        logger.warning(f"⚠️  以下设备停止失败: {', '.join(failed_devices)}")
```

### 步骤 4：运行测试验证通过

```bash
cd log-alert-service
pytest tests/integration/test_error_handling.py -v
```

预期输出：全部 `PASSED`

### 步骤 5：Commit

```bash
cd log-alert-service
git add src/multi_device_watcher.py
git commit -m "feat: enhance error handling in MultiDeviceWatcher"
```

---

## 任务 14：实现设备启动失败处理

**文件：**
- 修改：`log-alert-service/main.py`

### 步骤 1：修改 AlertService.start() 处理启动失败

修改 `start()` 方法中的设备启动部分：

```python
# 从数据库加载启用的设备
try:
    devices = self.multi_watcher.load_devices_from_db()
    
    if not devices:
        logger.warning("⚠️  数据库中没有启用的设备，服务将启动但不会监控任何日志")
    
    # 启动所有设备的监控
    success_count = self.multi_watcher.start_all(devices)
    
    if success_count == 0 and len(devices) > 0:
        logger.error("❌ 所有设备启动失败，服务将继续运行但不会监控任何日志")
    
except Exception as e:
    logger.error(f"❌ 加载设备配置失败: {e}")
    logger.info("服务将继续启动，但不会监控任何设备")
```

### 步骤 2：运行测试验证

```bash
cd log-alert-service
pytest tests/integration/test_error_handling.py tests/integration/test_main_service_integration.py -v
```

预期输出：全部 `PASSED`

### 步骤 3：Commit

```bash
cd log-alert-service
git add main.py
git commit -m "feat: add graceful handling for device startup failures in AlertService"
```

---

## 任务 15：压力测试和性能优化

**文件：**
- 创建：`log-alert-service/tests/integration/test_stress.py`

### 步骤 1：编写压力测试

创建 `log-alert-service/tests/integration/test_stress.py`：

```python
"""压力测试和性能验证"""
import pytest
import time


def test_max_devices_limit():
    """测试最大设备数量限制"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=lambda e: None)
    
    # 创建 15 个设备配置（超过推荐的 10 个）
    devices = []
    for i in range(15):
        devices.append({
            "device_name": f"压力测试设备{i}",
            "log_path": f"压力测试\\路径{i}\\",
            "enabled": True,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        })
    
    # 启动所有设备
    started = watcher.start_all(devices)
    
    # 验证：所有设备都能启动（即使超出推荐数量）
    assert started == 15
    assert len(watcher.get_active_devices()) == 15
    
    # 清理
    watcher.stop_all()


def test_device_status_query_performance():
    """测试设备状态查询性能"""
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=lambda e: None)
    
    # 启动 10 个设备
    devices = [
        {
            "device_name": f"设备{i}",
            "log_path": f"路径{i}\\",
            "enabled": True,
            "polling_interval": 2,
            "encoding": "utf-8-sig"
        }
        for i in range(10)
    ]
    
    watcher.start_all(devices)
    
    # 测试查询性能
    start_time = time.time()
    
    for i in range(100):
        status = watcher.get_device_status(f"设备{i % 10}")
        assert status is not None
    
    elapsed = time.time() - start_time
    
    # 验证：100 次查询应该在 1 秒内完成
    assert elapsed < 1.0
    
    watcher.stop_all()


def test_concurrent_device_start_stop():
    """测试并发启动和停止设备"""
    import threading
    
    from src.multi_device_watcher import MultiDeviceWatcher
    
    watcher = MultiDeviceWatcher(on_alarm=lambda e: None)
    
    def start_devices(device_list):
        for device in device_list:
            try:
                watcher.start_device(device)
            except Exception:
                pass
    
    # 创建 3 个线程，每个启动 3 个设备
    threads = []
    for i in range(3):
        devices = [
            {
                "device_name": f"并发设备{i}_{j}",
                "log_path": f"并发\\路径{i}_{j}\\",
                "enabled": True,
                "polling_interval": 2,
                "encoding": "utf-8-sig"
            }
            for j in range(3)
        ]
        thread = threading.Thread(target=start_devices, args=(devices,))
        threads.append(thread)
    
    # 启动所有线程
    for thread in threads:
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 验证：至少有一些设备成功启动
    active_count = len(watcher.get_active_devices())
    assert active_count > 0
    
    watcher.stop_all()
```

### 步骤 2：运行压力测试

```bash
cd log-alert-service
pytest tests/integration/test_stress.py -v
```

预期输出：全部 `PASSED`

### 步骤 3：Commit 测试文件

```bash
cd log-alert-service
git add tests/integration/test_stress.py
git commit -m "test: add stress tests for multi-device monitoring"
```

---

## 阶段 5：文档和验收

## 任务 16：更新服务文档

**文件：**
- 修改：`log-alert-service/SERVICE_GUIDE.md`

### 步骤 1：更新服务指南

打开 `log-alert-service/SERVICE_GUIDE.md`，在适当位置添加多设备监控说明：

```markdown
## 多设备监控

### 概述

系统支持同时监控多个设备的日志，每个设备有独立的配置和监控线程。

### 设备配置

设备配置存储在数据库的 `device_config` 表中，包含以下字段：

- `device_name`: 设备名称（唯一标识）
- `log_path`: 日志基础路径（系统会自动添加日期子目录）
- `enabled`: 是否启用监控
- `auto_notify`: 是否自动通知
- `polling_interval`: 轮询间隔（秒）
- `encoding`: 日志文件编码

### 运行时设备管理

系统每 30 秒轮询一次数据库，自动检测设备配置变化：

- **新设备**: 添加设备后，30 秒内自动启动监控
- **禁用设备**: 禁用设备后，30 秒内自动停止监控
- **修改配置**: 修改设备配置后，下次重启监控时生效

### 性能考虑

- 推荐最多同时监控 10 个设备
- 每个设备约占用 10-20 MB 内存
- CPU 占用取决于轮询间隔和告警频率

### 故障处理

- 单个设备启动失败不影响其他设备
- 设备日志目录不存在时跳过该设备
- 数据库连接失败时服务继续运行，但无法管理设备
```

### 步骤 2：Commit

```bash
cd log-alert-service
git add SERVICE_GUIDE.md
git commit -m "docs: add multi-device monitoring documentation to SERVICE_GUIDE"
```

---

## 任务 17：最终验收测试

### 步骤 1：运行所有测试

```bash
cd log-alert-service

# 单元测试
pytest tests/unit/test_device_monitor_info.py -v
pytest tests/unit/test_multi_device_watcher.py -v

# 集成测试
pytest tests/integration/test_main_service_integration.py -v
pytest tests/integration/test_runtime_device_management.py -v
pytest tests/integration/test_error_handling.py -v
pytest tests/integration/test_stress.py -v

# 端到端测试
pytest tests/e2e/test_runtime_device_e2e.py -v
```

预期输出：全部 `PASSED`

### 步骤 2：手动验证功能

1. **启动服务**：
   ```bash
   cd log-alert-service
   python main.py --web
   ```

2. **添加设备**：
   - 访问 http://localhost:5000
   - 进入设备管理页面
   - 添加 2-3 个测试设备
   - 观察日志输出，确认设备被启动

3. **验证监控**：
   - 在设备对应的日志目录中添加告警日志
   - 验证告警被检测并推送到飞书
   - 验证 WebSocket 实时推送

4. **禁用设备**：
   - 在 Web 界面禁用一个设备
   - 等待 30 秒
   - 验证设备监控已停止

5. **删除设备**：
   - 在 Web 界面删除一个设备
   - 验证设备监控已停止

### 步骤 3：检查功能完整性

对照设计文档的验收标准：

- [ ] 可以同时监控多个设备
- [ ] Web 界面添加的设备立即生效（30秒内）
- [ ] 可以通过 Web 界面启用/禁用设备
- [ ] 每个设备的告警独立处理
- [ ] 设备配置错误不影响其他设备监控
- [ ] 10 个设备同时运行正常
- [ ] 告警延迟 < 5 秒
- [ ] 内存占用 < 500 MB（10 个设备）
- [ ] CPU 占用 < 30%（空闲时）
- [ ] 启动服务时自动加载所有启用的设备
- [ ] 监控服务异常退出时能优雅停止
- [ ] 错误日志清晰明确
- [ ] 可以通过 API 动态管理设备

### 步骤 4：检查代码质量

```bash
cd log-alert-service

# 检查 Python 代码风格（如果有安装 pylint）
# pylint src/multi_device_watcher.py src/device_monitor_info.py

# 检查前端代码
cd frontend
npm run build  # 验证前端编译
```

### 步骤 5：最终 Commit

```bash
cd log-alert-service
git status
```

确认所有更改都已提交，如有未提交的文件：

```bash
cd log-alert-service
git add .
git commit -m "chore: final cleanup and verification for multi-device monitoring refactoring"
```

---

## 实施完成检查清单

### 核心组件
- [ ] DeviceMonitorInfo 类已实现
- [ ] MultiDeviceWatcher 类已实现
- [ ] 单元测试覆盖核心组件

### 主服务集成
- [ ] main.py 已集成 MultiDeviceWatcher
- [ ] AlertService.start() 使用多设备监控
- [ ] AlertService.stop() 正确停止所有设备
- [ ] 集成测试验证主服务集成

### 运行时设备管理
- [ ] 设备配置轮询机制已实现
- [ ] 设备启动/停止 API 端点已添加
- [ ] 运行时添加设备测试通过
- [ ] 运行时禁用设备测试通过

### 错误处理
- [ ] 设备启动失败不影响其他设备
- [ ] 优雅启动/停止已实现
- [ ] 错误日志清晰明确
- [ ] 错误处理测试通过

### 性能和稳定性
- [ ] 压力测试通过（15 个设备）
- [ ] 性能测试通过（查询 < 1秒）
- [ ] 并发测试通过

### 文档
- [ ] SERVICE_GUIDE.md 已更新
- [ ] 所有代码已提交
- [ ] 所有测试通过

---

**实现计划版本：** 1.0  
**创建日期：** 2026-07-10  
**预计工作量：** 17 个任务，约 6-10 小时  
**依赖：** 多设备监控系统重构设计文档 v1.0
