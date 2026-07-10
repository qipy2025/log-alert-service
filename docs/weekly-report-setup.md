# 📢 周报提醒配置（AI中台干活群专用）

## 🎯 功能说明
- **用途**：每周五上午9:30提醒团队成员填写周报
- **目标群**：AI中台干活群
- **触发时间**：每周五 09:30

---

## 📋 配置信息

| 项目 | 值 |
|------|------|
| **应用 ID** | `cli_a95710cbf179dcbb` |
| **目标群名** | `AI中台干活群` |
| **目标群ID** | `oc_0f39ea380ad7d1c9df681468f2d86d8e` |
| **提醒时间** | 每周五 09:30 |
| **周报链接** | `https://yesv-desaysv.feishu.cn/base/GQUrbRoOWa87yjsDp27cVIJmnYd?table=blkGTPs6HlmAWo62` |

---

## 🚀 配置步骤

### 1. 登录飞书开放平台
访问：https://open.feishu.cn/admin

### 2. 找到应用
应用ID：`cli_a95710cbf179dcbb`

### 3. 创建周报提醒定时任务

进入应用 → **「自动化」** → **「创建自动化」**

**触发条件：**
- **触发类型**：`定时触发`
- **执行时间**：`每周五 09:30`
- **时区**：`Asia/Shanghai (GMT+8)`

**执行动作：**
- **动作类型**：`发送群消息`
- **目标群组**：`AI中台干活群`
- **群ID**：`oc_0f39ea380ad7d1c9df681468f2d86d8e`
- **消息类型**：`卡片消息`

### 4. 粘贴消息模板

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "title": {
      "content": "📢 周五打卡时间到！",
      "tag": "plain_text"
    },
    "template": "turquoise"
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "content": "**亲爱的同学们，又到了一周一度的周报时间啦！** 🎉\n\n**✨ 本周有哪些收获和感悟？**\n**💡 遇到了什么有趣的问题？**\n**🎯 下周有什么计划？**\n\n请还未填写周报的小伙伴们抽空填写一下，让我们一起分享你的精彩瞬间！",
        "tag": "lark_md"
      }
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "content": "📝 点击填写周报",
            "tag": "plain_text"
          },
          "type": "default",
          "url": "https://yesv-desaysv.feishu.cn/base/GQUrbRoOWa87yjsDp27cVIJmnYd?table=blkGTPs6HlmAWo62"
        }
      ]
    },
    {
      "tag": "hr"
    },
    {
      "tag": "div",
      "text": {
        "content": "**大家辛苦了，周末愉快！** 🎈",
        "tag": "lark_md"
      }
    },
    {
      "tag": "note",
      "elements": [
        {
          "content": "AI中台干活群 · 周报提醒机器人 🤖",
          "tag": "plain_text"
        }
      ]
    }
  ]
}
```

### 5. 保存并启用
点击「保存」→ 确认任务状态为「已启用」

---

## ✅ 配置验证清单

- [ ] 目标群聊：AI中台干活群
- [ ] 群ID：oc_0f39ea380ad7d1c9df681468f2d86d8e
- [ ] 执行时间：每周五 09:30
- [ ] 周报链接：已配置正确链接
- [ ] 消息模板：已粘贴
- [ ] 任务状态：已启用

---

## 🎊 配置完成效果

- ✅ 每周五 9:30 自动发送到 **AI中台干活群**
- ✅ 包含一键填写周报按钮
- ✅ 活泼有趣的消息风格
- ✅ 完全独立，不影响日志分析功能

---

**配置完成时间**：2026-07-10
**下次提醒**：本周五 9:30 AM
**目标群组**：AI中台干活群（专用）

🚀 **周报提醒功能独立配置完成！**
