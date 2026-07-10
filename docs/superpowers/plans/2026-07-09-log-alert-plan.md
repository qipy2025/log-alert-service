# 设备日志 AI 告警推送系统 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。
>
> **参考设计文档：** `docs/superpowers/specs/2026-07-09-log-alert-design.md`

**目标：** 构建一个部署在 Windows 服务器上的 Python 后台服务，实时监控点胶设备上位机日志，检测报警/预警后通过飞书卡片消息推送通知（含 AI 推理建议）。

**架构：** 单进程 Python 服务，使用 watchdog 监控日志文件变更，正则匹配告警行，requests 调用 Claude API 做分析，飞书 IM API 推送卡片消息。APScheduler 管理每日定时汇总。

**技术栈：** Python 3.10+, watchdog, pyyaml, requests, apscheduler, python-dotenv

**项目根目录：** `D:\code\LOG\log-alert-service\`

---

## 文件结构

```
log-alert-service/
├── main.py                        # 入口：服务启动 + 组件编排
├── config.yaml                    # 配置文件（不含敏感信息）
├── .env                           # 环境变量（FEISHU_APP_ID, FEISHU_APP_SECRET, CLAUDE_API_KEY）
├── requirements.txt               # 依赖
├── README.md                      # 部署说明
├── src/
│   ├── __init__.py
│   ├── config_manager.py          # 配置管理（yaml + 环境变量）
│   ├── models.py                  # 数据模型（AlarmEvent, AlarmLevel 等）
│   ├── file_watcher.py            # 文件监控（watchdog 事件处理）
│   ├── log_parser.py              # 日志解析 + 告警行匹配
│   ├── alarm_dedup.py             # 告警去重
│   ├── context_collector.py       # 上下文收集（Default.log + 功能日志）
│   ├── ai_analyzer.py             # Claude API 调用
│   ├── feishu_notifier.py         # 飞书消息推送
│   └── daily_reporter.py          # 每日汇总
└── tests/
    ├── __init__.py
    ├── test_log_parser.py
    ├── test_alarm_dedup.py
    ├── test_context_collector.py
    ├── test_ai_analyzer.py
    └── test_feishu_notifier.py
```

---

### 任务 1：项目骨架和环境配置

**文件：**
- 创建：`log-alert-service/requirements.txt`
- 创建：`log-alert-service/config.yaml`
- 创建：`log-alert-service/src/__init__.py`
- 创建：`log-alert-service/tests/__init__.py`
- 创建：`log-alert-service/src/config_manager.py`
- 创建：`log-alert-service/src/models.py`

**测试文件：**
- 创建：`log-alert-service/tests/test_config_manager.py`

- [ ] **步骤 1：创建 requirements.txt**

```txt
watchdog>=4.0.0
pyyaml>=6.0
requests>=2.31.0
apscheduler>=3.10.0
python-dotenv>=1.0.0
pytest>=8.0
pytest-mock>=3.0
```

- [ ] **步骤 2：创建 models.py — 定义数据模型**

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AlarmLevel(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlarmSource(Enum):
    DEFAULT_LOG = "Default.log"
    FUNCTIONAL_LOG = "functional_log"


@dataclass
class AlarmEvent:
    """单个告警事件"""
    timestamp: datetime
    alarm_text: str
    module_name: str
    level: AlarmLevel
    source: AlarmSource
    line_number: int
    log_file: str
    raw_line: str
    context_lines: list[str] = field(default_factory=list)
    functional_log_context: list[str] = field(default_factory=list)
    daily_count: int = 1


@dataclass
class AnalysisResult:
    """AI 分析结果"""
    root_cause: str
    severity: str
    suggestion: str
    related_module: str
    probable_time_to_resolve: str = ""


@dataclass
class DailySummary:
    """每日汇总数据"""
    date: str
    total_alarms: int
    alarm_counts: dict[str, int]  # {alarm_type: count}
    reset_counts: int
    unresolved_alarms: int
    summary_text: str = ""
```

- [ ] **步骤 3：创建 config_manager.py**

```python
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigManager:
    """管理配置文件和环境变量"""

    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = f.read()
        # 替换 ${VAR} 占位符为环境变量
        import re

        def _env_replace(match: re.Match) -> str:
            var_name = match.group(1)
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(f"Environment variable {var_name} is not set")
            return value

        resolved = re.sub(r"\$\{(\w+)\}", _env_replace, raw)
        self._config = yaml.safe_load(resolved)

    def get(self, key: str, default: Any = None) -> Any:
        """通过点号路径获取配置，如 'feishu.app_id'"""
        parts = key.split(".")
        value = self._config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def raw(self) -> dict[str, Any]:
        return self._config
```

- [ ] **步骤 4：编写 config_manager 测试**

```python
# tests/test_config_manager.py
import os
import tempfile
from pathlib import Path
import pytest
import yaml

from src.config_manager import ConfigManager


def test_config_manager_loads_yaml():
    """测试加载基本 yaml 配置"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_data = {"log_source": {"path": "\\\test\\path", "polling_interval": 2}}
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        cm = ConfigManager(str(config_path))
        assert cm.get("log_source.path") == "\\test\\path"
        assert cm.get("log_source.polling_interval") == 2


def test_config_manager_env_var_substitution():
    """测试 ${VAR} 占位符能从环境变量读取"""
    os.environ["TEST_SECRET"] = "test_secret_value"
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("feishu:\n  app_secret: \"${TEST_SECRET}\"\n")

        cm = ConfigManager(str(config_path))
        assert cm.get("feishu.app_secret") == "test_secret_value"


def test_config_manager_missing_env_var():
    """测试缺少环境变量时抛出 ValueError"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("feishu:\n  app_secret: \"${MISSING_VAR}\"\n")

        with pytest.raises(ValueError, match="MISSING_VAR"):
            ConfigManager(str(config_path))


def test_config_manager_file_not_found():
    """测试配置文件不存在时抛出 FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        ConfigManager("/nonexistent/path/config.yaml")
```

- [ ] **步骤 5：运行测试验证全部通过**

运行：`cd D:\code\LOG\log-alert-service && pip install -r requirements.txt && python -m pytest tests/test_config_manager.py -v`

预期：4 个测试全部 PASS

- [ ] **步骤 6：创建 config.yaml（不含敏感信息）**

```yaml
# config.yaml - 告警推送服务配置
# 敏感信息（API Key / Secret）通过 .env 文件设置

# 日志源
log_source:
  type: windows_share
  path: "D:\\code\\LOG\\CD-ADS-1\\点胶设备\\上位机日志\\"
  polling_interval: 2
  encoding: utf-8
  max_context_lines: 20
  functional_log_window: 5

# 飞书配置（App ID 和 Secret 从 .env 读取）
feishu:
  app_id: "${FEISHU_APP_ID}"
  app_secret: "${FEISHU_APP_SECRET}"
  chats:
    - chat_id: oc_aa8f612241f26528a681db30bda7402e
      type: debug
      name: "日志分析测试"
    - chat_id: oc_e0dadc6e5ab606ff14ceb6f1150ee418
      type: production
      name: "设备日志AI分析预警"

# AI 分析（API Key 从 .env 读取）
ai_analysis:
  enabled: true
  api_key: "${CLAUDE_API_KEY}"
  api_base_url: "http://model-api.desaysv.com"
  model: "deepseek-v4-flash-anthropic"
  max_tokens: 2048
  temperature: 0.3

# 去重
dedup:
  alarm_window: 300
  max_repeat_count: 99

# 每日汇总
daily_report:
  enabled: true
  schedule_time: "22:00"

# 监控设备
devices:
  - name: "点胶设备"
    log_path: "点胶设备\\上位机日志\\"
    enabled: true
```

