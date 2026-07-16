"""网络共享（SMB/CIFS）访问支持

通过 Windows 原生 net use 命令建立网络共享会话，
建立后即可用普通 open() 直接读取 UNC 路径下的文件。

仅 Windows 平台有效；非 UNC 路径视为本地路径，直接放行。
"""
import base64
import logging
import re
import subprocess

logger = logging.getLogger(__name__)

# UNC 路径根（\\host\share），忽略后续子路径
_UNC_ROOT_PATTERN = re.compile(r'^(\\\\[^\\]+\\[^\\]+)')


def is_unc_path(log_path: str) -> bool:
    """判断是否为 UNC 网络路径（以 \\\\ 开头）"""
    return bool(log_path) and log_path.startswith('\\\\')


def extract_share_root(log_path: str) -> str:
    """从 UNC 路径提取 \\host\\share 根。

    例如 \\\\10.146.175.53\\Log\\sub -> \\\\10.146.175.53\\Log
    非 UNC 路径原样返回。
    """
    if not log_path:
        return log_path
    m = _UNC_ROOT_PATTERN.match(log_path)
    return m.group(1) if m else log_path


def encode_password(plain: str) -> str:
    """Base64 编码密码（入库前调用，简单遮蔽，非强加密）"""
    if not plain:
        return ''
    return base64.b64encode(plain.encode('utf-8')).decode('utf-8')


def decode_password(encoded: str) -> str:
    """Base64 解码密码（出库后调用）"""
    if not encoded:
        return ''
    try:
        return base64.b64decode(encoded).decode('utf-8')
    except Exception as e:
        logger.warning(f"密码解码失败，按明文处理: {e}")
        return encoded


def ensure_share_connection(log_path: str, username: str, password: str) -> bool:
    """建立网络共享会话（幂等）

    用 net use 命令建立 \\host\\share 的认证会话。
    若已存在同名会话先删除再重建，确保凭据正确。

    Args:
        log_path: UNC 日志路径（\\\\host\\share[\\sub...]）
        username: 共享访问用户名
        password: 共享访问密码（明文）

    Returns:
        True 表示建立成功或为本地路径无需认证；False 表示失败
    """
    if not is_unc_path(log_path):
        return True  # 本地路径无需建立共享会话

    if not username:
        logger.warning(f"UNC 路径 {log_path} 未配置用户名，跳过 net use 认证")
        return False

    share_root = extract_share_root(log_path)

    # 先尝试删除已有会话（忽略错误，可能不存在或已失效）
    try:
        subprocess.run(
            ["net", "use", share_root, "/delete", "/y"],
            capture_output=True, text=True, timeout=10
        )
    except Exception as e:
        logger.debug(f"删除旧会话 {share_root} 出错（可忽略）: {e}")

    # 建立新会话
    try:
        result = subprocess.run(
            ["net", "use", share_root, f"/user:{username}", password, "/persistent:no"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            logger.info(f"✅ 网络共享会话已建立: {share_root} (用户: {username})")
            return True
        else:
            logger.error(
                f"❌ 建立网络共享会话失败: {share_root} "
                f"(返回码: {result.returncode}, 输出: {(result.stderr or result.stdout).strip()})"
            )
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"❌ 建立网络共享会话超时: {share_root}")
        return False
    except FileNotFoundError:
        logger.error("❌ 未找到 net 命令（当前系统可能非 Windows），无法建立共享会话")
        return False
    except Exception as e:
        logger.error(f"❌ 建立网络共享会话异常: {share_root} - {e}")
        return False
