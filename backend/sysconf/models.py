"""
sysconf 应用：系统配置模型
=====================================================================
以"键-值"方式存储运行时配置（如 DeepSeek/Embedding 的 API Key），
让博主可以在前端设置页填写配置，而无需修改 .env 文件或重启服务。
- key      : 配置键（主键），如 DEEPSEEK_API_KEY
- value    : 配置值
- is_secret: 敏感项标记（API Key 等），返回前端时自动脱敏
- description: 配置项说明（展示在设置页表单）
=====================================================================
"""

from django.db import models


class SysConfig(models.Model):
    """系统运行时配置（键值对）"""

    key = models.CharField("配置键", max_length=64, primary_key=True)
    value = models.TextField("配置值", blank=True)
    is_secret = models.BooleanField("敏感项", default=False)
    description = models.CharField("说明", max_length=255, blank=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "系统配置"
        verbose_name_plural = verbose_name
        ordering = ["key"]

    def __str__(self):
        return self.key