---

### 任务 2：日志解析器（LogParser）

**文件：**
- 创建：`log-alert-service/src/log_parser.py`

**测试文件：**
- 创建：`log-alert-service/tests/test_log_parser.py`

- [ ] **步骤 1：编写 log_parser.py**

```python
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import AlarmLevel, AlarmSource, AlarmEvent


# Default.log 日志行正则
# 格式：2026-06-08 21:51:36,674 [   1] [Namespace.Class][Line] - 消息
LOG_LINE_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+"
    r"\[\s*(\d+)\]\s+"
    r"\[([^\]]+)\]"
    r"\[(\d+)\]\s*-\s*(.*)$"
)

# 告警级别匹配模式
ALARM_PATTERNS: dict[AlarmLevel, list[re.Pattern]] = {
    AlarmLevel.CRITICAL: [
        re.compile(r"报警_(?!复位)"),    # "报警_xxx" 但不匹配 "报警复位"
        re.compile(r"异常"),
    ],
    AlarmLevel.WARNING: [
        re.compile(r"预警_"),
    ],
    AlarmLevel.INFO: [
        re.compile(r"报警复位操作"),
    ],
}

# 功能日志告警匹配
FUNCTIONAL_ALARM_PATTERNS: dict[AlarmLevel, list[re.Pattern]] = {
    AlarmLevel.CRITICAL: [
        re.compile(r"报警_人工请马上更换"),
    ],
    AlarmLevel.WARNING: [
        re.compile(r"预警_人工请及时更换"),
    ],
}


def parse_log_line(line: str) -> Optional[dict]:
    """解析单行日志，返回结构化字典或 None（不匹配格式时）"""
    match = LOG_LINE_PATTERN.match(line)
    if not match:
        return None

    timestamp_str = match.group(1)
    thread_id = match.group(2)
    class_name = match.group(3)
    line_number = int(match.group(4))
    message = match.group(5)

    # 解析时间戳
    timestamp = datetime.strptime(
        timestamp_str.replace(",", "."),
        "%Y-%m-%d %H:%M:%S.%f"
    )

    return {
        "timestamp": timestamp,
        "thread_id": int(thread_id),
        "class_name": class_name,
        "line_number": line_number,
        "message": message,
        "raw_line": line.strip(),
    }


def detect_alarm_level(message: str, is_functional_log: bool = False) -> Optional[AlarmLevel]:
    """检测消息是否包含告警，返回告警级别或 None"""
    patterns = FUNCTIONAL_ALARM_PATTERNS if is_functional_log else ALARM_PATTERNS
    for level, regexes in patterns.items():
        for pattern in regexes:
            if pattern.search(message):
                return level
    return None


def create_alarm_event(
    parsed_line: dict,
    log_file: str,
    is_functional_log: bool = False,
) -> Optional[AlarmEvent]:
    """从解析后的日志行创建告警事件"""
    level = detect_alarm_level(parsed_line["message"], is_functional_log)
    if level is None:
        return None

    return AlarmEvent(
        timestamp=parsed_line["timestamp"],
        alarm_text=parsed_line["message"],
        module_name=parsed_line["class_name"],
        level=level,
        source=AlarmSource.FUNCTIONAL_LOG if is_functional_log else AlarmSource.DEFAULT_LOG,
        line_number=parsed_line["line_number"],
        log_file=log_file,
        raw_line=parsed_line["raw_line"],
    )


def scan_file_for_alarms(
    file_path: str,
    start_line: int = 0,
    is_functional_log: bool = False,
) -> list[AlarmEvent]:
    """扫描文件中的告警行，返回告警事件列表"""
    alarms: list[AlarmEvent] = []
    filepath = Path(file_path)
    if not filepath.exists():
        return alarms

    with open(filepath, "r", encoding="utf-8-sig") as f:
        for line_idx, line in enumerate(f):
            if line_idx < start_line:
                continue
            parsed = parse_log_line(line)
            if parsed is None:
                continue
            event = create_alarm_event(parsed, file_path, is_functional_log)
            if event is not None:
                alarms.append(event)
    return alarms
```

- [ ] **步骤 2：编写 log_parser 测试**

```python
# tests/test_log_parser.py
import pytest
from datetime import datetime
from src.log_parser import (
    parse_log_line,
    detect_alarm_level,
    create_alarm_event,
)
from src.models import AlarmLevel, AlarmSource


class TestParseLogLine:
    def test_parse_normal_line(self):
        """测试解析正常的 Default.log 行"""
        line = "2026-06-08 21:51:55,901 [   6] [DesaySV.Presentation.Core.FrmMain][1742] - 报警复位操作"
        result = parse_log_line(line)
        assert result is not None
        assert result["thread_id"] == 6
        assert result["class_name"] == "DesaySV.Presentation.Core.FrmMain"
        assert result["line_number"] == 1742
        assert result["message"] == "报警复位操作"

    def test_parse_alarm_line(self):
        """测试解析告警行"""
        line = "2026-06-08 21:51:36,674 [   1] [DesaySV.Presentation.Core.FrmMain][319] - 点胶交互流程:右点胶阀缺胶报警_人工请马上更换"
        result = parse_log_line(line)
        assert result is not None
        assert "缺胶报警" in result["message"]

    def test_parse_invalid_line(self):
        """测试不匹配格式的行"""
        line = "这是一行无效日志"
        assert parse_log_line(line) is None

    def test_parse_empty_line(self):
        """测试空行"""
        assert parse_log_line("") is None


class TestDetectAlarmLevel:
    def test_critical_alarm(self):
        """检测 critical 级别告警"""
        assert detect_alarm_level("右点胶阀缺胶报警_人工请马上更换") == AlarmLevel.CRITICAL

    def test_warning_alarm(self):
        """检测 warning 级别告警"""
        assert detect_alarm_level("右点胶阀缺胶预警_人工请及时更换") == AlarmLevel.WARNING

    def test_reset_operation(self):
        """检测复位操作"""
        assert detect_alarm_level("报警复位操作") == AlarmLevel.INFO

    def test_no_alarm(self):
        """非告警消息返回 None"""
        assert detect_alarm_level("轨迹数据3动作") is None

    def test_functional_log_critical(self):
        """功能日志 critical 告警"""
        assert detect_alarm_level(
            "右点胶阀缺胶报警_人工请马上更换", is_functional_log=True
        ) == AlarmLevel.CRITICAL


class TestCreateAlarmEvent:
    def test_create_from_parsed_line(self):
        """从解析行创建告警事件"""
        parsed = {
            "timestamp": datetime(2026, 6, 8, 21, 51, 36),
            "thread_id": 1,
            "class_name": "DesaySV.Presentation.Core.FrmMain",
            "line_number": 319,
            "message": "右点胶阀缺胶报警_人工请马上更换",
            "raw_line": "2026-06-08 21:51:36,674 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换",
        }
        event = create_alarm_event(parsed, "Default.log")
        assert event is not None
        assert event.level == AlarmLevel.CRITICAL
        assert event.module_name == "DesaySV.Presentation.Core.FrmMain"
        assert event.log_file == "Default.log"

    def test_non_alarm_returns_none(self):
        """非告警行返回 None"""
        parsed = {
            "timestamp": datetime(2026, 6, 8, 21, 51, 30),
            "thread_id": 37,
            "class_name": "DesaySV.Presentation.Core.GlueModule",
            "line_number": 233,
            "message": "轨迹数据3动作",
            "raw_line": "...",
        }
        assert create_alarm_event(parsed, "Default.log") is None
```

