# 飞书周报提醒机器人 🤖

## 功能说明

每周五上午 9:30 自动在飞书群发送周报填写提醒，支持两种活泼的消息风格。

## 快速开始

### 1. 环境准备

确保你的环境已安装 Python 3.8+ 和必要的依赖包：

```bash
# 安装依赖（如果尚未安装）
pip install python-dotenv requests
```

### 2. 配置环境变量

编辑项目根目录的 `.env` 文件，确保以下配置正确：

```env
# 飞书应用凭证
FEISHU_APP_ID=cli_a95710cbf179dcbb
FEISHU_APP_SECRET=REMOVED

# 周报提醒配置
WEEKLY_REPORT_URL=https://your-company.feishu.cn/wiki/weekly-report  # 替换为实际的周报链接
FEISHU_CHAT_ID=oc_e0dadc6e5ab606ff14ceb6f1150ee418  # 目标群聊 ID
```

### 3. 测试运行

```bash
# 在项目根目录运行
python weekly_report_reminder.py
```

如果配置正确，你应该会在目标飞书群收到周报提醒消息。

## 定时任务配置

### 方法一：使用 Claude Code 定时任务（推荐）

定时任务已自动配置完成！每周五上午 9:30 会自动运行提醒脚本。

查看和管理定时任务：
```bash
# 查看所有定时任务
/cron list

# 停止定时任务（如需要）
/cron delete a6e53cd2
```

### 方法二：使用 Windows 任务计划程序

如果需要更可靠的定时执行，可以配置 Windows 任务计划程序：

1. 打开"任务计划程序"（Task Scheduler）
2. 创建基本任务
3. 设置触发器：每周五 上午 9:30
4. 设置操作：运行程序
   - 程序：`python.exe` 的完整路径
   - 参数：`d:\code\LOG\weekly_report_reminder.py`
   - 起始于：`d:\code\LOG`

### 方法三：使用 Linux Cron

如果在 Linux 环境运行：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每周五 9:30 运行）
30 9 * * 5 cd /path/to/LOG && /usr/bin/python3 weekly_report_reminder.py >> weekly_report.log 2>&1
```

## 消息样式

机器人会随机发送两种风格的提醒消息：

### 样式一：轻松愉快型 🎉
```
📢 周五打卡时间到！

亲爱的同学们，又到了一周一度的周报时间啦！

✨ 本周有哪些收获和感悟？
💡 遇到了什么有趣的问题？
🎯 下周有什么计划？

[填写周报按钮]

大家辛苦了，周末愉快！🎈
```

### 样式二：温馨提醒型 ☕
```
☕ 周五早晨，周报提醒

Hi 各位小伙伴，

周五啦！这周过得怎么样？

在开启美好周末之前，别忘了填写本周周报哦：
• 记录本周工作成果 ✅
• 分享遇到的问题 💭
• 规划下周任务 🚀

[周报传送门按钮]

感谢你的用心分享，祝周末愉快！🌻
```

## 自定义配置

### 修改周报链接

编辑 `.env` 文件中的 `WEEKLY_REPORT_URL` 变量。

### 修改目标群聊

1. 获取群聊 ID：
   - 在飞书群中发送一条消息
   - 访问飞书开放平台的消息接收测试
   - 或使用机器人调试工具获取 chat_id

2. 修改 `.env` 中的 `FEISHU_CHAT_ID`

### 修改消息时间

编辑定时任务的 cron 表达式：
- 当前：`30 9 * * 5`（每周五 9:30）
- 格式：`分钟 小时 * * 星期`

### 自定义消息内容

编辑 `weekly_report_reminder.py` 中的以下方法：
- `_build_reminder_card()` - 样式一
- `_build_reminder_card_v2()` - 样式二

## 故障排除

### 问题 1：发送失败，提示 token 错误
**解决方案**：
- 检查 `.env` 中的 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 是否正确
- 确认飞书应用权限已启用消息发送功能

### 问题 2：消息没有发送到目标群
**解决方案**：
- 验证 `FEISHU_CHAT_ID` 是否正确
- 确认机器人已被添加到目标群聊
- 检查机器人是否有发送消息权限

### 问题 3：定时任务没有执行
**解决方案**：
- 检查 Python 环境是否正确配置
- 查看任务日志：`weekly_report.log`
- 手动运行脚本测试：`python weekly_report_reminder.py`

## 项目文件说明

```
d:\code\LOG\
├── weekly_report_reminder.py    # 周报提醒主脚本
├── .env                         # 环境变量配置
├── .claude/
│   └── scheduled_tasks.json     # Claude Code 定时任务配置
└── docs/
    └── weekly-report-reminder.md  # 本文档
```

## 相关文档

- [飞书开放平台文档](https://open.feishu.cn/document)
- [飞书机器人开发指南](https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjLU1zN)
- [Claude Code 定时任务](https://docs.claude-code.com)

## 维护建议

1. **定期检查**：每月检查一次机器人是否正常工作
2. **消息更新**：可以定期更新消息样式，保持新鲜感
3. **权限监控**：确保飞书应用权限一直有效
4. **日志备份**：保留运行日志，便于问题排查

---

**创建时间**：2026-07-10  
**维护者**：AI中台团队  
**版本**：v1.0.0
