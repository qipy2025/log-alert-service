#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书周报提醒配置助手
帮助配置飞书自动化/定时任务
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


class FeishuReminderSetup:
    """飞书提醒配置助手"""

    def __init__(self):
        # 加载环境变量
        load_dotenv()
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.target_chat_id = "oc_e0dadc6e5ab606ff14ceb6f1150ee418"  # AI中台干活群

        self.token = None
        self.base_url = "https://open.feishu.cn/open-apis"

    def get_tenant_token(self):
        """获取 tenant_access_token"""
        print("🔐 正在获取飞书 access token...")
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        response = requests.post(url, json={
            "app_id": self.app_id,
            "app_secret": self.app_secret
        })
        data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取 token 失败: {data}")

        self.token = data["tenant_access_token"]
        print("✅ Token 获取成功")
        return self.token

    def get_chat_info(self):
        """获取群聊信息"""
        print(f"🔍 获取目标群聊信息...")
        url = f"{self.base_url}/im/v1/chats/{self.target_chat_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, headers=headers)
        data = response.json()

        if data.get("code") != 0:
            print(f"⚠️  无法获取群聊信息: {data}")
            return None

        chat_info = data.get("data", {})
        print(f"✅ 找到群聊: {chat_info.get('name', 'Unknown')}")
        print(f"   群ID: {chat_info.get('chat_id')}")
        return chat_info

    def send_test_reminder(self):
        """发送测试周报提醒"""
        print("📤 发送测试周报提醒...")

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
                            "url": "https://example.com/weekly-report",  # 需要替换为实际链接
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

        url = f"{self.base_url}/im/v1/messages?receive_id_type=chat_id"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "receive_id": self.target_chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False)
        }

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if data.get("code") != 0:
            print(f"❌ 发送失败: {data}")
            return False

        print("✅ 测试消息发送成功！")
        print("   请检查飞书群是否收到消息")
        return True

    def get_app_info(self):
        """获取应用信息"""
        print("🔍 获取应用信息...")
        url = f"{self.base_url}/application/v6/applications/{self.app_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept-Language": "zh-CN"
        }
        response = requests.get(url, headers=headers)
        data = response.json()

        if data.get("code") != 0:
            print(f"⚠️  无法获取应用信息: {data}")
            return None

        app_info = data.get("data", {}).get("application", {})
        print(f"✅ 应用名称: {app_info.get('name', 'Unknown')}")
        print(f"   应用类型: {app_info.get('app_type', 'Unknown')}")
        return app_info

    def setup_automation(self):
        """尝试设置自动化任务"""
        print("\n🤖 尝试设置自动化任务...")

        # 注意：飞书的自动化API可能不对外开放，需要手动配置
        print("⚠️  飞书自动化任务需要在开放平台后台手动配置")
        print("   请访问: https://open.feishu.cn/admin")
        print(f"   应用ID: {self.app_id}")

    def generate_setup_guide(self):
        """生成配置指南"""
        print("\n" + "="*50)
        print("📋 飞书周报提醒配置指南")
        print("="*50)

        print("\n🎯 方式一：飞书开放平台后台配置（推荐）")
        print("-" * 50)
        print("1. 访问飞书开放平台: https://open.feishu.cn/admin")
        print(f"2. 找到应用: {self.app_id}")
        print("3. 选择以下任一方式:")
        print("   - 进入「自动化」→「创建自动化」")
        print("   - 进入「消息推送」→「定时推送」")
        print("4. 配置定时任务:")
        print("   - 执行时间: 每周五 9:30")
        print("   - 触发类型: 定时触发")
        print("   - 执行动作: 发送群消息")
        print(f"   - 目标群: {self.target_chat_id}")
        print("5. 粘贴消息模板 (见下方)")

        print("\n🎨 消息模板:")
        print("-" * 50)

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"content": "📢 周五打卡时间到！", "tag": "plain_text"},
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
                            "text": {"content": "📝 点击填写周报", "tag": "plain_text"},
                            "type": "default",
                            "url": "https://example.com/weekly-report"
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
                },
                {
                    "tag": "note",
                    "elements": [
                        {"content": "AI中台干活群 · 周报提醒机器人 🤖", "tag": "plain_text"}
                    ]
                }
            ]
        }

        print(json.dumps(card, indent=2, ensure_ascii=False))

        print("\n🎯 方式二：飞书群定时消息")
        print("-" * 50)
        print("1. 在飞书群「AI中台干活群」中")
        print("2. 点击群设置 → 群机器人 → 添加机器人")
        print("3. 设置定时消息:")
        print("   - 时间: 每周五 9:30")
        print("   - 内容: 使用上方消息模板")
        print("   - 重复: 每周")

        print("\n🚀 快速开始:")
        print("-" * 50)
        print("1. 现在发送一条测试消息验证配置")
        print("2. 确认消息在飞书群中显示正常")
        print("3. 在飞书后台设置定时任务")
        print("4. 完成！每周五自动发送提醒")

    def run(self, auto_send_test=False):
        """运行配置流程"""
        print("🤖 飞书周报提醒配置助手")
        print("="*50)

        try:
            # 1. 获取token
            self.get_tenant_token()

            # 2. 获取应用信息
            self.get_app_info()

            # 3. 获取群聊信息
            self.get_chat_info()

            # 4. 发送测试消息（自动发送）
            if auto_send_test:
                print("\n📤 自动发送测试消息...")
                self.send_test_reminder()
            else:
                print("\n是否发送测试消息？(y/n)")
                try:
                    choice = input().strip().lower()
                    if choice == 'y':
                        self.send_test_reminder()
                except EOFError:
                    print("⚠️  非交互模式，跳过测试消息发送")

            # 5. 生成配置指南
            self.generate_setup_guide()

        except Exception as e:
            print(f"\n❌ 配置过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False

        return True


def main():
    setup = FeishuReminderSetup()
    success = setup.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