- [ ] **步骤 3：运行测试**

运行：`cd D:\code\LOG\log-alert-service && python -m pytest tests/test_log_parser.py -v`

预期：至少 8 个测试全部 PASS

---

### 任务 3：告警去重（AlarmDedup）

**文件：**
- 创建：`log-alert-service/src/alarm_dedup.py`

**测试文件：**
- 创建：`log-alert-service/tests/test_alarm_dedup.py`

- [ ] **步骤 1：编写 alarm_dedup.py**

```python
import time
from typing import Optional
from .models import AlarmEvent


class AlarmDedup:
    """告警去重器：相同 (告警文本摘要, 模块名) 在窗口内合并"""

    def __init__(self, window_seconds: int = 300, max_repeat: int = 99):
        self.window = window_seconds
        self.max_repeat = max_repeat
        # { dedup_key: (first_timestamp, count, last_notified_count) }
        self._cache: dict[str, tuple[float, int, int]] = {}

    def _make_key(self, event: AlarmEvent) -> str:
        """生成去重键：告警文本前 20 字 + 模块名"""
        text_key = event.alarm_text[:20]
        return f"{text_key}|{event.module_name}"

    def should_notify(self, event: AlarmEvent) -> bool:
        """
        判断是否应该推送此告警。
        返回 True 表示需要推送（首次出现或窗口超时）。
        返回 False 表示在去重窗口内。
        """
        key = self._make_key(event)
        now = time.time()

        if key not in self._cache:
            self._cache[key] = (now, 1, 1)
            return True

        first_time, count, last_notified = self._cache[key]
        elapsed = now - first_time

        if elapsed > self.window:
            # 窗口超时，重置
            self._cache[key] = (now, count + 1, 1)
            return True

        # 窗口内
        self._cache[key] = (first_time, count + 1, last_notified)

        # 如果超过最大重复次数，强制推送
        if count + 1 >= self.max_repeat:
            self._cache[key] = (first_time, count + 1, count + 1)
            return True

        return False

    def get_repeat_count(self, event: AlarmEvent) -> int:
        """获取当前告警的重复次数"""
        key = self._make_key(event)
        if key not in self._cache:
            return 0
        return self._cache[key][1]

    def cleanup(self, max_age: float = 3600) -> None:
        """清理超过 max_age 秒的缓存"""
        now = time.time()
        stale = [k for k, v in self._cache.items() if now - v[0] > max_age]
        for k in stale:
            del self._cache[k]
```

- [ ] **步骤 2：编写 alarm_dedup 测试**

```python
# tests/test_alarm_dedup.py
import time
import pytest
from datetime import datetime
from src.alarm_dedup import AlarmDedup
from src.models import AlarmLevel, AlarmSource, AlarmEvent


def _make_event(alarm_text: str, module: str = "TestModule") -> AlarmEvent:
    return AlarmEvent(
        timestamp=datetime.now(),
        alarm_text=alarm_text,
        module_name=module,
        level=AlarmLevel.CRITICAL,
        source=AlarmSource.DEFAULT_LOG,
        line_number=1,
        log_file="Default.log",
        raw_line=alarm_text,
    )


class TestAlarmDedup:
    def test_first_alarm_notifies(self):
        """首次告警应推送"""
        dedup = AlarmDedup(window_seconds=300)
        event = _make_event("右点胶阀缺胶报警")
        assert dedup.should_notify(event) is True

    def test_same_alarm_in_window_does_not_notify(self):
        """窗口内相同告警不应推送"""
        dedup = AlarmDedup(window_seconds=300)
        event = _make_event("右点胶阀缺胶报警")
        assert dedup.should_notify(event) is True
        assert dedup.should_notify(event) is False
        assert dedup.should_notify(event) is False

    def test_different_alarms_both_notify(self):
        """不同告警都应推送"""
        dedup = AlarmDedup(window_seconds=300)
        e1 = _make_event("右点胶阀缺胶报警")
        e2 = _make_event("左点胶阀缺胶报警")
        assert dedup.should_notify(e1) is True
        assert dedup.should_notify(e2) is True

    def test_same_alarm_after_window_expiry(self):
        """窗口过期后相同告警应再次推送"""
        dedup = AlarmDedup(window_seconds=1)
        event = _make_event("右点胶阀缺胶报警")
        assert dedup.should_notify(event) is True
        assert dedup.should_notify(event) is False
        time.sleep(1.1)
        assert dedup.should_notify(event) is True

    def test_repeat_count_tracking(self):
        """重复次数跟踪"""
        dedup = AlarmDedup(window_seconds=300)
        event = _make_event("右点胶阀缺胶报警")
        assert dedup.get_repeat_count(event) == 0
        dedup.should_notify(event)
        assert dedup.get_repeat_count(event) == 1
        dedup.should_notify(event)
        assert dedup.get_repeat_count(event) == 2

    def test_cleanup_removes_stale_entries(self):
        """清理应移除过期条目"""
        dedup = AlarmDedup(window_seconds=300)
        event = _make_event("右点胶阀缺胶报警")
        dedup.should_notify(event)
        assert len(dedup._cache) == 1
        dedup.cleanup(max_age=0)  # 清理所有
        assert len(dedup._cache) == 0
```

- [ ] **步骤 3：运行测试**

运行：`cd D:\code\LOG\log-alert-service && python -m pytest tests/test_alarm_dedup.py -v`

预期：6 个测试全部 PASS

---

### 任务 4：上下文收集器（ContextCollector）

**文件：**
- 创建：`log-alert-service/src/context_collector.py`

**测试文件：**
- 创建：`log-alert-service/tests/test_context_collector.py`

- [ ] **步骤 1：编写 context_collector.py**

