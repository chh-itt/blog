"""
blog 应用：文章、分类、标签、评论、检索模块路由
"""

from django.urls import path

from . import views

urlpatterns = [
    # 公开文章列表（仅已发布）
    path("articles/", views.ArticleListView.as_view(), name="article-list"),
    # 文章详情（浏览量+1）
    path("articles/<int:pk>/", views.ArticleDetailView.as_view(), name="article-detail"),
    # 作者管理：我的文章 / 创建 / 我的文章详情（含草稿与正文）
    path("my/articles/", views.MyArticlesView.as_view(), name="my-articles"),
    path("my/articles/<int:pk>/", views.MyArticleDetailView.as_view(), name="my-article-detail"),
    path("author/articles/", views.ArticleListCreateView.as_view(), name="article-create"),
    # 作者管理：编辑/删除单篇文章
    path("author/articles/<int:pk>/", views.ArticleUpdateDestroyView.as_view(), name="article-update"),
    # 分类树 / 标签
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("tags/", views.TagListView.as_view(), name="tag-list"),
    # AI 标签自动入库（批量确保存在）
    path("tags/ensure/", views.TagEnsureView.as_view(), name="tag-ensure"),
    # AI/手动分类入库（同名复用，否则建顶层）
    path("categories/ensure/", views.CategoryEnsureView.as_view(), name="category-ensure"),
    # 评论：列表 + 发表
    path("articles/<int:article_id>/comments/", views.CommentListView.as_view(), name="comment-list"),
    # 评论审核（博主）
    path("comments/moderate/", views.CommentModerateView.as_view(), name="comment-moderate"),
    path("comments/auto-moderate/", views.CommentAutoModerateView.as_view(), name="comment-auto-moderate"),
    # 混合检索（创新点2）
    path("search/", views.SearchView.as_view(), name="search"),
    # 相关文章推荐（创新点2）
    path("articles/<int:article_id>/related/", views.RelatedArticlesView.as_view(), name="article-related"),
]
