"""
aigc 应用：AI 智能内容服务模块路由（创新点1）
"""

from django.urls import path

from . import views

urlpatterns = [
    # AI 自动摘要
    path("summary/", views.SummaryView.as_view(), name="aigc-summary"),
    # AI 自动标签
    path("tags/", views.TagsView.as_view(), name="aigc-tags"),
    # AI 写作助手
    path("writer/", views.WriterView.as_view(), name="aigc-writer"),
    # AI 智能问答（RAG）
    path("qa/", views.QaView.as_view(), name="aigc-qa"),
    # AI 评论审核
    path("moderate/", views.ModerateView.as_view(), name="aigc-moderate"),
    # AI 自动分类
    path("classify/", views.ClassifyView.as_view(), name="aigc-classify"),
]
