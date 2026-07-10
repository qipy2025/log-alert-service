"""通知控制器"""
import logging
from datetime import datetime
from src.db.mysql import get_db_session
from src.models.alarm import AlarmRecord
from src.feishu_notifier import FeishuNotifier

logger = logging.getLogger(__name__)


class NotificationController:
    """通知发送控制"""

    def __init__(self):
        self.notifier = None
        self._init_notifier()

    def _init_notifier(self):
        """初始化飞书通知器"""
        try:
            from src.config_manager import ConfigManager
            config = ConfigManager('config.yaml')
            feishu_config = config.get('feishu', {})

            self.notifier = FeishuNotifier(
                app_id=feishu_config.get('app_id', ''),
                app_secret=feishu_config.get('app_secret', ''),
                chats=feishu_config.get('chats', [])
            )
        except Exception as e:
            logger.error(f"初始化飞书通知器失败: {e}")

    def send_alarm_notification(self, alarm_id: int) -> dict:
        """手动发送告警通知

        Args:
            alarm_id: 告警记录ID

        Returns:
            发送结果

        Raises:
            ValueError: 告警不存在或已发送
            RuntimeError: 飞书API调用失败
        """
        session = get_db_session()
        try:
            # 获取告警记录
            alarm = session.query(AlarmRecord).filter_by(id=alarm_id).first()
            if not alarm:
                raise ValueError(f"告警记录不存在: {alarm_id}")

            # 检查是否已发送
            if alarm.notified:
                raise ValueError(f"通知已发送，不能重复发送: {alarm_id}")

            # 构建告警事件（用于飞书通知）
            from src.data_models import AlarmEvent, AlarmLevel, AlarmSource

            event = AlarmEvent(
                timestamp=alarm.log_timestamp or datetime.now(),
                alarm_text=alarm.alarm_content or "",
                module_name=alarm.device_name,
                level=AlarmLevel.INFO,
                source=AlarmSource.DEFAULT_LOG,
                line_number=0,
                log_file="",
                raw_line=""
            )

            # 解析AI分析结果
            analysis = None
            if alarm.ai_analysis:
                import json
                try:
                    analysis_data = json.loads(alarm.ai_analysis)
                    from src.data_models import AnalysisResult
                    analysis = AnalysisResult(
                        root_cause=analysis_data.get('root_cause', ''),
                        severity=analysis_data.get('severity', ''),
                        suggestion=analysis_data.get('suggestion', ''),
                        related_module=analysis_data.get('related_module', '')
                    )
                except:
                    pass

            # 发送飞书通知
            if self.notifier:
                success = self.notifier.send_alarm(event, analysis)
                if not success:
                    raise RuntimeError("飞书通知发送失败")

            # 标记为已发送
            alarm.notified = True
            session.commit()

            logger.info(f"通知已发送: alarm_id={alarm_id}")
            return {
                "success": True,
                "sent_at": datetime.now().isoformat()
            }

        except Exception as e:
            session.rollback()
            logger.error(f"发送通知失败: {e}")
            raise
        finally:
            session.close()

    def set_auto_notify(self, device_name: str, auto_notify: bool) -> bool:
        """设置设备的自动发送开关

        Args:
            device_name: 设备名称
            auto_notify: 是否自动发送

        Returns:
            是否设置成功
        """
        from src.device_manager import DeviceManager
        manager = DeviceManager()
        return manager.update_auto_notify(device_name, auto_notify)

    def batch_send_notifications(self, alarm_ids: list) -> dict:
        """批量发送通知

        Args:
            alarm_ids: 告警ID列表

        Returns:
            发送结果统计
        """
        sent_count = 0
        failed_count = 0
        results = []

        for alarm_id in alarm_ids:
            try:
                self.send_alarm_notification(alarm_id)
                sent_count += 1
                results.append({"alarm_id": alarm_id, "success": True})
            except Exception as e:
                failed_count += 1
                results.append({
                    "alarm_id": alarm_id,
                    "success": False,
                    "error": str(e)
                })

        return {
            "sent_count": sent_count,
            "failed_count": failed_count,
            "results": results
        }
