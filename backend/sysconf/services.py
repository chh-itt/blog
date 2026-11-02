"""
sysconf 应用：配置读写服务层
=====================================================================
提供给 aigc / blog 等业务层使用的配置读取入口：
- get_config(key, default) : 优先读数据库配置，未设置时回退到默认值
                              （默认值通常来自 settings / .env）
- get_secret_config(key)    : 读取敏感配置（API Key），兼容旧的环境变量
- 这样"前端设置页 → 数据库"的链路不会破坏原有 .env 兜底机制
=====================================================================
"""

from django.conf import settings

from .models import SysConfig


def get_config(key: str, default=None):
    """
    读取配置：数据库优先，未配置或为空时回退 default。
    - key     : 配置键
    - default : 兜底默认值（一般传 settings 里的同名配置）
    """
    try:
        obj = SysConfig.objects.get(pk=key)
        # 数据库里显式存了空字符串表示"清空"，此时也回退默认值
        if obj.value:
            return obj.value
    except SysConfig.DoesNotExist:
        pass
    return default


def get_deepseek_key():
    """读取 DeepSeek API Key：数据库优先，兜底 settings"""
    return get_config("DEEPSEEK_API_KEY", settings.DEEPSEEK_API_KEY)


def get_embedding_key():
    """读取 Embedding API Key：数据库优先，兜底 settings"""
    return get_config("EMBEDDING_API_KEY", settings.EMBEDDING_API_KEY)


def get_deepseek_base_url():
    """读取 DeepSeek Base URL，兜底 settings"""
    return get_config("DEEPSEEK_BASE_URL", settings.DEEPSEEK_BASE_URL)


def get_deepseek_model():
    """读取 DeepSeek 模型名，兜底 settings"""
    return get_config("DEEPSEEK_MODEL", settings.DEEPSEEK_MODEL)


def get_embedding_base_url():
    """读取 Embedding Base URL，兜底 settings"""
    return get_config("EMBEDDING_BASE_URL", settings.EMBEDDING_BASE_URL)


def get_embedding_model():
    """读取 Embedding 模型名，兜底 settings"""
    return get_config("EMBEDDING_MODEL", settings.EMBEDDING_MODEL)


def set_config(key: str, value: str, is_secret: bool = False, description: str = "") -> None:
    """写入/更新配置（幂等）"""
    if value is None:
        value = ""
    SysConfig.objects.update_or_create(
        pk=key,
        defaults={"value": value, "is_secret": is_secret, "description": description},
    )
