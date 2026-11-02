"""
stats 应用：访问统计与数据可视化模块路由
"""

from django.urls import path

from . import views

urlpatterns = [
    # 统计总览（文章数/评论数/访问量等）
    path("overview/", views.OverviewView.as_view(), name="stats-overview"),
    # 访问趋势（按天）
    path("trend/", views.TrendView.as_view(), name="stats-trend"),
    # 分类占比（饼图数据）
    path("categories/", views.CategoriesView.as_view(), name="stats-categories"),
    # 热门文章 Top10
    path("hot-articles/", views.HotArticlesView.as_view(), name="stats-hot"),
]