```python
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .log_parser import parse_log_line, detect_alarm_level
from .models import AlarmEvent


def read_lines(
    file_path: str,
    encoding: str = "utf-8-sig",
) -> list[tuple[int, str, Optional[dict]]]:
    """
    读取文件，返回 [(line_number_0index, raw_line, parsed_dict_or_None), ...]
    """
    lines: list[tuple[int, str, Optional[dict]]] = []
    filepath = Path(file_path)
    if not filepath.exists():
        return lines

    with open(filepath, "r", encoding=encoding) as f:
        for idx, raw_line in enumerate(f):
            parsed = parse_log_line(raw_line)
            lines.append((idx, raw_line.rstrip("\n\r"), parsed))
    return lines


def extract_context(
    lines: list[tuple[int, str, Optional[dict]]],
    target_idx: int,
    context_lines: int = 20,
) -> list[str]:
    """提取目标行前后各 N 行的上下文"""
    start = max(0, target_idx - context_lines)
    end = min(len(lines), target_idx + context_lines + 1)
    return [lines[i][1] for i in range(start, end)]


def find_related_functional_logs(
    timestamp: datetime,
    log_dir: str,
    window_seconds: int = 5,
) -> list[tuple[str, str]]:
    """
    在功能日志中查找时间相关的告警行。
    返回 [(文件名, 原始行), ...]
    """
    related: list[tuple[str, str]] = []
    log_dir_path = Path(log_dir)

    # 中文功能日志文件列表
    functional_logs = [
        "点胶交互流程.log",
        "点胶工站.log",
        "中间流道1.log",
        "清胶工站.log",
        "视觉交互.log",
    ]

    time_start = timestamp - timedelta(seconds=window_seconds)
    time_end = timestamp + timedelta(seconds=window_seconds)

    for log_name in functional_logs:
        log_path = log_dir_path / log_name
        if not log_path.exists():
            continue

        with open(log_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                parsed = parse_log_line(line)
                if parsed is None:
                    continue
                # 检查时间窗口内且包含告警
                if time_start <= parsed["timestamp"] <= time_end:
                    level = detect_alarm_level(parsed["message"], is_functional_log=True)
                    if level is not None:
                        related.append((log_name, parsed["raw_line"]))

    return related


def collect_context(
    event: AlarmEvent,
    log_dir: str,
    max_context_lines: int = 20,
    functional_window: int = 5,
) -> AlarmEvent:
    """
    为告警事件收集上下文：
    1. Default.log 前后行上下文
    2. 功能日志中的关联告警行
    """
    # 1. 收集 Default.log 上下文
    default_log_path = Path(log_dir) / event.log_file
    default_dir = str(Path(log_dir) / Path(event.log_file).parent)  # 兼容子目录
    if default_log_path.exists():
        lines = read_lines(str(default_log_path))
        target_idx = next(
            (i for i, (_, _, p) in enumerate(lines) if p and p["line_number"] == event.line_number),
            None,
        )
        if target_idx is not None:
            event.context_lines = extract_context(lines, target_idx, max_context_lines)

    # 2. 收集功能日志上下文
    functional_context = find_related_functional_logs(
        event.timestamp,
        str(Path(log_dir).parent),  # 上位机日志/ 目录
        functional_window,
    )
    event.functional_log_context = [
        f"[{fname}] {line}" for fname, line in functional_context
    ]

    return event
```

- [ ] **步骤 2：编写 context_collector 测试**

```python
# tests/test_context_collector.py
import tempfile
from datetime import datetime
from pathlib import Path
import pytest

from src.context_collector import (
    read_lines,
    extract_context,
    find_related_functional_logs,
    collect_context,
)
from src.models import AlarmLevel, AlarmSource, AlarmEvent


SAMPLE_LINES = [
    "2026-06-08 21:51:30,072 [  37] [Module1][233] - 轨迹数据3动作",
    "2026-06-08 21:51:30,104 [  37] [Module1][233] - 轨迹数据4动作",
    "2026-06-08 21:51:30,136 [  37] [Module1][233] - 轨迹数据5动作",
    "2026-06-08 21:51:36,674 [   1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换",
    "2026-06-08 21:51:55,901 [   6] [FrmMain][1742] - 报警复位操作",
    "2026-06-08 21:52:04,619 [   6] [FrmMain][1742] - 报警复位操作",
]


class TestContextCollector:
    def test_read_lines(self):
        """测试读取和解析日志行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            with open(log_path, "w", encoding="utf-8") as f:
                for line in SAMPLE_LINES:
                    f.write(line + "\n")

            lines = read_lines(str(log_path))
            assert len(lines) == 6
            # 验证解析成功的行
            parsed_count = sum(1 for _, _, p in lines if p is not None)
            assert parsed_count == 6

    def test_extract_context(self):
        """测试上下文提取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            with open(log_path, "w", encoding="utf-8") as f:
                for line in SAMPLE_LINES:
                    f.write(line + "\n")

            lines = read_lines(str(log_path))
            # 提取索引 3（告警行）前后各 2 行
            ctx = extract_context(lines, 3, context_lines=2)
            assert len(ctx) <= 5  # start=1, end=6
            assert "缺胶报警" in " ".join(ctx)

    def test_collect_context_sets_context_lines(self):
        """collect_context 应填充 context_lines"""
        event = AlarmEvent(
            timestamp=datetime(2026, 6, 8, 21, 51, 36),
            alarm_text="右点胶阀缺胶报警_人工请马上更换",
            module_name="FrmMain",
            level=AlarmLevel.CRITICAL,
            source=AlarmSource.DEFAULT_LOG,
            line_number=319,
            log_file="Default.log",
            raw_line=SAMPLE_LINES[3],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            with open(log_path, "w", encoding="utf-8") as f:
                for line in SAMPLE_LINES:
                    f.write(line + "\n")

            result = collect_context(event, str(tmpdir), max_context_lines=2)
            assert len(result.context_lines) > 0
```

- [ ] **步骤 3：运行测试**

运行：`cd D:\code\LOG\log-alert-service && python -m pytest tests/test_context_collector.py -v`

预期：3 个测试全部 PASS

---

### 任务 5：AI 分析器（AIAnalyzer）

**文件：**
- 创建：`log-alert-service/src/ai_analyzer.py`

**测试文件：**
- 创建：`log-alert-service/tests/test_ai_analyzer.py`

- [ ] **步骤 1：编写 ai_analyzer.py**

```python
import json
from typing import Optional

import requests

from .models import AlarmEvent, AnalysisResult


SYSTEM_PROMPT = """你是一个设备故障诊断专家。分析以下日志片段，找出告警的根本原因，
并给出具体的故障排除建议。回答要简洁、实用、针对具体的设备和工站。
只基于提供的日志内容做分析，不要猜测没有依据的原因。

请严格按以下 JSON 格式输出，不要包含任何其他内容：
{
  "root_cause": "根本原因分析（1-2句话）",
  "severity": "critical | warning | info",
  "suggestion": "具体的操作建议，分点列出",
  "related_module": "相关模块或工站",
  "probable_time_to_resolve": "预计处理时间"
}"""


class AIAnalyzer:
    """调用 Claude API（兼容接口）分析告警上下文"""

    def __init__(
        self,
        api_key: str,
        api_base_url: str = "http://model-api.desaysv.com",
        model: str = "deepseek-v4-flash-anthropic",
        max_tokens: int = 2048,
        temperature: float = 0.3,
        timeout: int = 30,
        enabled: bool = True,
    ):
        self.api_key = api_key
        self.api_base_url = api_base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.enabled = enabled

    def _build_prompt(self, event: AlarmEvent) -> str:
        """构建分析 prompt"""
        parts = [
            "[告警信息]",
            f"时间: {event.timestamp}",
            f"告警内容: {event.alarm_text}",
            f"模块: {event.module_name}",
            f"当日同类告警次数: {event.daily_count}",
            "",
            "[Default.log 上下文]",
        ]
        parts.extend(event.context_lines)
        parts.append("")
        parts.append("[功能日志关联]")
        parts.extend(event.functional_log_context)
        return "\n".join(parts)

    def analyze(self, event: AlarmEvent) -> Optional[AnalysisResult]:
        """
        分析告警事件，返回分析结果。
        如果 AI 分析被禁用或调用失败，返回 None。
        """
        if not self.enabled:
            return None

        prompt = self._build_prompt(event)

        try:
            response = requests.post(
                f"{self.api_base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "system": SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # 提取响应文本
            content = data.get("content", [])
            if not content:
                return None

            response_text = content[0].get("text", "") if isinstance(content[0], dict) else content[0]

            # 解析 JSON
            return self._parse_response(response_text)

        except requests.exceptions.RequestException as e:
            print(f"[AIAnalyzer] API 请求失败: {e}")
            return None
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"[AIAnalyzer] 响应解析失败: {e}, raw: {response_text if 'response_text' in dir() else 'N/A'}")
            return None

    def _parse_response(self, text: str) -> Optional[AnalysisResult]:
        """从 AI 响应中提取 JSON"""
        # 尝试直接解析
        text = text.strip()
        # 处理可能包含 ```json ... ``` 代码块的情况
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)
        return AnalysisResult(
            root_cause=data.get("root_cause", ""),
            severity=data.get("severity", "warning"),
            suggestion=data.get("suggestion", ""),
            related_module=data.get("related_module", ""),
            probable_time_to_resolve=data.get("probable_time_to_resolve", ""),
        )
```

