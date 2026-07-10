# 设备日志 AI 告警推送系统 - 测试设计方案

**项目名称**：log-alert-service 测试验证
**创建日期**：2026-07-09
**设计类型**：场景化集成测试方案

## 1. 项目概述

### 1.1 项目背景
log-alert-service 是一个实时监控点胶设备上位机日志的告警推送系统，检测告警并通过飞书推送通知（含 AI 分析建议）。

### 1.2 测试目标
验证现有测试是否完整，通过场景化测试覆盖真实使用场景、边界条件和异常情况，形成详细的测试验证报告。

### 1.3 测试策略
采用**增强型场景测试**方案：在现有单元测试基础上，增加端到端场景测试，覆盖真实业务流程。

## 2. 测试架构

### 2.1 目录结构
```
tests/
├── unit/              # 单元测试（保留现有）
│   ├── test_config_manager.py
│   ├── test_alarm_dedup.py
│   ├── test_log_parser.py
│   ├── test_context_collector.py
│   ├── test_ai_analyzer.py
│   ├── test_feishu_notifier.py
│   ├── test_file_watcher.py
│   └── test_daily_reporter.py
├── integration/       # 集成场景测试（新增）
│   ├── test_alarm_workflow.py      # 完整告警流程
│   ├── test_boundary_scenarios.py  # 边界场景
│   ├── test_error_recovery.py     # 异常恢复
│   └── test_daily_report.py       # 每日汇总
├── fixtures/          # 测试数据（新增）
│   ├── logs/          # 模拟日志文件
│   └── responses/     # 预期响应
└── conftest.py        # pytest 配置（新增）
```

### 2.2 测试执行策略
- 默认运行所有测试：`pytest`
- 只运行单元测试：`pytest tests/unit/`
- 只运行集成测试：`pytest tests/integration/`
- 生成覆盖率报告：`pytest --cov=src --cov-report=html`

### 2.3 测试环境隔离
- 使用独立的测试配置文件：`config.test.yaml`
- 测试专用的飞书群（避免污染生产环境）
- 模拟日志目录：`fixtures/logs/`

## 3. 测试场景设计

### 3.1 完整告警流程（test_alarm_workflow.py）

#### 场景 1.1：正常告警流程
**测试步骤**：
1. 写入包含报警的日志文件到监控目录
2. 等待文件监控检测到变化
3. 触发完整的告警处理流程

**验证点**：
- 文件监控检测到新文件
- 正确解析告警内容
- 去重检查通过（首次告警）
- AI 分析返回结果
- 飞书推送成功

**预期结果**：收到飞书通知，包含分析结果

#### 场景 1.2：告警去重验证
**测试步骤**：
1. 写入告警日志
2. 5 分钟内连续写入相同告警 3 次
3. 等待超过去重窗口（5 分钟）
4. 再次写入相同告警

**验证点**：
- 第 1 次推送成功
- 后续 3 次被去重，重复计数递增
- 超过窗口后再次推送成功

**预期结果**：收到 2 次通知，第 2 次显示重复次数为 3

#### 场景 1.3：告警窗口重置
**测试步骤**：
1. 写入告警 A
2. 等待 3 分钟
3. 写入告警 B（不同类型）
4. 再等待 3 分钟
5. 写入告警 A

**验证点**：
- 告警 A 的去重窗口独立计算
- 告警 B 不影响告警 A 的窗口
- 告警 A 窗口已过期，再次推送

**预期结果**：告警 A 收到 2 次通知，告警 B 收到 1 次

### 3.2 边界场景（test_boundary_scenarios.py）

#### 场景 2.1：大日志文件处理
**测试步骤**：
1. 准备 10MB 日志文件，包含 50 个告警
2. 将文件一次性写入监控目录
3. 监控解析过程

**验证点**：
- 文件被完整读取
- 所有告警被正确解析
- 无内存溢出或性能问题
- 解析时间在可接受范围内（< 30 秒）

**预期结果**：50 个告警全部被检测并推送

#### 场景 2.2：并发告警处理
**测试步骤**：
1. 模拟 3 个设备同时写入告警
2. 使用多线程或异步写入
3. 监控处理过程

**验证点**：
- 各设备告警独立处理
- 无相互干扰或数据混淆
- 去重机制正常工作

**预期结果**：所有设备的告警都被独立处理和推送

