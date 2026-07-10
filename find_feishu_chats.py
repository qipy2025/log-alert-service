#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书群聊查找助手
找到所有可用的群聊，找到"AI中台干活群"
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


class FeishuChatFinder:
    """飞书群聊查找助手"""

    def __init__(self):
        load_dotenv()
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
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

    def get_user_chats(self):
        """获取用户所在的群聊列表"""
        print("🔍 正在获取群聊列表...")
        url = f"{self.base_url}/im/v1/chats"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept-Language": "zh-CN"
        }
        params = {
            "page_size": 50
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data.get("code") != 0:
            print(f"❌ 获取群聊失败: {data}")
            return []

        chats = data.get("data", {}).get("items", [])
        print(f"✅ 找到 {len(chats)} 个群聊")
        return chats

    def find_target_chat(self, keyword="AI中台干活群"):
        """查找目标群聊"""
        print(f"🎯 正在查找包含'{keyword}'的群聊...")

        chats = self.get_user_chats()

        if not chats:
            print("❌ 没有找到任何群聊")
            return None

        matching_chats = []

        print(f"\n📋 所有群聊列表:")
        print("="*80)

        for i, chat in enumerate(chats, 1):
            chat_name = chat.get('name', 'Unknown')
            chat_id = chat.get('chat_id', 'Unknown')
            chat_description = chat.get('description', '')

            print(f"{i}. 群名: {chat_name}")
            print(f"   群ID: {chat_id}")
            print(f"   描述: {chat_description}")
            print("-"*80)

            # 查找包含关键词的群
            if keyword in chat_name:
                matching_chats.append({
                    'name': chat_name,
                    'chat_id': chat_id,
                    'description': chat_description
                })

        print(f"\n🎯 找到 {len(matching_chats)} 个匹配的群聊:")
        print("="*80)

        for i, chat in enumerate(matching_chats, 1):
            print(f"{i}. 群名: {chat['name']}")
            print(f"   群ID: {chat['chat_id']}")
            print(f"   描述: {chat['description']}")
            print()

        if matching_chats:
            print(f"✅ 找到目标群: {matching_chats[0]['name']}")
            print(f"   群ID: {matching_chats[0]['chat_id']}")
            return matching_chats[0]
        else:
            print(f"❌ 没有找到包含'{keyword}'的群聊")
            print(f"请检查群名是否正确，或者从上面的列表中选择合适的群")
            return None

    def run(self):
        """运行查找流程"""
        print("🤖 飞书群聊查找助手")
        print("="*80)

        try:
            # 1. 获取token
            self.get_tenant_token()

            # 2. 查找目标群
            target_chat = self.find_target_chat("AI中台干活群")

            if target_chat:
                print(f"\n🎉 找到目标群聊！")
                print(f"群名: {target_chat['name']}")
                print(f"群ID: {target_chat['chat_id']}")
                print(f"\n请将此群ID配置到你的应用中")
                return target_chat
            else:
                print(f"\n❌ 未找到目标群聊")
                return None

        except Exception as e:
            print(f"\n❌ 查找过程出错: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    finder = FeishuChatFinder()
    result = finder.run()
    return 0 if result else 1


if __name__ == "__main__":
    exit(main())