- [ ] **步骤 2：编写 ai_analyzer 测试**

```python
# tests/test_ai_analyzer.py
import pytest
from datetime import datetime
from src.ai_analyzer import AIAnalyzer, AnalysisResult
from src.models import AlarmLevel, AlarmSource, AlarmEvent


def _make_event() -> AlarmEvent:
    return AlarmEvent(
        timestamp=datetime(2026, 6, 8, 21, 51, 36),
        alarm_text="右点胶阀缺胶报警_人工请马上更换",
        module_name="DesaySV.Presentation.Core.FrmMain",
        level=AlarmLevel.CRITICAL,
        source=AlarmSource.DEFAULT_LOG,
        line_number=319,
        log_file="Default.log",
        raw_line="2026-06-08 21:51:36,674 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换",
        context_lines=[
            "2026-06-08 21:51:34,189 [37] [GlueModule][751] - 热熔阀点胶回吸完成",
            "2026-06-08 21:51:36,674 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换",
            "2026-06-08 21:51:55,901 [6] [FrmMain][1742] - 报警复位操作",
        ],
        functional_log_context=[
            "[点胶交互流程.log] 2026-06-08 21:51:36,512 - 右点胶阀缺胶报警_人工请马上更换",
        ],
    )


class TestAIAnalyzer:
    def test_disabled_returns_none(self):
        """禁用 AI 分析时返回 None"""
        analyzer = AIAnalyzer(api_key="test", enabled=False)
        result = analyzer.analyze(_make_event())
        assert result is None

    def test_build_prompt_contains_alarm_info(self):
        """prompt 应包含告警信息"""
        analyzer = AIAnalyzer(api_key="test")
        event = _make_event()
        prompt = analyzer._build_prompt(event)
        assert "右点胶阀缺胶报警" in prompt
        assert "Default.log 上下文" in prompt
        assert "功能日志关联" in prompt

    def test_parse_valid_json(self):
        """解析有效的 JSON 响应"""
        analyzer = AIAnalyzer(api_key="test")
        text = '{"root_cause":"胶量不足","severity":"critical","suggestion":"更换胶桶","related_module":"点胶阀","probable_time_to_resolve":"10分钟"}'
        result = analyzer._parse_response(text)
        assert result is not None
        assert result.root_cause == "胶量不足"
        assert result.severity == "critical"
        assert result.suggestion == "更换胶桶"

    def test_parse_json_in_code_block(self):
        """解析被 ```json 包裹的 JSON"""
        analyzer = AIAnalyzer(api_key="test")
        text = '```json\n{"root_cause":"胶路堵塞","severity":"critical","suggestion":"检查胶路","related_module":"点胶阀","probable_time_to_resolve":"30分钟"}\n```'
        result = analyzer._parse_response(text)
        assert result is not None
        assert result.root_cause == "胶路堵塞"

    def test_parse_invalid_json(self):
        """解析无效 JSON 返回 None"""
        analyzer = AIAnalyzer(api_key="test")
        with pytest.raises(Exception):
            analyzer._parse_response("不是 JSON 内容")
```

- [ ] **步骤 3：运行测试**

运行：`cd D:\code\LOG\log-alert-service && python -m pytest tests/test_ai_analyzer.py -v`

预期：5 个测试全部 PASS

---

### 任务 6：飞书通知器（FeishuNotifier）

**文件：**
- 创建：`log-alert-service/src/feishu_notifier.py`

**测试文件：**
- 创建：`log-alert-service/tests/test_feishu_notifier.py`

- [ ] **步骤 1：编写 feishu_notifier.py**

```python
import json
import time
from typing import Any, Optional

import requests

from .models import AlarmEvent, AlarmLevel, AnalysisResult, DailySummary


class FeishuNotifier:
    """飞书消息推送（自建应用方式）"""

    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        chats: list[dict],
        timeout: int = 10,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.chats = chats  # [{"chat_id": "...", "type": "debug|production", "name": "..."}]
        self.timeout = timeout
        self._token: Optional[str] = None
        self._token_expire: float = 0

    def _get_token(self) -> str:
        """获取 tenant_access_token（带缓存）"""
        if self._token and time.time() < self._token_expire - 60:
            return self._token

        resp = requests.post(
            self.TOKEN_URL,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get token: {data}")

        self._token = data["tenant_access_token"]
        self._token_expire = time.time() + data["expire"]
        return self._token

    def _send_message(self, chat_id: str, card: dict) -> bool:
        """发送卡片消息到指定群"""
        token = self._get_token()
        payload = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        }

        resp = requests.post(
            self.MESSAGE_URL,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            print(f"[FeishuNotifier] 发送失败: {result}")
            return False
        return True

    def _get_target_chats(self, msg_type: str = "production") -> list[str]:
        """获取目标群 chat_id 列表"""
        return [
            c["chat_id"]
            for c in self.chats
            if c.get("type") == msg_type or c.get("type") == "debug"
        ]

    def _build_alarm_card(self, event: AlarmEvent, analysis: Optional[AnalysisResult] = None) -> dict:
        """构建告警卡片"""
        level_colors = {
            AlarmLevel.CRITICAL: "red",
            AlarmLevel.WARNING: "yellow",
            AlarmLevel.INFO: "blue",
        }
        level_icons = {
            AlarmLevel.CRITICAL: "🔴",
            AlarmLevel.WARNING: "🟡",
            AlarmLevel.INFO: "ℹ️",
        }

        header_title = f"{level_icons[event.level]} 告警通知 - 点胶设备"
        color = level_colors[event.level]

        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**告警时间：**{event.timestamp}\n"
                        f"**告警类型：**{level_icons[event.level]} {event.level.value}\n"
                        f"**告警内容：**{event.alarm_text}\n"
                        f"**模块：**{event.module_name}\n"
                        f"**当日已出现：**{event.daily_count} 次"
                    ),
                },
            },
            {"tag": "hr"},
        ]

        if analysis:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**🧠 AI 分析**\n"
                        f"**根本原因：**{analysis.root_cause}\n\n"
                        f"**建议操作：**{analysis.suggestion}\n\n"
                        f"**预计处理时间：**{analysis.probable_time_to_resolve}"
                    ),
                },
            })
            elements.append({"tag": "hr"})

        if event.context_lines:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**📋 日志参考**\n" + "\n".join(event.context_lines[-5:]),
                },
            })

        elements.append({
            "tag": "note",
            "elements": [
                {"tag": "plain_text", "content": "点胶设备 · 日志AI分析预警系统 v0.1"}
            ],
        })

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": header_title},
                "template": color,
            },
            "elements": elements,
        }

    def send_alarm(
        self,
        event: AlarmEvent,
        analysis: Optional[AnalysisResult] = None,
    ) -> bool:
        """推送告警通知到所有生产群"""
        card = self._build_alarm_card(event, analysis)
        chat_ids = self._get_target_chats("production")

        all_ok = True
        for chat_id in chat_ids:
            ok = self._send_message(chat_id, card)
            if not ok:
                all_ok = False
        return all_ok

    def send_test(self, chat_id: str) -> bool:
        """发送测试消息（用于验证配置）"""
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "✅ 告警推送服务测试"},
                "template": "green",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**告警推送服务已配置成功！**\n\n告警推送服务已成功连接到飞书。",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**当前配置：**\n- 监控设备：点胶设备\n- AI 分析：已启用\n- 推送格式：富文本卡片",
                    },
                },
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": "设备日志AI分析预警系统 v0.1"}
                    ],
                },
            ],
        }
        return self._send_message(chat_id, card)

    def _build_daily_report_card(self, summary: DailySummary) -> dict:
        """构建每日汇总卡片"""
        alarm_type_str = "\n".join(
            [f"   {k}：{v} 次" for k, v in summary.alarm_counts.items()]
        )

        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**告警统计**\n"
                        f"告警总次数：{summary.total_alarms} 次\n\n"
                        f"**告警类型分布：**\n{alarm_type_str}\n\n"
                        f"**已复位未解决：**{summary.unresolved_alarms} 次"
                    ),
                },
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**🧠 今日总结**\n{summary.summary_text}",
                },
            },
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": "点胶设备 · 日志AI分析预警系统 v0.1"}
                ],
            },
        ]

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 点胶设备告警日报 - {summary.date}",
                },
                "template": "blue",
            },
            "elements": elements,
        }

    def send_daily_report(self, summary: DailySummary) -> bool:
        """推送每日汇总报告"""
        card = self._build_daily_report_card(summary)
        chat_ids = self._get_target_chats("production")

        all_ok = True
        for chat_id in chat_ids:
            ok = self._send_message(chat_id, card)
            if not ok:
                all_ok = False
        return all_ok
```

- [ ] **步骤 2：编写 feishu_notifier 测试**

```python
# tests/test_feishu_notifier.py
from datetime import datetime
import pytest
from src.feishu_notifier import FeishuNotifier
from src.models import AlarmEvent, AlarmLevel, AlarmSource, AnalysisResult, DailySummary


def _make_event() -> AlarmEvent:
    return AlarmEvent(
        timestamp=datetime(2026, 6, 8, 21, 51, 36),
        alarm_text="右点胶阀缺胶报警_人工请马上更换",
        module_name="DesaySV.Presentation.Core.FrmMain",
        level=AlarmLevel.CRITICAL,
        source=AlarmSource.DEFAULT_LOG,
        line_number=319,
        log_file="Default.log",
        raw_line="...",
        context_lines=[
            "2026-06-08 21:51:34,189 - 热熔阀点胶回吸完成",
            "2026-06-08 21:51:36,674 - 右点胶阀缺胶报警_人工请马上更换",
        ],
        daily_count=3,
    )


class TestFeishuNotifier:
    def setup_method(self):
        self.notifier = FeishuNotifier(
            app_id="test_id",
            app_secret="test_secret",
            chats=[
                {"chat_id": "test_chat_1", "type": "debug", "name": "测试群"},
                {"chat_id": "test_chat_2", "type": "production", "name": "生产群"},
            ],
        )

    def test_build_alarm_card_without_analysis(self):
        """无 AI 分析的告警卡片"""
        event = _make_event()
        card = self.notifier._build_alarm_card(event)
        assert card["header"]["template"] == "red"
        assert "右点胶阀缺胶报警" in card["header"]["title"]["content"]
        assert len(card["elements"]) == 3  # div + hr + note

    def test_build_alarm_card_with_analysis(self):
        """有 AI 分析的告警卡片"""
        event = _make_event()
        analysis = AnalysisResult(
            root_cause="胶量不足，建议更换胶桶",
            severity="critical",
            suggestion="1. 检查胶桶\n2. 更换胶桶",
            related_module="点胶阀",
            probable_time_to_resolve="10分钟",
        )
        card = self.notifier._build_alarm_card(event, analysis)
        assert "胶量不足" in str(card)
        assert len(card["elements"]) == 4  # div + hr + div(分析) + hr + note...→ 4 elements

    def test_get_target_chats(self):
        """获取目标群"""
        production = self.notifier._get_target_chats("production")
        assert "test_chat_2" in production
        assert "test_chat_1" in production  # debug 群也包含

    def test_build_daily_report_card(self):
        """每日汇总卡片"""
        summary = DailySummary(
            date="2026-06-08",
            total_alarms=12,
            alarm_counts={"缺胶报警": 8, "缺胶预警": 3, "复位操作": 11},
            reset_counts=11,
            unresolved_alarms=6,
            summary_text="今日主要告警集中在右点胶阀缺胶。",
        )
        card = self.notifier._build_daily_report_card(summary)
        assert card["header"]["template"] == "blue"
        assert "2026-06-08" in card["header"]["title"]["content"]
```

- [ ] **步骤 3：运行测试**

运行：`cd D:\code\LOG\log-alert-service && python -m pytest tests/test_feishu_notifier.py -v`

预期：4 个测试全部 PASS

---

### 任务 7：文件监控器（FileWatcher）

**文件：**
- 创建：`log-alert-service/src/file_watcher.py`

**测试文件：**
- 创建：`log-alert-service/tests/test_file_watcher.py`

- [ ] **步骤 1：编写 file_watcher.py**

```python
import os
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer

from .log_parser import parse_log_line, detect_alarm_level, create_alarm_event
from .models import AlarmEvent


class LogFileHandler(FileSystemEventHandler):
    """watchdog 事件处理器，监控日志文件变更"""

    def __init__(
        self,
        default_log_file: str,
        on_alarm: Callable[[AlarmEvent], None],
        encoding: str = "utf-8-sig",
    ):
        self.default_log_file = default_log_file
        self.on_alarm = on_alarm
        self.encoding = encoding
        self._last_position: dict[str, int] = {}  # 文件路径 → 上次读取到的位置

    def on_modified(self, event: FileModifiedEvent):
        """文件被修改时调用"""
        if not event.is_directory and event.src_path.endswith("Default.log"):
            self._process_new_lines(event.src_path)

    def _process_new_lines(self, file_path: str):
        """读取文件新增的行，检测告警"""
        path = Path(file_path)
        if not path.exists():
            return

        current_size = path.stat().st_size
        last_pos = self._last_position.get(file_path, 0)

        # 检测文件轮转（新文件比上次位置小）
        if current_size < last_pos:
            last_pos = 0

        if current_size == last_pos:
            return

        with open(file_path, "r", encoding=self.encoding) as f:
            f.seek(last_pos)
            for line in f:
                parsed = parse_log_line(line)
                if parsed is None:
                    continue
                level = detect_alarm_level(parsed["message"])
                if level is not None:
                    event = create_alarm_event(parsed, file_path)
                    if event is not None:
                        self.on_alarm(event)

        self._last_position[file_path] = current_size

    def scan_existing_file(self, file_path: str):
        """扫描已有文件全部内容（启动时使用）"""
        self._last_position[file_path] = 0
        self._process_new_lines(file_path)


class LogWatcher:
    """日志目录监控器"""

    def __init__(
        self,
        log_dir: str,
        on_alarm: Callable[[AlarmEvent], None],
        polling_interval: int = 2,
        encoding: str = "utf-8-sig",
    ):
        self.log_dir = log_dir
        self.polling_interval = polling_interval
        self.observer = Observer()
        self.handler = LogFileHandler(
            default_log_file=str(Path(log_dir) / "Default.log"),
            on_alarm=on_alarm,
            encoding=encoding,
        )

    def start(self):
        """启动监控"""
        self.observer.schedule(
            self.handler,
            self.log_dir,
            recursive=False,
        )
        self.observer.start()

        # 启动时扫描已有文件
        default_log = Path(self.log_dir) / "Default.log"
        if default_log.exists():
            self.handler.scan_existing_file(str(default_log))

    def stop(self):
        """停止监控"""
        self.observer.stop()
        self.observer.join()
```

- [ ] **步骤 2：编写 file_watcher 测试**

```python
# tests/test_file_watcher.py
import tempfile
import time
from pathlib import Path
import pytest
from src.file_watcher import LogFileHandler, LogWatcher
from src.models import AlarmLevel


class TestLogFileHandler:
    def test_process_new_lines_detects_alarm(self):
        """新写入的告警行应被检测"""
        alarms = []

        def callback(event):
            alarms.append(event)

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            log_path.write_text(
                "2026-06-08 21:51:30,072 [37] [Module][233] - 轨迹数据\n",
                encoding="utf-8",
            )

            handler = LogFileHandler(
                default_log_file=str(log_path),
                on_alarm=callback,
            )

            # 追加告警行
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("2026-06-08 21:51:36,674 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换\n")

            handler._process_new_lines(str(log_path))
            assert len(alarms) == 1
            assert alarms[0].level == AlarmLevel.CRITICAL

    def test_no_alarm_no_callback(self):
        """非告警行不触发回调"""
        alarms = []

        def callback(event):
            alarms.append(event)

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "Default.log"
            log_path.write_text("", encoding="utf-8")

            handler = LogFileHandler(
                default_log_file=str(log_path),
                on_alarm=callback,
            )

            with open(log_path, "a", encoding="utf-8") as f:
                f.write("2026-06-08 21:51:30,072 [37] [Module][233] - 轨迹数据\n")

            handler._process_new_lines(str(log_path))
            assert len(alarms) == 0
```

- [ ] **步骤 3：运行测试**

运行：`cd D:\code\LOG\log-alert-service && python -m pytest tests/test_file_watcher.py -v`

预期：2 个测试全部 PASS

---

### 任务 8：每日汇总器（DailyReporter）

**文件：**
- 创建：`log-alert-service/src/daily_reporter.py`

**测试文件：**
- 创建：`log-alert-service/tests/test_daily_reporter.py`

- [ ] **步骤 1：编写 daily_reporter.py**

```python
from collections import defaultdict
from datetime import datetime
from typing import Optional

from .models import AlarmEvent, DailySummary
from .ai_analyzer import AIAnalyzer
from .log_parser import scan_file_for_alarms


class DailyReporter:
    """每日告警汇总"""

    def __init__(
        self,
        log_dir: str,
        ai_analyzer: Optional[AIAnalyzer] = None,
        functional_log_dir: Optional[str] = None,
    ):
        self.log_dir = log_dir
        self.ai_analyzer = ai_analyzer
        self.functional_log_dir = functional_log_dir or log_dir
        self._today_alarms: dict[str, list[AlarmEvent]] = defaultdict(list)

    def record_alarm(self, event: AlarmEvent):
        """记录告警（由文件监控器触发时调用）"""
        date_key = event.timestamp.strftime("%Y-%m-%d")
        self._today_alarms[date_key].append(event)

    def get_summary(self, date_str: str) -> DailySummary:
        """生成指定日期的汇总"""
        alarms = self._today_alarms.get(date_str, [])

        alarm_counts: dict[str, int] = defaultdict(int)
        reset_count = 0
        for a in alarms:
            if "复位" in a.alarm_text:
                reset_count += 1
            # 取告警文本的前 10 个字作为类型
            alarm_type = a.alarm_text[:10]
            alarm_counts[alarm_type] += 1

        # 判断未解决告警：报警次数 > 复位次数
        critical_count = sum(1 for a in alarms if a.level.value == "critical")
        unresolved = max(0, critical_count - reset_count)

        summary_text = ""
        if self.ai_analyzer and self.ai_analyzer.enabled and alarms:
            # 用 AI 生成总结
            try:
                combined_context = "\n".join(
                    [f"[{a.timestamp}] {a.alarm_text}" for a in alarms[-10:]]
                )
                from .models import AlarmEvent as TempEvent
                from datetime import datetime as dt

                mock_event = TempEvent(
                    timestamp=dt.now(),
                    alarm_text=f"告警日报汇总 - {date_str}",
                    module_name="DailyReporter",
                    level=__import__("src.models", fromlist=["AlarmLevel"]).AlarmLevel.INFO,
                    source=__import__("src.models", fromlist=["AlarmSource"]).AlarmSource.DEFAULT_LOG,
                    line_number=0,
                    log_file="",
                    raw_line="",
                    context_lines=[f"今日告警共 {len(alarms)} 次"] + alarms[-5:],
                )
                result = self.ai_analyzer.analyze(mock_event)
                if result:
                    summary_text = result.root_cause
            except Exception as e:
                summary_text = f"AI 总结生成失败: {e}"

        if not summary_text:
            summary_text = f"今日共 {len(alarms)} 次告警，{reset_count} 次复位操作，{unresolved} 次未解决。"

        return DailySummary(
            date=date_str,
            total_alarms=len(alarms),
            alarm_counts=dict(alarm_counts),
            reset_counts=reset_count,
            unresolved_alarms=unresolved,
            summary_text=summary_text,
        )
```

- [ ] **步骤 2：编写 daily_reporter 测试**

```python
# tests/test_daily_reporter.py
from datetime import datetime
import pytest
from src.daily_reporter import DailyReporter
from src.models import AlarmEvent, AlarmLevel, AlarmSource


def _make_alarm(text: str, level: AlarmLevel = AlarmLevel.CRITICAL) -> AlarmEvent:
    return AlarmEvent(
        timestamp=datetime(2026, 6, 8, 21, 51, 36),
        alarm_text=text,
        module_name="FrmMain",
        level=level,
        source=AlarmSource.DEFAULT_LOG,
        line_number=1,
        log_file="Default.log",
        raw_line=text,
    )


class TestDailyReporter:
    def test_get_summary_empty_day(self):
        """空日期的汇总"""
        reporter = DailyReporter(log_dir="/tmp")
        summary = reporter.get_summary("2026-06-08")
        assert summary.total_alarms == 0
        assert summary.reset_counts == 0

    def test_get_summary_with_alarms(self):
        """有告警的汇总"""
        reporter = DailyReporter(log_dir="/tmp")
        reporter.record_alarm(_make_alarm("右点胶阀缺胶报警"))
        reporter.record_alarm(_make_alarm("右点胶阀缺胶报警"))
        reporter.record_alarm(_make_alarm("报警复位操作", AlarmLevel.INFO))
        reporter.record_alarm(_make_alarm("左点胶阀缺胶预警", AlarmLevel.WARNING))

        summary = reporter.get_summary("2026-06-08")
        assert summary.total_alarms == 4
        assert summary.reset_counts == 1
        assert "右点胶阀缺胶报警" in summary.alarm_counts
```

- [ ] **步骤 3：运行测试**

运行：`cd D:\code\LOG\log-alert-service && python -m pytest tests/test_daily_reporter.py -v`

预期：2 个测试全部 PASS

---

### 任务 9：主入口（main.py）

**文件：**
- 创建：`log-alert-service/main.py`

- [ ] **步骤 1：编写 main.py**

```python
#!/usr/bin/env python3
"""
设备日志 AI 告警推送服务

