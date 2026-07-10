# 设备日志 AI 告警推送系统设计文档

> **日期：** 2026-07-09
> **状态：** 设计稿 v1
> **涉及设备：** 点胶设备（初期），后续扩展至打螺丝、排线检测、贴屏设备

---

## 1. 概述

### 1.1 目标

构建一个部署在 Windows 服务器上的日志告警推送服务，实时监控点胶设备上位机日志，当检测到报警/预警时，自动通过飞书卡片消息推送告警通知，内容包含告警详情、上下文分析及 AI 推理建议。

### 1.2 非目标

- 不修改设备上位机软件
- 不涉及 MES 系统对接（仅消费日志文件）
- 不替代设备原有的报警机制
- 不做告警自动复位或远程控制

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Windows 服务器（部署机器）                           │
│                                                                      │
│  ┌──────────────────────────────────────────┐                        │
│  │         Python 后台服务                     │                       │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────┐  │  ┌─────────────────┐│
│  │  │File      │→ │Log       │→ │Alarm    │  │  │ 日志来源          ││
│  │  │Watcher   │  │Parser    │  │Dedup    │  │  │ \\设备IPC\上位机   ││
│  │  └──────────┘  └────┬─────┘  └────┬────┘  │  │   日志\按天目录    ││
│  │                     │              │       │  └─────────────────┘│
│  │                     ▼              ▼       │                      │
│  │  ┌──────────┐  ┌───────────────────────┐   │                      │
│  │  │Context   │→ │  AI Analyzer          │   │  ┌─────────────────┐│
│  │  │Collector │  │  (Claude API)          │   │  │ Claude API      ││
│  │  └──────────┘  └──────────┬────────────┘   │  │ model-api.      ││
│  │                            │                │  │ desaysv.com     ││
│  │                            ▼                │  └─────────────────┘│
│  │  ┌──────────────────────────────────────┐   │                      │
│  │  │  Feishu Notifier                     │   │                      │
│  │  │  (tenant_access_token + IM API)       │──┼──→ 飞书群            │
│  │  └──────────────────────────────────────┘   │                      │
│  └──────────────────────────────────────────┘                        │
│                                                                      │
│  ┌──────────────────────────────────────────┐                        │
│  │  APScheduler（定时任务）                    │                        │
│  │  - Daily Report (每日 22:00 汇总推送)       │                        │
│  └──────────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 核心组件

| 组件 | 职责 | 关键技术 |
|------|------|----------|
| **FileWatcher** | 监控日志目录文件变更，捕获追加事件 | `watchdog` |
| **LogParser** | 解析日志行，识别告警级别和告警类型 | 正则匹配 |
| **AlarmDedup** | 同类告警去重合并，5 分钟内相同告警合并为一次事件 | 内存字典 + 时间窗 |
| **ContextCollector** | 提取告警行上下文 + 关联功能日志 | 时间戳关联 |
| **AIAnalyzer** | 调用 Claude API 分析上下文，生成推理和建议 | `requests` |
| **FeishuNotifier** | 通过飞书 IM API 推送卡片消息 | `requests` |
| **DailyReporter** | 定时汇总当日告警，生成日报并推送 | `apscheduler` |
| **ConfigManager** | 管理配置（yaml 文件） | `pyyaml` |

---

## 3. 日志源分析

### 3.1 目录结构

```
上位机日志\
├── 2026-06-08\
│   ├── Default.log          # 主日志（所有线程，按大小备份）
│   ├── Default.log.1        # 备份日志 1
│   ├── Default.log.2        # 备份日志 2
│   ├── 点胶交互流程.log      # 功能日志：点胶交互流程
│   ├── 点胶工站.log          # 功能日志：点胶工站
│   ├── 中间流道1.log         # 功能日志：中间流道
│   ├── 清胶工站.log          # 功能日志：清胶工站
│   └── 视觉交互.log          # 功能日志：视觉交互
├── 2026-06-09\
└── 2026-06-10\
```

### 3.2 日志格式

```
时间 [线程号] [命名空间.类名][行号] - 消息内容

示例：
2026-06-08 21:51:36,674 [   1] [DesaySV.Presentation.Core.FrmMain][319] - 点胶交互流程:右点胶阀缺胶报警_人工请马上更换
```

### 3.3 告警类型