#### 场景 2.3：特殊字符和编码
**测试步骤**：
1. 准备包含特殊字符的日志：
   - Unicode 字符（emoji、中文、日文等）
   - 控制字符（换行、制表符等）
   - 特殊符号（$、&、%、# 等）
2. 写入监控目录

**验证点**：
- 正确解析各种字符编码
- 不抛出编码异常
- 飞书推送内容格式正确

**预期结果**：正确解析和推送，内容无乱码

#### 场景 2.4：日期切换场景
**测试步骤**：
1. 在 23:59:50 写入告警日志
2. 等待日期切换到 00:00:10
3. 写入新的告警日志
4. 检查监控目录和日志路径

**验证点**：
- 服务正常跨日期运行
- 监控目录自动切换到新日期
- 旧日期的告警仍能处理
- 新日期的日志正常监控

**预期结果**：服务持续工作，日志路径正确更新

### 3.3 异常恢复（test_error_recovery.py）

#### 场景 3.1：网络故障恢复
**测试步骤**：
1. 正常发送告警
2. 断开网络或模拟飞书 API 不可用
3. 发送新告警（应该失败）
4. 恢复网络
5. 验证重试机制

**验证点**：
- 网络故障时正确识别错误
- 重试机制正常工作
- 网络恢复后推送成功
- 无告警丢失

**预期结果**：网络恢复后，失败的告警重新推送成功

#### 场景 3.2：AI 分析失败降级
**测试步骤**：
1. 模拟 AI API 返回错误或超时
2. 发送告警
3. 验证降级处理

**验证点**：
- 捕获 AI 分析异常
- 降级为基础告警推送
- 不影响后续告警处理
- 飞书推送仍成功（但无 AI 分析）

**预期结果**：仍然推送飞书通知，标记为"AI 分析不可用"

#### 场景 3.3：日志文件缺失处理
**测试步骤**：
1. 配置监控一个不存在的目录
2. 启动服务

**验证点**：
- 启动失败，抛出明确异常
- 错误信息包含目录路径
- 不静默继续运行

**预期结果**：抛出 FileNotFoundError，包含明确的错误信息

#### 场景 3.4：配置文件错误
**测试步骤**：
1. 准备各种错误配置：
   - YAML 格式错误
   - 缺失必需字段
   - 环境变量未定义
   - 数据类型错误
2. 尝试加载配置

**验证点**：
- 正确识别各类配置错误
- 给出明确的错误信息（包含字段名和行号）
- 服务启动失败

**预期结果**：抛出明确的配置错误，不启动服务

### 3.4 每日汇总（test_daily_report.py）

#### 场景 4.1：每日汇总触发
**测试步骤**：
1. 当日发送 10 个不同类型的告警
2. 手动触发每日汇总任务
3. 检查飞书推送

**验证点**：
- 汇总包含所有告警统计
- 按类型分组正确
- 时间范围准确（当日 00:00-23:59）
- 飞书推送格式正确

**预期结果**：收到完整的飞书汇总报告

#### 场景 4.2：空日汇总
**测试步骤**：
1. 当日无告警发生
2. 触发每日汇总任务
3. 检查飞书推送

**验证点**：
- 正确处理空数据
- 推送"当日无告警"消息
- 不抛出异常

**预期结果**：收到"当日无告警"的通知

## 4. 测试数据和环境配置

### 4.1 测试数据结构

#### 4.1.1 日志样本（fixtures/logs/）

#### 日志文件格式规范
所有测试日志文件遵循以下格式：
- 编码：UTF-8-sig（带 BOM）
- 行分隔符：\n
- 时间戳格式：YYYY-MM-DD HH:mm:ss.SSS
- 告警标识：包含 `[ERROR]` 或 `[WARN]` 关键字

#### 测试数据文件清单
```
fixtures/logs/
├── normal_alarms.log          # 正常告警日志（50 行，3 个告警）
├── boundary_large.log         # 大文件测试（10MB+，1000 个告警）
├── boundary_concurrent.log    # 并发告警场景（模拟 3 个设备）
├── boundary_encoding.log      # 特殊字符编码（emoji、中文、日文）
├── boundary_date_change.log   # 日期切换场景（跨 23:59:59）
├── error_missing_file.log     # 文件缺失场景（用于验证错误处理）
└── recovery_network.log       # 网络恢复场景（连续告警测试）
```

#### 日志文件生成脚本
使用 `scripts/generate_test_logs.py` 生成测试数据：
```bash
python scripts/generate_test_logs.py --output tests/fixtures/logs/
```

