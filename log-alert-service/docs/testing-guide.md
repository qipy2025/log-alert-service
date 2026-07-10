# 测试指南

## 测试环境

测试使用独立的配置文件 `config.test.yaml` 和环境变量 `.env.test`。

## 测试数据

测试日志文件由 `scripts/generate_test_logs.py` 生成：

```bash
python scripts/generate_test_logs.py --output tests/fixtures/logs/
```

生成的测试文件：
- normal_alarms.log - 正常告警日志
- boundary_large.log - 大文件测试（0.8MB+）
- boundary_concurrent.log - 并发告警场景
- boundary_encoding.log - 特殊字符编码
- boundary_date_change.log - 日期切换场景

## Mock 对象

Mock 对象定义在 `tests/mocks.py`，包括：
- **MockFeishuAPI**：飞书 API mock
  - success_response() - 成功响应
  - error_response() - 错误响应
  - token_response() - Token 响应
  
- **MockAIAnalyzer**：AI 分析器 mock
  - success_response() - 成功分析结果
  - timeout_response() - 超时异常
  - error_response() - API 错误

- **MockFileSystem**：文件系统 mock
  - create_temp_log_file() - 创建临时日志文件
  - create_default_log() - 创建 Default.log 文件

## 集成测试

集成测试位于 `tests/integration/`，覆盖：

### 完整告警流程（test_alarm_workflow.py）
- test_1_1_normal_alarm_flow - 正常告警流程
- test_1_2_alarm_deduplication - 告警去重验证
- test_1_3_alarm_window_reset - 告警窗口重置

### 边界场景（test_boundary_scenarios.py）
- test_2_1_large_log_file - 大日志文件处理
- test_2_2_concurrent_alarms - 并发告警处理
- test_2_3_special_characters_encoding - 特殊字符和编码
- test_2_4_date_change_scenario - 日期切换场景

### 异常恢复（test_error_recovery.py）
- test_3_1_network_error_recovery - 网络故障恢复
- test_3_2_ai_analysis_failure_graceful_degradation - AI分析失败降级
- test_3_3_missing_log_file_handling - 日志文件缺失处理
- test_3_4_config_file_errors - 配置文件错误

### 每日汇总（test_daily_report.py）
- test_4_1_daily_summary_trigger - 每日汇总触发
- test_4_2_empty_day_summary - 空日汇总

## 持续集成

TODO：配置 CI/CD 流程

## Python 环境说明

如果 Python 不在 PATH 中，使用完整路径：
```bash
C:\Users\UID05478\AppData\Local\Programs\Python\Python312\python.exe -m pytest -v
```

或添加到 PATH：
```bash
set PATH=%PATH%;C:\Users\UID05478\AppData\Local\Programs\Python\Python312;C:\Users\UID05478\AppData\Local\Programs\Python\Python312\Scripts
```