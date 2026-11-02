"""
sysconf 应用：视图
=====================================================================
GET /api/sysconf/config/  : 查看全部系统配置（敏感项脱敏）
PUT /api/sysconf/config/  : 批量更新配置（仅白名单键，仅博主可操作）
=====================================================================
"""

from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api import ApiResponseMixin

from .models import SysConfig
from .permissions import IsAuthor
from .serializers import SysConfigSerializer
from .services import set_config

# 可配置项白名单：key -> (是否敏感, 说明)
CONFIG_DEFS = {
    "DEEPSEEK_API_KEY": (True, "DeepSeek 大模型 API Key（AI 摘要/标签/写作/问答/审核）"),
    "DEEPSEEK_BASE_URL": (False, "DeepSeek 接口地址（默认 https://api.deepseek.com）"),
    "DEEPSEEK_MODEL": (False, "DeepSeek 模型名（默认 deepseek-chat）"),
    "EMBEDDING_API_KEY": (True, "Embedding 向量 API Key（语义检索/相关推荐）"),
    "EMBEDDING_BASE_URL": (False, "Embedding 接口地址（默认 SiliconFlow）"),
    "EMBEDDING_MODEL": (False, "Embedding 模型名（默认 BAAI/bge-m3）"),
}


class ConfigView(ApiResponseMixin, APIView):
    """系统配置查看与修改（仅博主）"""

    permission_classes = [permissions.IsAuthenticated, IsAuthor]

    def get(self, request):
        """返回全部配置，敏感项脱敏"""
        configs = SysConfig.objects.all()
        return Response(SysConfigSerializer(configs, many=True).data)

    def put(self, request):
        """批量更新：body 为 {key: value}，只接受白名单键"""
        payload = request.data or {}
        if not isinstance(payload, dict):
            raise ValidationError({"detail": "请求体格式错误，应为 {key: value}"})
        for key, value in payload.items():
            if key in CONFIG_DEFS:
                is_secret, desc = CONFIG_DEFS[key]
                set_config(key, str(value), is_secret=is_secret, description=desc)
        configs = SysConfig.objects.all()
        return Response(SysConfigSerializer(configs, many=True).data)