| 类型 | 判定关键词 | 示例 | 严重级别 |
|------|-----------|------|---------|
| **报警** | 包含"报警" | `右点胶阀缺胶报警_人工请马上更换` | critical |
| **预警** | 包含"预警" | `右点胶阀缺胶预警_人工请及时更换_复位后继续启动` | warning |
| **复位操作** | 包含"报警复位操作" | `报警复位操作` | info |
| **异常** | 包含"异常" | 待补充 | critical |

### 3.4 日志轮转规则

- `Default.log` 超过 ~5MB 时备份为 `Default.log.1`
- 原 `Default.log.1` 推至 `Default.log.2`
- `Default.log.2` 被覆盖
- 功能日志（中文名）无备份机制（未观察到 .1/.2 后缀）

---

## 4. 告警检测与去重

### 4.1 告警行匹配规则

```python
# 主日志（Default.log）告警匹配
ALARM_PATTERNS = {
    "critical": [
        r"报警_(?!复位).*",      # 报警_xxx（排除"报警复位"）
        r".*异常.*",
    ],
    "warning": [
        r"预警_.*",
    ],
    "info": [
        r"报警复位操作",
    ]
}

# 功能日志告警行匹配（直接匹配）
FUNCTIONAL_LOG_PATTERNS = {
    "critical": [r"报警_人工请马上更换"],
    "warning":  [r"预警_人工请及时更换"],
}
```

### 4.2 去重规则

- **去重键：** `(告警文本摘要, 模块名)`
- **去重窗口：** 300 秒（5 分钟）
- **同一窗口内的行为：** 不触发新推送，记录重复次数
- **窗口刷新：** 每次新告警重置该键的窗口计时器（只要告警持续出现，推送只在首次和窗口超时后触发）

### 4.3 上下文提取

当检测到告警时，提取以下上下文：

1. **Default.log 上下文：** 告警行前后各 20 行
2. **功能日志关联：** 在告警时间 ±5 秒范围内，搜索中文功能日志中相关的告警/状态行
3. **当日历史告警计数：** 该告警类型当天已出现的次数

---

## 5. AI 分析

### 5.1 API 配置

| 参数 | 值 |
|------|-----|
| Base URL | `http://model-api.desaysv.com` |
| 模型 | `deepseek-v4-flash-anthropic` |
| 最大 Token | 2048 |
| 温度 | 0.3（倾向于确定性输出） |

> API Key 通过环境变量 `CLAUDE_API_KEY` 读取，不写入配置文件或代码。

### 5.2 Prompt 设计

**系统提示词：**
```
你是一个设备故障诊断专家。分析以下日志片段，找出告警的根本原因，
并给出具体的故障排除建议。回答要简洁、实用、针对具体的设备和工站。
只基于提供的日志内容做分析，不要猜测没有依据的原因。
```

**用户输入结构：**
```
[告警信息]
时间: {timestamp}
告警内容: {alarm_text}
模块: {module_name}
当日同类告警次数: {count}

[Default.log 上下文]
{context_lines}

[功能日志关联]
{functional_log_context}
```

**输出格式（JSON）：**
```json
{
  "root_cause": "根本原因分析（1-2句话，中文）",
  "severity": "critical | warning | info",
  "suggestion": "具体的操作建议（分点列出，中文）",
  "related_module": "相关模块或工站",
  "probable_time_to_resolve": "预计处理时间（如：5分钟 / 30分钟 / 需停机）"
}
```

### 5.3 成本控制

- **每次告警事件调用 1 次 API**（去重合并后）
- **每日汇总调用 1 次 API**
- 可通过配置 `ai_analysis.enabled: false` 关闭 AI 分析，此时只推送原始告警信息
- API 调用失败时，自动降级为无 AI 分析的推送

---

## 6. 飞书消息推送

### 6.1 鉴权方式

使用**自建应用**方式，通过 `tenant_access_token` 调用 IM API。

```
1. 获取 `tenant_access_token`（App ID 和 Secret 从环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 读取）
2. 发送消息
POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id
Header: Authorization: Bearer <tenant_access_token>
Body: {
    "receive_id": "<chat_id>",
    "msg_type": "interactive",
    "content": "<卡片JSON>"
}
```

### 6.2 目标群

| 群名 | chat_id | 推送内容 |
|------|---------|---------|
| 日志分析测试 | `oc_aa8f612241f26528a681db30bda7402e` | 测试/调试消息 |
| 设备日志AI分析预警 | `oc_e0dadc6e5ab606ff14ceb6f1150ee418` | 正式告警通知 + 日报 |