#### 4.1.2 预期响应（fixtures/responses/）
```
fixtures/responses/
├── feishu_success.json        # 飞书成功响应
├── feishu_error.json          # 飞书错误响应
├── ai_analysis_result.json    # AI 分析示例
└── daily_report_template.json # 日报模板
```

### 4.2 测试配置文件

#### 4.2.1 config.test.yaml
```yaml
log_source:
  type: local
  path: "tests/fixtures/logs/"
  polling_interval: 1  # 加快测试
  encoding: utf-8-sig
  max_context_lines: 10  # 减少测试数据量
  functional_log_window: 3

feishu:
  app_id: "${FEISHU_TEST_APP_ID}"
  app_secret: "${FEISHU_TEST_APP_SECRET}"
  chats:
    - chat_id: "${FEISHU_TEST_CHAT_ID}"  # 测试专用群
      type: test
      name: "测试群"

ai_analysis:
  enabled: true  # 可以关闭以测试降级场景
  api_key: "${CLAUDE_API_KEY}"
  api_base_url: "${CLAUDE_API_BASE}"
  model: "deepseek-v4-flash-anthropic"
  max_tokens: 1024  # 减少测试成本
  temperature: 0.3

dedup:
  alarm_window: 10  # 缩短窗口以加速测试
  max_repeat_count: 3

daily_report:
  enabled: true
  schedule_time: "00:00"  # 测试时手动触发
```

#### 4.2.2 .env.test
```bash
# 测试环境凭证
FEISHU_TEST_APP_ID=your_test_app_id
FEISHU_TEST_APP_SECRET=your_test_secret
FEISHU_TEST_CHAT_ID=your_test_chat_id
CLAUDE_API_KEY=your_api_key
CLAUDE_API_BASE=http://model-api.desaysv.com
```

### 4.3 外部服务故障模拟

#### 4.3.1 网络故障模拟
使用 `pytest-mock` 模拟网络故障：
```python
from unittest.mock import patch
import requests

def test_network_error():
    """测试网络故障时的处理"""
    with patch('requests.post') as mock_post:
        # 模拟连接超时
        mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        # 发送告警
        # 验证错误处理
```

#### 4.3.2 API 错误模拟
模拟各种 API 错误响应：
```python
def test_api_timeout():
    """测试 API 超时"""
    with patch('src.ai_analyzer.requests.post') as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        # 验证降级处理

def test_api_rate_limit():
    """测试 API 限流"""
    with patch('src.ai_analyzer.requests.post') as mock_post:
        mock_post.return_value.status_code = 429
        # 验证重试机制
```

#### 4.3.3 Mock 配置文件
创建 `tests/mocks.py` 统一管理 mock 对象：
```python
from unittest.mock import MagicMock, patch
import requests

class MockFeishuAPI:
    """飞书 API mock"""
    @staticmethod
    def success_response():
        return MagicMock(status_code=200, json=lambda: {"code": 0})

    @staticmethod
    def error_response():
        return MagicMock(status_code=500, json=lambda: {"code": 999, "msg": "Internal error"})

class MockAIAnalyzer:
    """AI 分析器 mock"""
    @staticmethod
    def success_response():
        return {"root_cause": "测试原因", "suggestion": "测试建议"}

    @staticmethod
    def timeout_response():
        raise requests.exceptions.Timeout("AI API timeout")
```

### 4.4 pytest 配置（conftest.py）

```python
import pytest
import os
from pathlib import Path

# 设置测试环境
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """测试环境初始化"""
    os.environ["ENV"] = "test"
    # 加载测试环境变量
    from dotenv import load_dotenv
    load_dotenv(".env.test")

@pytest.fixture
def test_config():
    """提供测试配置"""
    return "config.test.yaml"

@pytest.fixture
def temp_log_dir(tmp_path):
    """临时日志目录"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir

@pytest.fixture
def mock_feishu_success():
    """飞书 API 成功响应"""
    with patch('src.feishu_notifier.requests.post') as mock:
        mock.return_value = MagicMock(status_code=200, json=lambda: {"code": 0})
        yield mock

@pytest.fixture
def mock_ai_timeout():
    """AI API 超时响应"""
    with patch('src.ai_analyzer.requests.post') as mock:
        mock.side_effect = requests.exceptions.Timeout("Timeout")
        yield mock
```

## 5. 测试报告模板

### 5.1 报告结构

