"""统一的 Mock 对象"""
from unittest.mock import MagicMock
import requests

class MockFeishuAPI:
    """飞书 API mock"""

    @staticmethod
    def success_response():
        """成功响应"""
        return MagicMock(status_code=200, json=lambda: {"code": 0})

    @staticmethod
    def error_response():
        """错误响应"""
        return MagicMock(
            status_code=500,
            json=lambda: {"code": 999, "msg": "Internal error"}
        )

    @staticmethod
    def rate_limit_response():
        """限流响应"""
        return MagicMock(status_code=429, json=lambda: {"code": 999, "msg": "Rate limit"})

    @staticmethod
    def token_response():
        """Token 响应"""
        return MagicMock(
            status_code=200,
            json=lambda: {
                "code": 0,
                "tenant_access_token": "test_token_xxx",
                "expire": 7200
            }
        )

class MockAIAnalyzer:
    """AI 分析器 mock"""

    @staticmethod
    def success_response():
        """成功分析结果"""
        return {
            "root_cause": "胶量不足导致点胶阀缺胶报警",
            "severity": "critical",
            "suggestion": "1. 检查胶桶余量\n2. 更换胶桶\n3. 重新启动点胶流程",
            "related_module": "点胶阀",
            "probable_time_to_resolve": "10分钟"
        }

    @staticmethod
    def timeout_response():
        """超时异常"""
        raise requests.exceptions.Timeout("AI API timeout")

    @staticmethod
    def error_response():
        """API 错误"""
        raise requests.exceptions.RequestException("AI API error")

class MockFileSystem:
    """文件系统 mock"""

    @staticmethod
    def create_temp_log_file(tmp_path, filename, content):
        """创建临时日志文件"""
        import os
        file_path = tmp_path / filename
        with open(file_path, "w", encoding="utf-8-sig") as f:
            f.write(content)
        return file_path

    @staticmethod
    def create_default_log(tmp_path, alarm_count=3):
        """创建 Default.log 文件"""
        lines = [
            "2026-07-09 10:29:50,000 [37] [GlueModule][233] - 轨迹数据3动作\n",
            "2026-07-09 10:29:55,000 [37] [GlueModule][234] - 轨迹数据4动作\n",
        ]
        for i in range(alarm_count):
            lines.append(f"2026-07-09 10:30:0{i},000 [1] [FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换\n")
            lines.append(f"2026-07-09 10:30:0{i},500 [6] [FrmMain][1742] - 报警复位操作\n")

        return MockFileSystem.create_temp_log_file(
            tmp_path, "Default.log", "".join(lines)
        )