实时监控点胶设备上位机日志，检测报警后通过飞书推送通知。
"""

import logging
import signal
import sys
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from src.config_manager import ConfigManager
from src.file_watcher import LogWatcher
from src.alarm_dedup import AlarmDedup
from src.context_collector import collect_context
from src.ai_analyzer import AIAnalyzer
from src.feishu_notifier import FeishuNotifier
from src.daily_reporter import DailyReporter

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("service.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class AlertService:
    """告警推送服务主类"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = ConfigManager(config_path)
        self._running = False

        # 初始化组件
        self._init_components()

    def _init_components(self):
        """初始化各组件"""
        # 告警去重
        self.dedup = AlarmDedup(
            window_seconds=self.config.get("dedup.alarm_window", 300),
            max_repeat=self.config.get("dedup.max_repeat_count", 99),
        )

        # AI 分析
        ai_config = self.config.get("ai_analysis", {})
        self.ai_analyzer = AIAnalyzer(
            api_key=ai_config.get("api_key", ""),
            api_base_url=ai_config.get("api_base_url", "http://model-api.desaysv.com"),
            model=ai_config.get("model", "deepseek-v4-flash-anthropic"),
            max_tokens=ai_config.get("max_tokens", 2048),
            temperature=ai_config.get("temperature", 0.3),
            enabled=ai_config.get("enabled", True),
        )

        # 飞书通知器
        feishu_config = self.config.get("feishu", {})
        self.notifier = FeishuNotifier(
            app_id=feishu_config.get("app_id", ""),
            app_secret=feishu_config.get("app_secret", ""),
            chats=feishu_config.get("chats", []),
        )

        # 每日汇总
        self.reporter = DailyReporter(
            log_dir="",
            ai_analyzer=self.ai_analyzer,
        )

        # 定时任务
        self.scheduler = BackgroundScheduler()

        # 当前监控的日期目录
        self._current_log_dir: str = ""

    def _on_alarm(self, event):
        """告警回调"""
        try:
            # 1. 去重检查
            if not self.dedup.should_notify(event):
                logger.debug(f"告警被去重: {event.alarm_text}")
                return

            # 更新告警的当日重复次数
            event.daily_count = self.dedup.get_repeat_count(event)

            # 2. 收集上下文
            if self._current_log_dir:
                collect_context(
                    event,
                    self._current_log_dir,
                    self.config.get("log_source.max_context_lines", 20),
                    self.config.get("log_source.functional_log_window", 5),
                )

            # 3. AI 分析
            analysis = self.ai_analyzer.analyze(event)

            # 4. 记录到日报
            self.reporter.record_alarm(event)

            # 5. 推送飞书
            success = self.notifier.send_alarm(event, analysis)
            if success:
                logger.info(f"告警推送成功: {event.alarm_text}")
            else:
                logger.error(f"告警推送失败: {event.alarm_text}")

        except Exception as e:
            logger.exception(f"处理告警时出错: {e}")

    def _send_daily_report(self):
        """发送每日汇总报告"""
        try:
            from datetime import datetime, timedelta

            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            summary = self.reporter.get_summary(yesterday)
            self.notifier.send_daily_report(summary)
            logger.info(f"每日汇总推送成功: {yesterday}")
        except Exception as e:
            logger.exception(f"发送每日汇总时出错: {e}")

    def start(self):
        """启动服务"""
        logger.info("=" * 50)
        logger.info("设备日志 AI 告警推送服务启动中...")
        logger.info("=" * 50)

        # 获取日志路径
        log_source = self.config.get("log_source", {})
        base_path = log_source.get("path", "")

        # 确定今天的日志目录
        from datetime import datetime

        today_str = datetime.now().strftime("%Y-%m-%d")
        today_dir = str(Path(base_path) / today_str)
        self._current_log_dir = today_dir

        logger.info(f"监控日志目录: {today_dir}")

        # 启动文件监控
        self.watcher = LogWatcher(
            log_dir=today_dir,
            on_alarm=self._on_alarm,
            polling_interval=log_source.get("polling_interval", 2),
            encoding=log_source.get("encoding", "utf-8-sig"),
        )
        self.watcher.start()
        logger.info("文件监控已启动")

        # 配置每日汇总定时任务
        daily_config = self.config.get("daily_report", {})
        if daily_config.get("enabled", True):
            schedule_time = daily_config.get("schedule_time", "22:00")
            hour, minute = schedule_time.split(":")
            self.scheduler.add_job(
                self._send_daily_report,
                "cron",
                hour=int(hour),
                minute=int(minute),
                id="daily_report",
            )
            self.scheduler.start()
            logger.info(f"每日汇总定时任务已设定: {schedule_time}")

        self._running = True
        logger.info("服务启动完成 ✅")

    def stop(self):
        """停止服务"""
        logger.info("正在停止服务...")
        self._running = False
        if hasattr(self, "watcher"):
            self.watcher.stop()
        if hasattr(self, "scheduler") and self.scheduler.running:
            self.scheduler.shutdown()
        logger.info("服务已停止")


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"

    service = AlertService(config_path)

    def signal_handler(sig, frame):
        logger.info("收到停止信号")
        service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        service.start()
        # 保持运行
        import time

        while service._running:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()


