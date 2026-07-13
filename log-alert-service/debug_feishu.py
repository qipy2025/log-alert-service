#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""飞书API调试脚本"""

import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加载父目录的.env文件
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

import requests
import json

def test_feishu_api():
    """测试飞书API连接和权限"""

    print("=" * 80)
    print("飞书API调试")
    print("=" * 80)

    # 从配置读取
    from src.config_manager import ConfigManager
    config = ConfigManager('config.yaml')
    feishu_config = config.get('feishu', {})

    app_id = feishu_config.get('app_id', '')
    app_secret = feishu_config.get('app_secret', '')
    chats = feishu_config.get('chats', [])

    print(f"\n📱 App ID: {app_id}")
    print(f"🔑 App Secret: {app_secret[:20]}...")
    print(f"👥 配置的群聊数: {len(chats)}")

    # 1. 测试获取tenant_access_token
    print("\n" + "-" * 80)
    print("步骤1: 获取访问令牌")
    print("-" * 80)

    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

    token_payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }

    try:
        resp = requests.post(token_url, json=token_payload, timeout=10)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")

        if resp.status_code != 200:
            print("❌ 获取token失败")
            return False

        result = resp.json()
        if result.get("code") != 0:
            print(f"❌ API返回错误: {result.get('msg')}")
            return False

        tenant_access_token = result.get("tenant_access_token")
        print(f"✅ 获取token成功: {tenant_access_token[:20]}...")

    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

    # 2. 测试发送消息到每个群聊
    print("\n" + "-" * 80)
    print("步骤2: 测试发送消息到各个群聊")
    print("-" * 80)

    message_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

    for chat in chats:
        chat_id = chat.get('chat_id', '')
        chat_name = chat.get('name', '未知')
        chat_type = chat.get('type', '未知')

        print(f"\n测试群聊: {chat_name} (类型: {chat_type})")
        print(f"Chat ID: {chat_id}")

        # 构造简单的文本消息
        message_payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": "飞书API测试消息"}, ensure_ascii=False)
        }

        try:
            headers = {
                "Authorization": f"Bearer {tenant_access_token}",
                "Content-Type": "application/json"
            }

            resp = requests.post(message_url, headers=headers, json=message_payload, timeout=10)
            print(f"状态码: {resp.status_code}")

            result = resp.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

            if resp.status_code == 200 and result.get("code") == 0:
                print("✅ 发送成功")
            else:
                print(f"❌ 发送失败: code={result.get('code')}, msg={result.get('msg')}")

        except Exception as e:
            print(f"❌ 请求异常: {e}")

    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_feishu_api()