```markdown
# 测试验证报告
生成时间：YYYY-MM-DD HH:mm:ss

## 执行摘要

- 测试覆盖：✓ 覆盖 8 个核心场景，共 24 个测试用例
- 通过率：23/24 (95.8%)
- 失败用例：1 个
- 执行时间：2分35秒

## 测试覆盖矩阵

| 场景分类 | 场景数 | 通过 | 失败 | 跳过 |
|---------|-------|------|------|------|
| 完整告警流程 | 3 | 3 | 0 | 0 |
| 边界场景 | 4 | 4 | 0 | 0 |
| 异常恢复 | 4 | 3 | 1 | 0 |
| 每日汇总 | 2 | 2 | 0 | 0 |
| 单元测试 | 11 | 11 | 0 | 0 |

## 详细测试结果

### 完整告警流程 ✓
- ✓ 正常告警流程 (0.8s)
- ✓ 告警去重验证 (5.2s)
- ✓ 告警窗口重置 (10.5s)

### 边界场景 ✓
- ✓ 大日志文件处理 (15.3s)
- ✓ 并发告警处理 (8.1s)
- ✓ 特殊字符和编码 (2.2s)
- ✓ 日期切换场景 (12.4s)

### 异常恢复 ⚠️
- ✓ 网络故障恢复 (18.5s)
- ✗ AI分析失败降级 (3.2s) - 失败原因：未正确降级
- ✓ 日志文件缺失处理 (1.1s)
- ✓ 配置文件错误 (0.9s)

### 每日汇总 ✓
- ✓ 每日汇总触发 (5.5s)
- ✓ 空日汇总 (4.8s)

## 发现的问题

### Important
1. **AI分析失败时未降级推送基础告警**
   - 位置：src/ai_analyzer.py:45
   - 问题：AI API 异常时直接返回 None，导致推送被跳过
   - 影响：AI服务故障时所有告警静默丢失
   - 修复建议：捕获异常后返回基础分析结果

### Minor
1. **日志文件编码错误时提示不清晰**
   - 位置：src/log_parser.py:28
   - 问题：编码错误时只打印日志，未给出明确错误
   - 影响：排查问题时定位困难
   - 修复建议：抛出明确异常，包含文件路径和编码信息

## 代码覆盖率

| 模块 | 语句覆盖 | 分支覆盖 | 行覆盖 |
|------|---------|---------|--------|
| config_manager.py | 92% | 85% | 92% |
| log_parser.py | 88% | 75% | 88% |
| alarm_dedup.py | 95% | 90% | 95% |
| ai_analyzer.py | 78% | 60% | 78% |
| feishu_notifier.py | 85% | 70% | 85% |
| 总体 | 87% | 76% | 87% |

## 改进建议

1. **立即修复**：AI分析失败降级逻辑
2. **本周内**：提升 ai_analyzer.py 覆盖率到 85%+
3. **下个迭代**：添加性能监控和日志
4. **持续改进**：集成到 CI/CD 流程

## 下一步计划

- [ ] 修复 AI 降级问题
- [ ] 补充 ai_analyzer 异常场景测试
- [ ] 添加自动化测试脚本
- [ ] 配置 CI/CD 集成
```

### 5.2 验证标准

| 验证项 | 通过标准 | 实际结果 |
|-------|---------|---------|
| 核心场景覆盖 | ≥ 8 个场景 | 待验证 |
| 测试通过率 | ≥ 90% | 待验证 |
| 代码覆盖率 | ≥ 80% | 待验证 |
| Critical 问题 | 0 个 | 待验证 |
| Important 问题 | ≤ 2 个 | 待验证 |
| 报告完整性 | 所有章节完整 | 待验证 |

## 6. 实施计划

### 6.1 阶段一：环境准备（预计 1 小时）
**任务清单**：
- [ ] 创建测试目录结构（5 分钟）
  - `tests/integration/` 目录
  - `tests/fixtures/logs/` 目录
  - `tests/fixtures/responses/` 目录
- [ ] 创建日志数据生成脚本（20 分钟）
  - `scripts/generate_test_logs.py`
  - 生成各种场景的测试日志
- [ ] 配置测试环境（10 分钟）
  - 创建 `config.test.yaml`
  - 配置 `.env.test`
- [ ] 设置 pytest 配置（15 分钟）
  - 创建 `conftest.py`
  - 配置覆盖率工具
- [ ] 准备 mock 对象（10 分钟）
  - 创建 `tests/mocks.py`
  - 定义各种 mock 响应