### 6.3 实时告警卡片

```
┌──────────────────────────────────────┐
│ 🔴 告警通知 - 点胶设备               │  header: red template
├──────────────────────────────────────┤
│ 告警时间：2026-06-08 21:51:36        │  div
│ 告警类型：⚠️ 报警                     │
│ 告警内容：右点胶阀缺胶报警            │
│ 设备工站：点胶交互流程                │
│ 当日已出现：3 次                      │
├──────────────────────────────────────┤  hr
│ 🧠 AI 分析                           │  div
│ **根本原因：**                         │
│ 右点胶阀胶量不足，可能胶桶已空或      │
│ 胶路堵塞导致缺胶报警。                │
│                                      │
│ **建议操作：**                        │
│ 1. 检查右点胶阀胶桶剩余量              │
│ 2. 如胶桶已空，更换新胶桶             │
│ 3. 检查胶路是否堵塞                    │
├──────────────────────────────────────┤  hr
│ 📋 日志参考                           │  div
│ Default.log #1825-1845               │
│ 点胶交互流程.log #11590-11598        │
├──────────────────────────────────────┤  note
│ 点胶设备 · 日志AI分析预警系统 v0.1    │
└──────────────────────────────────────┘
```

### 6.4 每日汇总卡片

```
┌──────────────────────────────────────┐
│ 📊 点胶设备告警日报 - 2026-06-08     │  header: blue template
├──────────────────────────────────────┤
│ **告警统计**                          │  div
│ 告警总次数：12 次                      │
│ 告警类型分布：                         │
│   🔴 缺胶报警：8 次                    │
│   🟡 缺胶预警：3 次                    │
│   ℹ️ 复位操作：11 次                  │
│ 已复位未解决：6 次                     │
├──────────────────────────────────────┤  hr
│ 🧠 今日总结                           │  div
│ 今日主要告警集中在右点胶阀缺胶，        │
│ 操作员多次复位但未更换胶桶，建议        │
│ 接班时优先确认胶桶状态。               │
├──────────────────────────────────────┤  hr
│ 🔗 详细记录查看：[日志文件路径]         │  div
├──────────────────────────────────────┤  note
│ 点胶设备 · 日志AI分析预警系统 v0.1    │
└──────────────────────────────────────┘
```

---

## 7. 配置文件

```yaml
# config.yaml - 告警推送服务配置

# 日志源
log_source:
  type: windows_share          # windows_share | local
  path: \\设备IPC\上位机日志\    # 共享文件夹路径
  polling_interval: 2          # 目录轮询间隔（秒）
  encoding: utf-8              # 日志文件编码
  max_context_lines: 20        # 告警前后提取的行数
  functional_log_window: 5     # 功能日志关联时间窗口（秒）

# 飞书配置（App ID 和 Secret 从环境变量读取）
feishu:
  app_id: "${FEISHU_APP_ID}"
  app_secret: "${FEISHU_APP_SECRET}"
  chats:                               # 推送目标群
    - chat_id: oc_aa8f612241f26528a681db30bda7402e
      type: debug                      # debug = 仅调试消息
    - chat_id: oc_e0dadc6e5ab606ff14ceb6f1150ee418
      type: production                 # production = 正式告警 + 日报

# AI 分析（API Key 从环境变量读取）
ai_analysis:
  enabled: true
  api_key: "${CLAUDE_API_KEY}"
  api_base_url: http://model-api.desaysv.com
  model: deepseek-v4-flash-anthropic
  max_tokens: 2048
  temperature: 0.3

# 去重配置
dedup:
  alarm_window: 300            # 同类告警去重窗口（秒）
  max_repeat_count: 99         # 超过此次数强制推送一次

# 每日汇总
daily_report:
  enabled: true
  schedule_time: "22:00"       # 推送时间（24小时制）

# 监控设备（可扩展）
devices:
  - name: 点胶设备
    log_path: 点胶设备\上位机日志\
    enabled: true
  # - name: 打螺丝设备
  #   log_path: 打螺丝设备\上位机日志\
  #   enabled: false
  # - name: 排线检测设备
  #   log_path: 排线检测设备\上位机日志\
  #   enabled: false
  # - name: 贴屏设备
  #   log_path: 贴屏设备\上位机日志\
  #   enabled: false
```

