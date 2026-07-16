import json
import logging
from typing import Optional

import requests

from src.data_models import AlarmEvent, AnalysisResult

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一个设备故障诊断专家。分析以下日志片段，找出告警的根本原因，
并给出具体的故障排除建议。回答要简洁、实用、针对具体的设备和工站。
只基于提供的日志内容做分析，不要猜测没有依据的原因。

请严格按以下 JSON 格式输出，不要包含任何其他内容：
{
  "root_cause": "根本原因分析（1-2句话）",
  "severity": "critical | warning | info",
  "suggestion": "具体的操作建议，分点列出",
  "related_module": "相关模块或工站",
  "probable_time_to_resolve": "预计处理时间"
}"""


class AIAnalyzer:
    """调用 Claude API（兼容接口）分析告警上下文"""

    def __init__(
        self,
        api_key: str,
        api_base_url: str = "http://model-api.desaysv.com",
        model: str = "deepseek-v4-flash-anthropic",
        max_tokens: int = 2048,
        temperature: float = 0.3,
        timeout: int = 30,
        enabled: bool = True,
    ):
        self.api_key = api_key
        self.api_base_url = api_base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.enabled = enabled

    def _build_prompt(self, event: AlarmEvent) -> str:
        """构建分析 prompt"""
        parts = [
            "[告警信息]",
            f"时间: {event.timestamp}",
            f"告警内容: {event.alarm_text}",
            f"模块: {event.module_name}",
            f"当日同类告警次数: {event.daily_count}",
            "",
            "[Default.log 上下文]",
        ]
        parts.extend(event.context_lines)
        parts.append("")
        parts.append("[功能日志关联]")
        parts.extend(event.functional_log_context)
        return "\n".join(parts)

    def analyze(self, event: AlarmEvent) -> Optional[AnalysisResult]:
        """
        分析告警事件，返回分析结果。
        如果 AI 分析被禁用或调用失败，返回 None。
        """
        if not self.enabled:
            return None

        prompt = self._build_prompt(event)

        try:
            logger.info(f"调用AI分析: model={self.model}, 告警={event.alarm_text[:40]}")
            response = requests.post(
                f"{self.api_base_url}/v1/messages",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "system": SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=self.timeout,
            )
            logger.info(f"AI响应 status={response.status_code}, len={len(response.text)}")
            response.raise_for_status()
            data = response.json()

            # 提取响应文本
            content = data.get("content", [])
            if not content:
                logger.warning(f"AI响应content为空: {str(data)[:200]}")
                return None

            response_text = content[0].get("text", "") if isinstance(content[0], dict) else content[0]
            logger.info(f"AI响应文本(前100): {response_text[:100]}")

            # 解析 JSON
            return self._parse_response(response_text)

        except requests.exceptions.RequestException as e:
            logger.error(f"AI API请求失败: {e}")
            return None
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"AI响应解析失败: {e}, raw: {response_text[:200] if 'response_text' in dir() else 'N/A'}")
            return None

    def _parse_response(self, text: str) -> Optional[AnalysisResult]:
        """从 AI 响应中提取 JSON"""
        # 尝试直接解析
        text = text.strip()
        # 处理可能包含 ```json ... ``` 代码块的情况
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)
        suggestion = data.get("suggestion", "")
        if isinstance(suggestion, list):
            suggestion = "\n".join(str(s) for s in suggestion)
        return AnalysisResult(
            root_cause=data.get("root_cause", ""),
            severity=data.get("severity", "warning"),
            suggestion=suggestion,
            related_module=data.get("related_module", ""),
            probable_time_to_resolve=data.get("probable_time_to_resolve", ""),
        )