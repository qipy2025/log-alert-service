#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送包含正确周报链接的最终测试消息
"""

import json
import os
import sys
import requests
from dotenv import load_dotenv

# 设置Windows下的编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def send_final_reminder():
    """发送包含正确周报链接的最终测试消息"""
    load_dotenv()

    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    target_chat_id = "oc_0f39ea380ad7d1c9df681468f2d86d8e"  # AI中台干活群
    weekly_report_url = "https://yesv-desaysv.feishu.cn/base/GQUrbRoOWa87yjsDp27cVIJmnYd?table=blkGTPs6HlmAWo62"

    print("🤖 发送最终周报提醒测试")
    print("="*60)
    print(f"目标群: AI中台干活群")
    print(f"群ID: {target_chat_id}")
    print(f"周报链接: {weekly_report_url}")
    print("-"*60)

    # 1. 获取token
    print("🔐 正在获取飞书 access token...")
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    response = requests.post(token_url, json={
        "app_id": app_id,
        "app_secret": app_secret
    })
    data = response.json()
    if data.get("code") != 0:
        print(f"❌ 获取 token 失败: {data}")
        return False

    token = data["tenant_access_token"]
    print("✅ Token 获取成功")

    # 2. 构建消息卡片（包含正确的周报链接）
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
                        "**✨ 本周有哪些收获和感悟？**\n"
                        "**💡 遇到了什么有趣的问题？**\n"
                        "**🎯 下周有什么计划？**\n\n"
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
                        "url": weekly_report_url,  # 使用正确的周报链接
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

    # 3. 发送消息
    print("📤 正在发送最终测试消息...")
    message_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "receive_id": target_chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False)
    }

    response = requests.post(message_url, headers=headers, json=payload)
    result = response.json()

    if result.get("code") != 0:
        print(f"❌ 发送失败: {result}")
        return False

    print("✅ 最终测试消息发送成功！")
    print("-"*60)
    print("请检查飞书群「AI中台干活群」:")
    print("1. 是否收到消息")
    print("2. 点击「📝 点击填写周报」按钮")
    print("3. 验证是否能正确跳转到周报页面")
    print("="*60)
    return True


if __name__ == "__main__":
    success = send_final_reminder()
    exit(0 if success else 1)
