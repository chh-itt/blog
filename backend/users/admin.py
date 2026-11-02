"""
users 应用：admin 后台管理
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """扩展默认用户管理：显示自定义字段"""

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("扩展信息", {"fields": ("nickname", "avatar", "bio", "is_author", "created_at")}),
    )
    list_display = ("username", "nickname", "email", "is_author", "is_staff", "date_joined")
    list_filter = ("is_author", "is_staff", "is_active")
    search_fields = ("username", "nickname", "email")
    readonly_fields = ("created_at",)
