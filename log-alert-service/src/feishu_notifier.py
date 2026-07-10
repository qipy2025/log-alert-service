import json
import time
from typing import Any, Optional

import requests

from src.data_models import AlarmEvent, AlarmLevel, AnalysisResult, DailySummary


class FeishuNotifier:
    """飞书消息推送（自建应用方式）"""

    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        chats: list[dict],
        timeout: int = 10,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.chats = chats  # [{"chat_id": "...", "type": "debug|production", "name": "..."}]
        self.timeout = timeout
        self._token: Optional[str] = None
        self._token_expire: float = 0

    def _get_token(self) -> str:
        """获取 tenant_access_token（带缓存）"""
        if self._token and time.time() < self._token_expire - 60:
            return self._token

        resp = requests.post(
            self.TOKEN_URL,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get token: {data}")

        self._token = data["tenant_access_token"]
        self._token_expire = time.time() + data["expire"]
        return self._token

    def _send_message(self, chat_id: str, card: dict) -> bool:
        """发送卡片消息到指定群"""
        token = self._get_token()
        payload = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        }

        resp = requests.post(
            self.MESSAGE_URL,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            print(f"[FeishuNotifier] 发送失败: {result}")
            return False
        return True

    def _get_target_chats(self, msg_type: str = "production") -> list[str]:
        """获取目标群 chat_id 列表"""
        return [
            c["chat_id"]
            for c in self.chats
            if c.get("type") == msg_type or c.get("type") == "debug"
        ]

    def _build_alarm_card(self, event: AlarmEvent, analysis: Optional[AnalysisResult] = None) -> dict:
        """构建告警卡片"""
        level_colors = {
            AlarmLevel.CRITICAL: "red",
            AlarmLevel.WARNING: "yellow",
            AlarmLevel.INFO: "blue",
        }
        level_icons = {
            AlarmLevel.CRITICAL: "🔴",
            AlarmLevel.WARNING: "🟡",
            AlarmLevel.INFO: "ℹ️",
        }

        header_title = f"{level_icons[event.level]} 告警通知 - 点胶设备"
        color = level_colors[event.level]

        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**告警时间：**{event.timestamp}\n"
                        f"**告警类型：**{level_icons[event.level]} {event.level.value}\n"
                        f"**告警内容：**{event.alarm_text}\n"
                        f"**模块：**{event.module_name}\n"
                        f"**当日已出现：**{event.daily_count} 次"
                    ),
                },
            },
            {"tag": "hr"},
        ]

        if analysis:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**🧠 AI 分析**\n"
                        f"**根本原因：**{analysis.root_cause}\n\n"
                        f"**建议操作：**{analysis.suggestion}\n\n"
                        f"**预计处理时间：**{analysis.probable_time_to_resolve}"
                    ),
                },
            })
            elements.append({"tag": "hr"})

        if event.context_lines:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**📋 日志参考**\n" + "\n".join(event.context_lines[-5:]),
                },
            })

        elements.append({
            "tag": "note",
            "elements": [
                {"tag": "plain_text", "content": "点胶设备 · 日志AI分析预警系统 v0.1"}
            ],
        })

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": header_title},
                "template": color,
            },
            "elements": elements,
        }

    def send_alarm(
        self,
        event: AlarmEvent,
        analysis: Optional[AnalysisResult] = None,
    ) -> bool:
        """推送告警通知到所有生产群"""
        # 检查设备是否启用（如果有设备信息）
        device_name = getattr(event, 'device_name', None)
        if device_name:
            from src.file_watcher import check_device_enabled
            if not check_device_enabled(device_name):
                logger = __import__('logging').getLogger(__name__)
                logger.info(f"设备 {device_name} 已暂停，跳过飞书推送")
                return True  # 返回True避免被标记为失败

        card = self._build_alarm_card(event, analysis)
        chat_ids = self._get_target_chats("production")

        all_ok = True
        for chat_id in chat_ids:
            ok = self._send_message(chat_id, card)
            if not ok:
                all_ok = False
        return all_ok

    def send_test(self, chat_id: str) -> bool:
        """发送测试消息（用于验证配置）"""
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "✅ 告警推送服务测试"},
                "template": "green",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**告警推送服务已配置成功！**\n\n告警推送服务已成功连接到飞书。",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**当前配置：**\n- 监控设备：点胶设备\n- AI 分析：已启用\n- 推送格式：富文本卡片",
                    },
                },
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": "设备日志AI分析预警系统 v0.1"}
                    ],
                },
            ],
        }
        return self._send_message(chat_id, card)

    def _build_daily_report_card(self, summary: DailySummary) -> dict:
        """构建每日汇总卡片"""
        alarm_type_str = "\n".join(
            [f"   {k}：{v} 次" for k, v in summary.alarm_counts.items()]
        )

        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**告警统计**\n"
                        f"告警总次数：{summary.total_alarms} 次\n\n"
                        f"**告警类型分布：**\n{alarm_type_str}\n\n"
                        f"**已复位未解决：**{summary.unresolved_alarms} 次"
                    ),
                },
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**🧠 今日总结**\n{summary.summary_text}",
                },
            },
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": "点胶设备 · 日志AI分析预警系统 v0.1"}
                ],
            },
        ]

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 点胶设备告警日报 - {summary.date}",
                },
                "template": "blue",
            },
            "elements": elements,
        }

    def send_daily_report(self, summary: DailySummary) -> bool:
        """推送每日汇总报告"""
        card = self._build_daily_report_card(summary)
        chat_ids = self._get_target_chats("production")

        all_ok = True
        for chat_id in chat_ids:
            ok = self._send_message(chat_id, card)
            if not ok:
                all_ok = False
        return all_ok