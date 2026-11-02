"""
blog 应用：admin 后台管理
"""

from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin

from .models import Article, Category, Comment, Tag


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    """分类管理（支持拖拽排序的树形结构）"""

    mptt_level_indent = 20
    list_display = ("tree_actions", "indented_title", "slug", "description")
    list_display_links = ("indented_title",)
    search_fields = ("name", "slug")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """文章管理"""

    list_display = ("title", "author", "category", "status", "views", "likes", "is_top", "published_at")
    list_filter = ("status", "is_top", "category", "created_at")
    search_fields = ("title", "summary", "content_md")
    readonly_fields = ("slug", "views", "likes", "ai_summary", "ai_tags", "search_vector", "embedding", "created_at", "updated_at", "published_at")
    autocomplete_fields = ("author", "category", "tags")
    date_hierarchy = "published_at"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """评论管理（含审核状态）"""

    list_display = ("content", "user", "article", "status", "likes", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("content", "user__username")
    actions = ["approve_comments", "reject_comments"]

    @admin.action(description="批量通过审核")
    def approve_comments(self, request, queryset):
        queryset.update(status=Comment.STATUS_APPROVED)
        self.message_user(request, f"已通过 {queryset.count()} 条评论")

    @admin.action(description="批量拒绝")
    def reject_comments(self, request, queryset):
        queryset.update(status=Comment.STATUS_REJECTED)
        self.message_user(request, f"已拒绝 {queryset.count()} 条评论")