if __name__ == "__main__":
    main()
```

---

### 任务 10：创建 README 和 .env 模板

**文件：**
- 创建：`log-alert-service/README.md`
- 创建：`log-alert-service/.env.example`

- [ ] **步骤 1：创建 .env.example**

```bash
# 飞书应用凭证
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret

# AI 模型 API
CLAUDE_API_KEY=your_api_key
```

- [ ] **步骤 2：创建 README.md**

```markdown
# 设备日志 AI 告警推送系统

实时监控点胶设备上位机日志，检测告警并通过飞书推送通知（含 AI 分析建议）。

## 快速开始

### 1. 配置环境

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制并编辑）
cp .env.example .env
```

编辑 `.env` 文件，填入飞书和 Claude API 的凭证。

### 2. 配置 config.yaml

根据实际环境修改 `config.yaml`：
- `log_source.path`：日志文件所在的共享文件夹路径
- `feishu.chats`：推送目标群

### 3. 启动服务

```bash
python main.py
```

### 4. 注册为 Windows Service（可选）

```bash
nssm install LogAlertService "D:\path\to\venv\Scripts\python.exe" "D:\path\to\main.py"
nssm start LogAlertService
```

## 功能

- **实时告警推送**：自动检测日志中的报警/预警，通过飞书卡片推送
- **AI 分析**：调用大模型分析告警上下文，给出根本原因和处理建议
- **告警去重**：同类告警 5 分钟内自动合并，减少重复通知
- **每日汇总**：每天 22:00 推送当日告警统计报告
- **多群推送**：支持同时推送到多个飞书群

## 项目结构

```
log-alert-service/
├── main.py              # 入口
├── config.yaml          # 配置
├── .env                 # 环境变量（敏感信息）
├── src/                 # 核心代码
│   ├── file_watcher.py       # 文件监控
│   ├── log_parser.py         # 日志解析
│   ├── alarm_dedup.py        # 告警去重
│   ├── context_collector.py  # 上下文收集
│   ├── ai_analyzer.py        # AI 分析
│   ├── feishu_notifier.py    # 飞书推送
│   ├── daily_reporter.py     # 每日汇总
│   └── config_manager.py     # 配置管理
└── tests/               # 测试
```

## 依赖

- Python 3.10+
- 见 requirements.txt
```