**验证标准**：
- 目录结构完整
- 能成功运行 `pytest --collect-only`
- 环境变量正确加载

### 6.2 阶段二：集成测试开发（预计 4 小时）
**任务清单**：
- [ ] 实现 test_alarm_workflow.py（60 分钟）
  - 场景 1.1：正常告警流程（20 分钟）
  - 场景 1.2：告警去重验证（20 分钟）
  - 场景 1.3：告警窗口重置（20 分钟）
- [ ] 实现 test_boundary_scenarios.py（90 分钟）
  - 场景 2.1：大日志文件处理（30 分钟）
  - 场景 2.2：并发告警处理（25 分钟）
  - 场景 2.3：特殊字符和编码（20 分钟）
  - 场景 2.4：日期切换场景（15 分钟）
- [ ] 实现 test_error_recovery.py（75 分钟）
  - 场景 3.1：网络故障恢复（25 分钟）
  - 场景 3.2：AI 分析失败降级（20 分钟）
  - 场景 3.3：日志文件缺失处理（15 分钟）
  - 场景 3.4：配置文件错误（15 分钟）
- [ ] 实现 test_daily_report.py（30 分钟）
  - 场景 4.1：每日汇总触发（20 分钟）
  - 场景 4.2：空日汇总（10 分钟）
- [ ] 添加测试标记和分类（15 分钟）

**验证标准**：
- 每个测试文件能独立运行
- 测试覆盖率 > 0
- 测试命名规范清晰

### 6.3 阶段三：测试执行和报告（预计 2 小时）
**任务清单**：
- [ ] 首次运行所有测试（20 分钟）
  - 运行 `pytest -v`
  - 记录失败用例
- [ ] 生成覆盖率报告（15 分钟）
  - 运行 `pytest --cov=src --cov-report=html`
  - 分析覆盖率数据
- [ ] 执行性能基准测试（25 分钟）
  - 记录每个测试的执行时间
  - 识别性能瓶颈
- [ ] 分析测试结果（30 分钟）
  - 汇总测试结果
  - 分析失败原因
  - 识别潜在问题
- [ ] 生成测试报告（30 分钟）
  - 填写测试报告模板
  - 按严重程度分类问题
  - 提供改进建议

**验证标准**：
- 所有测试都能运行（即使有失败）
- 覆盖率报告生成成功
- 测试报告包含所有必需章节

### 6.4 阶段四：问题修复和验证（预计 3 小时）
**任务清单**：
- [ ] 修复 Critical 问题（如有）
  - 定位问题根因
  - 实现修复
  - 单独验证修复
- [ ] 修复 Important 问题（预计 1 小时）
  - 逐个修复
  - 验证修复效果
- [ ] 优化 Minor 问题（预计 30 分钟）
  - 代码风格调整
  - 性能优化
- [ ] 重新运行完整测试（30 分钟）
  - 验证所有修复
  - 确认无回归
- [ ] 更新测试报告（30 分钟）
  - 更新测试结果
  - 标记已修复问题
- [ ] 文档归档（30 分钟）
  - 提交测试代码
  - 归档测试报告
  - 更新项目文档

**验证标准**：
- 所有问题已修复或文档化
- 测试通过率 ≥ 90%
- 代码覆盖率 ≥ 80%
- 无 Critical 问题

**总预计时间**：10 小时（分布：1 + 4 + 2 + 3）

**关键里程碑**：
- 里程碑 1（1 小时）：测试环境就绪，能运行测试
- 里程碑 2（5 小时）：所有集成测试用例完成
- 里程碑 3（7 小时）：首次完整测试报告生成
- 里程碑 4（10 小时）：所有问题修复，测试验证完成

## 7. 风险和依赖

### 7.1 风险
- **外部服务稳定性**：依赖飞书 API 和 AI API 的稳定性
- **测试数据准备**：部分测试数据需要精心准备
- **执行时间**：集成测试执行时间较长，可能影响开发效率

### 7.2 依赖
- 需要有效的飞书测试群配置
- 需要可访问的 AI API 凭证
- 需要能够写入日志的测试环境

## 8. 成功标准

测试验证成功需满足：
1. 所有 8 个核心场景都有对应的测试用例
2. 测试通过率 ≥ 90%
3. 代码覆盖率 ≥ 80%
4. 无 Critical 级别问题
5. Important 级别问题 ≤ 2 个
6. 生成完整的测试验证报告

---

**文档状态**：待用户审查
**下一步**：调用 writing-plans 技能创建实施计划
