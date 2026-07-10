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

## 测试

### 运行测试

```bash
# 运行所有测试
pytest -v

# 只运行单元测试
pytest tests/unit/ -v

# 只运行集成测试
pytest tests/integration/ -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 测试覆盖

- ✅ 完整告警流程（3个场景）
- ✅ 边界场景测试（4个场景）
- ✅ 异常恢复测试（4个场景）
- ✅ 每日汇总测试（2个场景）
- ✅ 单元测试（34个测试，3个待修复）

### 测试数据

测试日志文件位于 `tests/fixtures/logs/`，由 `scripts/generate_test_logs.py` 生成：

```bash
python scripts/generate_test_logs.py --output tests/fixtures/logs/
```

### 测试报告

详细的测试分析报告请参阅：[docs/test-analysis-report.md](docs/test-analysis-report.md)