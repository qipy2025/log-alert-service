#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书消息撤回助手
撤回刚才发送的错误消息
"""

import json
import os
import sys
import time
import requests
from dotenv import load_dotenv

# 设置Windows下的编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class FeishuMessageRecall:
    """飞书消息撤回助手"""

    def __init__(self):
        load_dotenv()
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.target_chat_id = "oc_e0dadc6e5ab606ff14ceb6f1150ee418"
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

    def get_recent_messages(self, limit=10):
        """获取最近的消息列表"""
        print(f"🔍 获取最近的消息...")
        url = f"{self.base_url}/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept-Language": "zh-CN"
        }
        params = {
            "container_id_type": "chat_id",
            "container_id": self.target_chat_id,
            "page_size": limit
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data.get("code") != 0:
            print(f"❌ 获取消息失败: {data}")
            print(f"提示：尝试使用不同的API端点...")
            # 尝试备用方法
            return self._get_messages_alt(limit)

        messages = data.get("data", {}).get("items", [])
        print(f"✅ 找到 {len(messages)} 条最近消息")
        return messages

    def _get_messages_alt(self, limit=10):
        """备用方法：获取消息列表"""
        print(f"🔄 使用备用方法获取消息...")
        url = f"{self.base_url}/im/v1/messages/{self.target_chat_id}/list"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept-Language": "zh-CN",
            "Content-Type": "application/json"
        }
        params = {
            "page_size": limit
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data.get("code") != 0:
            print(f"❌ 备用方法也失败了: {data}")
            return []

        messages = data.get("data", {}).get("items", [])
        return messages

    def recall_message(self, message_id):
        """撤回指定消息"""
        print(f"📤 正在撤回消息: {message_id}")
        url = f"{self.base_url}/im/v1/messages/{message_id}/recall"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept-Language": "zh-CN"
        }

        response = requests.post(url, headers=headers)
        data = response.json()

        if data.get("code") != 0:
            print(f"❌ 撤回失败: {data}")
            return False

        print("✅ 消息撤回成功！")
        return True

    def find_and_recall_recent_message(self, keyword="周报"):
        """查找并撤回最近的周报相关消息"""
        # 获取最近消息
        messages = self.get_recent_messages(15)

        if not messages:
            print("❌ 没有找到消息")
            return False

        # 查找包含关键词的消息
        for msg in messages:
            msg_content = msg.get("body", {}).get("content", "")
            try:
                content_dict = json.loads(msg_content)
                text_content = str(content_dict)
            except:
                text_content = msg_content

            if keyword in text_content or "周五打卡" in text_content:
                print(f"🎯 找到目标消息: {msg.get('msg_id')}")
                print(f"   消息内容预览: {text_content[:50]}...")

                # 询问是否撤回
                print(f"\n是否撤回这条消息？(y/n)")
                try:
                    choice = input().strip().lower()
                    if choice == 'y':
                        return self.recall_message(msg.get('msg_id'))
                    else:
                        print("❌ 取消撤回")
                        return False
                except EOFError:
                    # 非交互模式，自动撤回
                    print("⚠️  非交互模式，自动撤回消息")
                    return self.recall_message(msg.get('msg_id'))

        print("❌ 没有找到包含关键词的消息")
        return False

    def run(self):
        """运行撤回流程"""
        print("🤖 飞书消息撤回助手")
        print("="*50)

        try:
            # 1. 获取token
            self.get_tenant_token()

            # 2. 查找并撤回最近的周报消息
            self.find_and_recall_recent_message("周报")

        except Exception as e:
            print(f"\n❌ 撤回过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False

        return True


def main():
    recall = FeishuMessageRecall()
    success = recall.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
