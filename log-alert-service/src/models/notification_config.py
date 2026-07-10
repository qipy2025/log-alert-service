"""通知配置数据模型"""
from dataclasses import dataclass
from typing import Optional, List
import json


@dataclass
class NotificationConfig:
    """通知配置数据模型"""
    id: int
    enabled: bool
    allowed_levels: List[str]

    @classmethod
    def from_db(cls, record) -> 'NotificationConfig':
        """从数据库记录创建模型

        Args:
            record: 数据库记录对象，包含 id, enabled, allowed_levels 字段

        Returns:
            NotificationConfig 实例
        """
        levels = []
        if record and hasattr(record, 'allowed_levels') and record.allowed_levels:
            try:
                # 如果是字符串，解析 JSON
                if isinstance(record.allowed_levels, str):
                    levels = json.loads(record.allowed_levels)
                # 如果已经是列表，直接使用
                elif isinstance(record.allowed_levels, list):
                    levels = record.allowed_levels
            except (json.JSONDecodeError, TypeError):
                # 解析失败，返回空列表
                levels = []

        return cls(
            id=record.id if record and hasattr(record, 'id') else 1,
            enabled=record.enabled if record and hasattr(record, 'enabled') else False,
            allowed_levels=levels
        )
