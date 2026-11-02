"""
aigc 应用：模型
- AICache AI 结果缓存（创新点1：按 功能类型 + 输入哈希 去重缓存，避免重复调用付费 API）
"""

from django.db import models


class AICache(models.Model):
    """
    AI 生成结果缓存表
    - func_type：功能类型（summary/tags/writer/qa/moderate）
    - input_hash：输入内容的哈希值（MD5，命中即复用结果）
    - output：AI 返回结果（JSON 存储，兼容字符串/列表/对象）
    """

    func_type = models.CharField("功能类型", max_length=50)
    input_hash = models.CharField("输入哈希", max_length=64, db_index=True)
    output = models.JSONField("输出结果", default=dict)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "AI缓存"
        verbose_name_plural = verbose_name
        unique_together = [["func_type", "input_hash"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.func_type}:{self.input_hash[:8]}"
