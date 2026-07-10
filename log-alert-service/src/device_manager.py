"""设备管理器"""
import re
import logging
from src.db.device_config import DeviceConfig
from src.db.cache import get_device_status

logger = logging.getLogger(__name__)

class DeviceManager:
    """设备管理业务逻辑"""

    # 设备名称正则：允许中文、字母、数字、下划线，1-50字符
    DEVICE_NAME_PATTERN = re.compile(r'^[一-龥a-zA-Z0-9_]{1,50}$')

    # Windows路径正则
    WINDOWS_PATH_PATTERN = re.compile(r'^[a-zA-Z]:\\[^<>:"|?*]*')

    # Linux路径正则
    LINUX_PATH_PATTERN = re.compile(r'^/[^<>:"|?*]*')

    @staticmethod
    def validate_device_name(device_name: str) -> bool:
        """验证设备名称"""
        if not device_name:
            raise ValueError("设备名称不能为空")

        if not DeviceManager.DEVICE_NAME_PATTERN.match(device_name):
            raise ValueError("设备名称格式无效：只允许中文、字母、数字、下划线，长度1-50字符")

        return True

    @staticmethod
    def validate_log_path(log_path: str) -> bool:
        """验证日志路径格式"""
        if not log_path:
            raise ValueError("日志路径不能为空")

        # 检查是否为有效的Windows或Linux路径
        is_windows = DeviceManager.WINDOWS_PATH_PATTERN.match(log_path)
        is_linux = DeviceManager.LINUX_PATH_PATTERN.match(log_path)

        # 也支持相对路径（如：设备名\\日志\\）
        if not (is_windows or is_linux):
            # 检查是否包含非法字符
            invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
            if any(char in log_path for char in invalid_chars):
                raise ValueError("路径格式无效：包含非法字符")

        return True

    def add_device(self, config: dict) -> dict:
        """添加新设备

        Args:
            config: {
                "device_name": str,
                "log_path": str,
                "auto_notify": bool (optional),
                "polling_interval": int (optional),
                "encoding": str (optional)
            }

        Returns:
            新创建的设备配置

        Raises:
            ValueError: 设备名称已存在或输入验证失败
        """
        device_name = config.get("device_name")
        log_path = config.get("log_path")

        # 验证输入
        self.validate_device_name(device_name)
        self.validate_log_path(log_path)

        # 检查设备是否已存在
        if DeviceConfig.exists(device_name):
            raise ValueError(f"设备名称已存在: {device_name}")

        # 获取可选参数
        auto_notify = config.get("auto_notify", False)
        polling_interval = config.get("polling_interval", 2)
        encoding = config.get("encoding", "utf-8-sig")

        # 创建设备配置
        try:
            device = DeviceConfig.create(
                device_name=device_name,
                log_path=log_path,
                auto_notify=auto_notify,
                polling_interval=polling_interval,
                encoding=encoding
            )
            logger.info(f"设备已添加: {device_name}")
            return device
        except Exception as e:
            logger.error(f"添加设备失败: {e}")
            raise

    def delete_device(self, device_name: str) -> bool:
        """删除设备

        Args:
            device_name: 设备名称

        Returns:
            是否删除成功

        Raises:
            ValueError: 设备不存在
        """
        # 检查设备是否存在
        if not DeviceConfig.exists(device_name):
            raise ValueError(f"设备不存在: {device_name}")

        # 检查设备是否正在运行
        try:
            status = get_device_status(device_name)
            if status.get("status") == "RUNNING":
                # TODO: 停止设备监控
                logger.warning(f"设备正在运行，请先停止: {device_name}")
                raise RuntimeError(f"设备正在运行，无法删除: {device_name}")
        except:
            # 如果获取状态失败，继续删除
            pass

        # 删除设备配置
        try:
            result = DeviceConfig.delete(device_name)
            if result:
                logger.info(f"设备已删除: {device_name}，历史告警记录已保留")
            return result
        except Exception as e:
            logger.error(f"删除设备失败: {e}")
            raise

    def get_all_devices(self) -> list:
        """获取所有设备配置

        Returns:
            设备配置列表
        """
        return DeviceConfig.get_all()

    def get_device(self, device_name: str) -> dict:
        """获取单个设备配置

        Returns:
            设备配置，如果不存在返回 None
        """
        return DeviceConfig.get_by_name(device_name)

    def update_auto_notify(self, device_name: str, auto_notify: bool) -> bool:
        """更新设备的自动发送设置

        Args:
            device_name: 设备名称
            auto_notify: 是否自动发送

        Returns:
            是否更新成功
        """
        if not DeviceConfig.exists(device_name):
            raise ValueError(f"设备不存在: {device_name}")

        result = DeviceConfig.update_auto_notify(device_name, auto_notify)
        if result:
            logger.info(f"设备 {device_name} 自动发送设置为: {auto_notify}")
        return result

    def update_device(self, device_name: str, config: dict) -> dict:
        """更新设备配置

        Args:
            device_name: 当前设备名称
            config: {
                "device_name": str (optional),  # 新的设备名称
                "log_path": str (optional),
                "enabled": bool (optional)
            }

        Returns:
            更新后的设备配置

        Raises:
            ValueError: 设备不存在或输入验证失败
        """
        # 检查设备是否存在
        if not DeviceConfig.exists(device_name):
            raise ValueError(f"设备不存在: {device_name}")

        # 获取可选参数
        new_device_name = config.get("device_name")
        new_log_path = config.get("log_path")
        new_enabled = config.get("enabled")

        # 如果要修改设备名称，需要验证新名称
        if new_device_name is not None:
            self.validate_device_name(new_device_name)
            # 检查新名称是否已被其他设备使用
            if new_device_name != device_name and DeviceConfig.exists(new_device_name):
                raise ValueError(f"设备名称已存在: {new_device_name}")

        # 如果要修改日志路径，需要验证
        if new_log_path is not None:
            self.validate_log_path(new_log_path)

        # 处理设备名称修改（需要特殊处理）
        if new_device_name is not None and new_device_name != device_name:
            # 1. 获取旧配置
            old_device = DeviceConfig.get_by_name(device_name)
            # 2. 创建新设备
            DeviceConfig.create(
                device_name=new_device_name,
                log_path=new_log_path or old_device["log_path"],
                auto_notify=old_device["auto_notify"],
                polling_interval=old_device["polling_interval"],
                encoding=old_device["encoding"],
                enabled=new_enabled if new_enabled is not None else old_device["enabled"]
            )
            # 3. 删除旧设备
            DeviceConfig.delete(device_name)
            # 4. 返回新设备配置
            return DeviceConfig.get_by_name(new_device_name)
        else:
            # 只更新其他字段
            result = DeviceConfig.update(
                device_name=device_name,
                log_path=new_log_path,
                enabled=new_enabled
            )
            if result:
                return DeviceConfig.get_by_name(device_name)
            else:
                raise ValueError(f"更新设备失败: {device_name}")
