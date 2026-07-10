# 🔧 日志分析告警配置（设备日志AI分析预警群专用）

## 🎯 功能说明
- **用途**：点胶设备日志实时监控和AI分析告警
- **目标群**：设备日志AI分析预警
- **触发方式**：实时监控日志文件，检测到告警立即推送

---

## 📋 配置信息

| 项目 | 值 |
|------|------|
| **应用 ID** | `cli_a95710cbf179dcbb` |
| **目标群名** | `设备日志AI分析预警` |
| **目标群ID** | `oc_e0dadc6e5ab606ff14ceb6f1150ee418` |
| **监控日志** | 点胶设备上位机日志 |
| **告警级别** | CRITICAL/WARNING/INFO |

---

## 🔧 现有配置

### 当前日志分析配置（log-alert-service）

**配置文件**：`log-alert-service/config.yaml`

```yaml
# 飞书配置（设备日志AI分析预警群专用）
feishu:
  app_id: "${FEISHU_APP_ID}"
  app_secret: "${FEISHU_APP_SECRET}"
  chats:
    - chat_id: oc_e0dadc6e5ab606ff14ceb6f1150ee418
      type: production
      name: "设备日志AI分析预警"
    - chat_id: oc_aa8f612241f26528a681db30bda7402e
      type: debug
      name: "日志分析测试"

# 日志源
log_source:
  type: windows_share
  path: "D:\\code\\LOG\\CD-ADS-1\\点胶设备\\上位机日志\\2026-06-08\\"
  use_direct_path: true
  polling_interval: 2

# AI 分析
ai_analysis:
  enabled: true
  api_key: "${CLAUDE_API_KEY}"
  api_base_url: "http://model-api.desaysv.com"
  model: "deepseek-v4-flash-anthropic"

# 每日汇总
daily_report:
  enabled: true
  schedule_time: "22:00"
```

---

## 🚀 日志分析功能

### 1. 实时告警推送
- 监控点胶设备日志
- 检测告警关键词
- 实时推送到 **设备日志AI分析预警群**

### 2. AI 智能分析
- 自动分析告警原因
- 提供处理建议
- 预估解决时间

### 3. 每日汇总报告
- 每天 22:00 自动发送
- 统计当日告警情况
- AI 生成日报总结

---

## 📊 告警消息样式

### 实时告警消息
```
┌─────────────────────────────────┐
│ 🔴 告警通知 - 点胶设备            │
├─────────────────────────────────┤
│ 告警时间：2026-07-10 14:30:25    │
│ 告警类型：🔴 CRITICAL            │
│ 告警内容：温度超过安全阈值         │
│ 模块：加热系统                    │
│ 当日已出现：3 次                  │
├─────────────────────────────────┤
│ 🧠 AI 分析                       │
│ 根本原因：温控传感器故障           │
│ 建议操作：立即停机检查传感器       │
│ 预计处理时间：30分钟              │
├─────────────────────────────────┤
│ 📋 日志参考                      │
│ [相关日志片段...]                │
├─────────────────────────────────┤
│ 点胶设备 · 日志AI分析预警系统 v0.1│
└─────────────────────────────────┘
```

### 每日汇总报告
```
┌─────────────────────────────────┐
│ 📊 点胶设备告警日报 - 2026-07-10 │
├─────────────────────────────────┤
│ 告警统计                         │
│ 告警总次数：12 次                │
│ 告警类型分布：                    │
│   CRITICAL：3 次                │
│   WARNING：7 次                 │
│   INFO：2 次                    │
│ 已复位未解决：1 次                │
├─────────────────────────────────┤
│ 🧠 今日总结                      │
│ [AI生成的日报总结...]            │
├─────────────────────────────────┤
│ 点胶设备 · 日志AI分析预警系统 v0.1│
└─────────────────────────────────┘
```

---

## 🔧 运行日志分析服务

### 启动服务
```bash
cd log-alert-service
python main.py config.yaml
```

### 测试功能
```bash
# 发送测试消息到设备日志AI分析预警群
python -c "from src.feishu_notifier import FeishuNotifier; from dotenv import load_dotenv; import os; load_dotenv(); notifier = FeishuNotifier(os.getenv('FEISHU_APP_ID'), os.getenv('FEISHU_APP_SECRET'), [{'chat_id': 'oc_e0dadc6e5ab606ff14ceb6f1150ee418', 'type': 'production'}]); notifier.send_test('oc_e0dadc6e5ab606ff14ceb6f1150ee418')"
```

---

## ✅ 配置验证清单

- [ ] 目标群聊：设备日志AI分析预警
- [ ] 群ID：oc_e0dadc6e5ab606ff14ceb6f1150ee418
- [ ] 日志监控：已启动
- [ ] AI分析：已启用
- [ ] 实时告警：已配置
- [ ] 每日汇总：已启用（22:00）
- [ ] 测试消息：已发送

---

## 🚨 与周报提醒的区别

| 功能 | 周报提醒 | 日志分析告警 |
|------|----------|--------------|
| **目标群** | AI中台干活群 | 设备日志AI分析预警 |
| **群ID** | oc_0f39ea380ad7d1c9df681468f2d86d8e | oc_e0dadc6e5ab606ff14ceb6f1150ee418 |
| **触发方式** | 定时（每周五 9:30） | 实时（日志监控） |
| **消息内容** | 周报填写提醒 | 设备告警通知 |
| **接收人员** | AI中台团队成员 | 设备运维人员 |
| **紧急程度** | 常规提醒 | 紧急告警 |

---

## 🎊 配置完成效果

- ✅ 实时监控设备日志，只发送到 **设备日志AI分析预警群**
- ✅ AI 智能分析告警原因
- ✅ 每日自动汇总报告
- ✅ 完全独立，不影响周报提醒功能

---

**配置状态**：已运行
**服务端口**：log-alert-service
**目标群组**：设备日志AI分析预警（专用）

🔧 **日志分析功能独立配置完成！**
