# 飞书周报提醒 - 原生配置方案 🎯

## 方案一：飞书开放平台后台配置（推荐）⭐

### 1. 登录飞书开放平台
访问：https://open.feishu.cn/admin

### 2. 找到你的自建应用
- 应用名称：你的飞书机器人应用
- App ID：cli_a95710cbf179dcbb（从项目 .env 中获取）

### 3. 配置定时消息

#### 方式 A：使用"自动化"功能
1. 进入应用 → **自动化** → **创建自动化**
2. 设置触发条件：
   - **触发类型**：定时触发
   - **执行时间**：每周五 9:30
   - **时区**：Asia/Shanghai
3. 设置执行动作：
   - **动作类型**：发送群消息
   - **目标群组**：AI中台干活群
   - **消息类型**：卡片消息
4. 配置消息内容（见下方消息模板）

#### 方式 B：使用"消息推送"功能
1. 进入应用 → **消息推送** → **定时推送**
2. 添加定时任务：
   - **任务名称**：周报提醒
   - **执行时间**：`30 9 * * 5`（每周五 9:30）
   - **推送目标**：选择 AI中台干活群
   - **消息内容**：粘贴下方消息模板

## 方案二：飞书群直接配置（最简单）🎉

### 1. 在目标群聊中
打开飞书 → AI中台干活群

### 2. 添加群机器人
1. 点击群设置 → **群机器人** → **添加机器人**
2. 选择你的自建应用机器人
3. 启用消息发送权限

### 3. 设置定时消息
1. 在群聊中输入 `/schedule` 或找到定时消息功能
2. 创建定时提醒：
   - **提醒内容**：使用下方消息模板
   - **提醒时间**：每周五 9:30
   - **重复周期**：每周重复

## 方案三：利用现有项目 + 飞书自动化API 🛠️

如果需要更复杂的逻辑，可以基于现有项目扩展：

### 1. 在现有 FeishuNotifier 中添加周报提醒方法

```python
# 在 log-alert-service/src/feishu_notifier.py 中添加

def send_weekly_report_reminder(self) -> bool:
    """发送周报提醒"""
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "📢 周五打卡时间到！"},
            "template": "turquoise",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        "**亲爱的同学们，又到了一周一度的周报时间啦！** 🎉\n\n"
                        "✨ **本周有哪些收获和感悟？**\n"
                        "💡 **遇到了什么有趣的问题？**\n"
                        "🎯 **下周有什么计划？**\n\n"
                        "请还未填写周报的小伙伴们抽空填写一下，"
                        "让我们一起分享你的精彩瞬间！"
                    ),
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 点击填写周报"},
                        "type": "default",
                        "url": "https://your-company.feishu.cn/wiki/weekly-report",
                    }
                ],
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**大家辛苦了，周末愉快！** 🎈"
                },
            },
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": "AI中台干活群 · 周报提醒机器人 🤖"}
                ],
            },
        ],
    }

    chat_ids = self._get_target_chats("production")
    all_ok = True
    for chat_id in chat_ids:
        ok = self._send_message(chat_id, card)
        if not ok:
            all_ok = False
    return all_ok
```

### 2. 在主服务中添加定时任务

```python
# 在 log-alert-service/main.py 的 start() 方法中添加

# 配置周报提醒定时任务
self.scheduler.add_job(
    lambda: self.notifier.send_weekly_report_reminder(),
    "cron",
    hour=9,
    minute=30,
    day_of_week=4,  # 周五（0=周一，6=周日）
    id="weekly_report_reminder",
)
logger.info("周报提醒定时任务已设定: 每周五 9:30")
```

## 🎨 消息模板（复制即用）

### 模板一：轻松愉快型
```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"content": "📢 周五打卡时间到！", "tag": "plain_text"},
    "template": "turquoise"
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "content": "**亲爱的同学们，又到了一周一度的周报时间啦！** 🎉\n\n✨ **本周有哪些收获和感悟？**\n💡 **遇到了什么有趣的问题？**\n🎯 **下周有什么计划？**",
        "tag": "lark_md"
      }
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {"content": "📝 点击填写周报", "tag": "plain_text"},
          "type": "default",
          "url": "https://your-link.com"
        }
      ]
    },
    {"tag": "hr"},
    {
      "tag": "div",
      "text": {
        "content": "**大家辛苦了，周末愉快！** 🎈",
        "tag": "lark_md"
      }
    }
  ]
}
```

### 模板二：简洁活泼型
```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"content": "🔔 叮！周五周报提醒", "tag": "plain_text"},
    "template": "green"
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "content": "**各位同学：**\n\n周五到了，请查收本周周报填写提醒～\n\n📝 **周报传送门**\n让我们一起回顾本周工作、总结经验教训、规划下周目标！",
        "tag": "lark_md"
      }
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {"content": "✅ 填写周报", "tag": "plain_text"},
          "type": "primary",
          "url": "https://your-link.com"
        }
      ]
    }
  ]
}
```

## 🚀 推荐方案排序

1. **飞书后台自动化功能**（5分钟搞定）⭐⭐⭐⭐⭐
2. **飞书群定时消息**（最简单）⭐⭐⭐⭐
3. **基于现有项目扩展**（适合复杂需求）⭐⭐⭐

## 📝 配置步骤总结

### 最快方案（飞书后台）：
1. 登录飞书开放平台
2. 找到你的应用
3. 进入自动化/消息推送
4. 创建定时任务：每周五 9:30
5. 粘贴消息模板
6. 完成！✅

---

**建议**：使用方案一（飞书开放平台后台配置），最简单直接，无需维护额外代码。
