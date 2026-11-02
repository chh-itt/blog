"""
aigc 应用：admin 后台管理
"""

from django.contrib import admin

from .models import AICache


@admin.register(AICache)
class AICacheAdmin(admin.ModelAdmin):
    """AI 缓存管理（可查看命中情况，便于论文演示"缓存命中"效果）"""

    list_display = ("func_type", "input_hash", "output_preview", "created_at")
    list_filter = ("func_type", "created_at")
    search_fields = ("func_type", "input_hash")

    def output_preview(self, obj):
        text = str(obj.output)
        return text[:60] + ("..." if len(text) > 60 else "")

    output_preview.short_description = "输出预览"
