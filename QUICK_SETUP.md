# 🚀 飞书周报提醒 - 快速配置

## ⚡ 3分钟快速配置

### 1️⃣ 登录飞书开放平台
```
https://open.feishu.cn/admin
```

### 2️⃣ 找到你的应用
```
App ID: cli_a95710cbf179dcbb
```

### 3️⃣ 创建定时任务
路径：应用 → 自动化/消息推送 → 创建定时任务

**配置信息：**
- ⏰ **时间**：每周五 09:30
- 🎯 **目标**：AI中台干活群
- 📝 **消息**：复制下方模板

## 📋 消息模板（复制即用）

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
        "tag": "lark_md",
        "content": "**亲爱的同学们，又到了一周一度的周报时间啦！** 🎉\n\n**✨ 本周有哪些收获和感悟？**\n**💡 遇到了什么有趣的问题？**\n**🎯 下周有什么计划？**\n\n请还未填写周报的小伙伴们抽空填写一下，让我们一起分享你的精彩瞬间！"
      }
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {"content": "📝 点击填写周报", "tag": "plain_text"},
          "type": "default",
          "url": "https://your-company.feishu.cn/wiki/weekly-report"
        }
      ]
    },
    {"tag": "hr"},
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**大家辛苦了，周末愉快！** 🎈"
      }
    },
    {
      "tag": "note",
      "elements": [
        {"content": "AI中台干活群 · 周报提醒机器人 🤖", "tag": "plain_text"}
      ]
    }
  ]
}
```

## ⚠️ 重要：替换周报链接

在模板中找到这行，替换为你的实际周报链接：
```json
"url": "https://your-company.feishu.cn/wiki/weekly-report"
```

## ✅ 完成！

1. 保存配置
2. 启用定时任务
3. 等待周五 9:30 自动发送 🎉

---

**详细步骤**：查看 [feishu-setup-step-by-step.md](feishu-setup-step-by-step.md)
