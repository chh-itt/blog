"""
sysconf 应用：序列化器
"""

from rest_framework import serializers

from .models import SysConfig


def mask_secret(value: str) -> str:
    """敏感值脱敏：只保留首尾 4 位，中间用 * 代替"""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "****" + value[-4:]


class SysConfigSerializer(serializers.ModelSerializer):
    """系统配置序列化器（敏感项返回时自动脱敏）"""

    class Meta:
        model = SysConfig
        fields = ["key", "value", "is_secret", "description", "updated_at"]
        read_only_fields = ["key", "is_secret", "description", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_secret:
            data["value"] = mask_secret(data["value"])
        return data
