"""
stats 应用：admin 后台管理
"""

from django.contrib import admin

from .models import VisitLog


@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    """访问日志管理"""

    list_display = ("ip", "path", "article", "created_at")
    list_filter = ("created_at",)
    search_fields = ("ip", "path")
    readonly_fields = ("ip", "path", "user_agent", "article", "created_at")

    def has_add_permission(self, request):
        return False
