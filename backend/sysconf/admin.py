"""
sysconf 应用：Django 自带后台注册
"""

from django.contrib import admin

from .models import SysConfig


@admin.register(SysConfig)
class SysConfigAdmin(admin.ModelAdmin):
    """系统配置后台管理"""

    list_display = ["key", "value", "is_secret", "updated_at"]
    search_fields = ["key"]