---

## 8. 部署方案

### 8.1 环境要求

| 项 | 要求 |
|----|------|
| 操作系统 | Windows Server 2016+ / Windows 10+ |
| Python | 3.10+ |
| 网络 | 可访问日志共享文件夹 + 外网（飞书 API + Claude API） |
| 运行方式 | Windows Service（通过 `nssm` 或 `pywin32` 注册） |

### 8.2 项目结构

```
log-alert-service/
├── main.py                  # 入口文件
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖
├── src/
│   ├── __init__.py
│   ├── file_watcher.py      # 文件监控
│   ├── log_parser.py        # 日志解析
│   ├── alarm_dedup.py       # 告警去重
│   ├── context_collector.py # 上下文收集
│   ├── ai_analyzer.py       # AI 分析
│   ├── feishu_notifier.py   # 飞书推送
│   ├── daily_reporter.py    # 每日汇总
│   ├── config_manager.py    # 配置管理
│   └── models.py            # 数据模型
├── tests/
│   ├── test_log_parser.py
│   ├── test_alarm_dedup.py
│   ├── test_context_collector.py
│   ├── test_ai_analyzer.py
│   └── test_feishu_notifier.py
├── logs/                    # 服务自身运行日志
└── README.md                # 部署说明
```

### 8.3 关键技术依赖

```txt
# requirements.txt
watchdog>=4.0.0        # 文件系统监控
pyyaml>=6.0            # 配置管理
requests>=2.31.0       # HTTP 请求
apscheduler>=3.10.0    # 定时任务
python-dotenv>=1.0.0   # 环境变量管理
```

### 8.4 部署步骤

1. 安装 Python 3.10+
2. 克隆项目，创建虚拟环境：`python -m venv venv`
3. 安装依赖：`pip install -r requirements.txt`
4. 创建 `.env` 文件（或设置系统环境变量），包含敏感凭证：
   ```
   FEISHU_APP_ID=cli_a95710cbf179dcbb
   FEISHU_APP_SECRET=<your_secret>
   CLAUDE_API_KEY=<your_api_key>
   ```
5. 配置 `config.yaml`
6. 启动服务：`python main.py`
7. 注册为 Windows Service（可选）：
   ```
   nssm install LogAlertService "D:\log-alert-service\venv\Scripts\python.exe" "D:\log-alert-service\main.py"
   nssm start LogAlertService
   ```

---

## 9. 错误处理与降级策略

| 场景 | 行为 |
|------|------|
| 飞书 token 获取失败 | 重试 3 次，间隔 5 秒；仍失败则写本地日志，跳过该次推送 |
| API 调用超时 | 超时时间 30 秒，降级推送无 AI 分析的卡片 |
| 日志文件被轮转 | 自动检测文件变化，切换到新文件继续监控 |
| 网络中断 | 缓存告警事件，恢复后批量推送（最多缓存 50 条） |
| 共享文件夹不可达 | 每隔 60 秒重试连接，恢复后自动继续 |

---

## 10. 版本规划

| 版本 | 功能 | 时间 |
|------|------|------|
| v0.1 | 实时告警推送 + 飞书卡片 + AI 分析 | 当前设计 |
| v0.2 | 每日汇总报告 | 后续 |
| v0.3 | 其他设备接入（打螺丝/排线/贴屏） | 后续 |
| v0.4 | Web 管理界面（告警历史查询） | 后续 |
| v1.0 | 告警统计面板 + 告警规则自定义 | 后续 |

---

## 11. 附录

### 11.1 告警事件示例分析

以下为从实际日志中提取的典型告警事件分析：

**事件：** 2026-06-08 21:51 右点胶阀缺胶报警

**Default.log 时序：**
1. 21:51:34 — 点胶完成，数据上传
2. 21:51:36 — RFID 写入完成
3. **21:51:36,674 — FrmMain: 右点胶阀缺胶报警_人工请马上更换**
4. 21:51:55~21:52:08 — 操作员连续 6 次"报警复位操作"
5. 每次复位后立即再次触发报警

**功能日志关联（点胶交互流程.log）：**
6. 21:51:36,512 — FlowRelationStation: 右点胶阀缺胶报警_人工请马上更换

**分析结论：**
- 右点胶阀胶量已耗尽
- 操作员反复复位不解决问题
- 建议立即更换右点胶阀胶桶