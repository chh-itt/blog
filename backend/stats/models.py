"""
stats 应用：模型
- VisitLog 访问日志（用于统计面板：趋势/来源/热门）
"""

from django.db import models


class VisitLog(models.Model):
    """
    访问日志表
    每次文章详情被访问时记录一行，支撑 ECharts 统计面板
    """

    article = models.ForeignKey(
        "blog.Article", on_delete=models.CASCADE, related_name="visit_logs", verbose_name="文章", null=True, blank=True
    )
    ip = models.GenericIPAddressField("IP地址", null=True, blank=True)
    user_agent = models.CharField("浏览器UA", max_length=500, blank=True)
    path = models.CharField("访问路径", max_length=255, blank=True)
    created_at = models.DateTimeField("访问时间", auto_now_add=True)

    class Meta:
        verbose_name = "访问日志"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["created_at"], name="idx_visit_created")]

    def __str__(self):
        return f"{self.ip} -> {self.path} @ {self.created_at:%Y-%m-%d %H:%M}"
