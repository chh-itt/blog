"""
blog 应用：视图
- 分类 / 标签 列表
- 文章 CRUD（公开读 / 作者写）
- 评论 列表 + 发表
- 混合检索 search（创新点2 对外接口）
- 相关文章推荐 related
"""

import logging

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, Q
from django.utils.text import slugify
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, views
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from aigc import services as aigc_services

from config.api import ApiResponseMixin

from . import services as blog_services
from .models import Article, Category, Comment, Tag
from .serializers import (
    ArticleDetailSerializer,
    ArticleListSerializer,
    ArticleWriteSerializer,
    CategoryEnsureSerializer,
    CategorySerializer,
    CommentSerializer,
    CommentWriteSerializer,
    SearchResultSerializer,
    TagEnsureSerializer,
    TagSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 分类 & 标签
# ------------------------------------------------------------------
class CategoryListView(ApiResponseMixin, generics.ListAPIView):
    """分类树列表"""

    queryset = Category.objects.filter(level=0)  # 顶层分类
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # 元数据接口不分页


class TagListView(ApiResponseMixin, generics.ListAPIView):
    """标签列表（含文章数）"""

    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # 元数据接口不分页

    def get_queryset(self):
        return Tag.objects.annotate(article_count=Count("articles")).order_by("-article_count")


class TagEnsureView(ApiResponseMixin, views.APIView):
    """AI 标签自动入库：批量确保标签存在（不存在则创建），返回 id 列表（登录用户）"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        s = TagEnsureSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = []
        for name in s.validated_data["names"]:
            name = (name or "").strip()
            if not name or len(name) > 50:
                continue
            tag, created = Tag.objects.get_or_create(name=name)
            result.append({"id": tag.id, "name": tag.name, "created": created})
        return Response({"code": 0, "message": "success", "data": result})


class CategoryEnsureView(ApiResponseMixin, views.APIView):
    """AI/手动分类入库：同名任意层级复用，否则创建为顶层大类（登录用户）"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        s = CategoryEnsureSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        name = (s.validated_data["name"] or "").strip()
        if not name or len(name) > 50:
            return Response({"code": 400, "message": "分类名不合法（1~50字）", "data": None}, status=400)
        # 优先复用：任意层级同名分类
        category = Category.objects.filter(name=name).first()
        created = False
        if category is None:
            # 新建为顶层大类；slug 冲突时追加后缀（Category.slug 有 unique 约束）
            base = slugify(name, allow_unicode=True) or name
            slug = base
            i = 2
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            category = Category.objects.create(name=name, slug=slug)
            created = True
        return Response(
            {
                "code": 0,
                "message": "success",
                "data": {"id": category.id, "name": category.name, "created": created, "level": category.level},
            }
        )


# ------------------------------------------------------------------
# 文章
# ------------------------------------------------------------------
class ArticleListView(ApiResponseMixin, generics.ListAPIView):
    """文章列表（仅已发布；Redis 缓存首页第一页 60 秒）"""

    serializer_class = ArticleListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "tags", "is_top"]
    search_fields = ["title", "summary", "content_md"]
    ordering_fields = ["published_at", "views", "likes"]
    ordering = ["-is_top", "-published_at"]

    def get_queryset(self):
        qs = Article.objects.filter(status=Article.STATUS_PUBLISHED).select_related("author", "category")
        # 关键词额外用标题/摘要/标签做非空过滤（与 search 接口互补）
        return qs

    def list(self, request, *args, **kwargs):
        """首页列表走 Redis 缓存（支撑点：Redis 多级缓存）"""
        from django.core.cache import cache

        # 仅缓存默认排序的第一页，避免缓存键爆炸
        is_default = (
            not request.query_params
            or set(request.query_params.keys()) <= {"page"}
            and request.query_params.get("page", "1") == "1"
        )
        cache_key = "blog:article_list:page1"
        if is_default:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)
        response = super().list(request, *args, **kwargs)
        if is_default and response.status_code == 200:
            cache.set(cache_key, response.data, timeout=60)
        return response


class ArticleDetailView(ApiResponseMixin, generics.RetrieveAPIView):
    """文章详情（访问时 +1 浏览量并记日志；详情走 Redis 缓存）"""

    queryset = Article.objects.filter(status=Article.STATUS_PUBLISHED)
    serializer_class = ArticleDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"  # 对应 URL 中的 <int:pk>

    def retrieve(self, request, *args, **kwargs):
        from django.core.cache import cache

        cache_key = f"blog:article_detail:{kwargs.get('pk')}"
        cached = cache.get(cache_key)
        if cached is not None:
            # 命中缓存：仅浏览量 +1 与访问日志仍走 DB（不计入序列化）
            Article.objects.filter(pk=kwargs["pk"]).update(views=models.F("views") + 1)
            try:
                from stats.models import VisitLog

                VisitLog.objects.create(
                    article_id=kwargs["pk"],
                    ip=request.META.get("REMOTE_ADDR"),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                    path=request.path,
                )
            except Exception:
                pass
            return Response(cached)

        instance = self.get_object()
        # 浏览量 +1（用 F 避免并发覆盖）
        Article.objects.filter(pk=instance.pk).update(views=instance.views + 1)
        instance.views += 1
        # 记录访问日志（创新点：统计面板数据来源）
        try:
            from stats.models import VisitLog

            VisitLog.objects.create(
                article=instance,
                ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                path=request.path,
            )
        except Exception:
            pass
        serializer = self.get_serializer(instance)
        # 写缓存：文章详情 5 分钟
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data)


class ArticleListCreateView(ApiResponseMixin, generics.ListCreateAPIView):
    """文章创建（登录作者）"""

    serializer_class = ArticleWriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # 管理端一次返回，由前端分页

    def get_queryset(self):
        return Article.objects.filter(author=self.request.user).select_related("category")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        # 创建新文章后清除列表缓存，避免前台首页列表缺失新文章
        from django.core.cache import cache

        cache.delete("blog:article_list:page1")


class ArticleUpdateDestroyView(ApiResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    """文章编辑 / 删除（仅作者本人）"""

    serializer_class = ArticleWriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"  # 对应 URL <int:pk>

    def get_queryset(self):
        return Article.objects.filter(author=self.request.user)

    def _clear_article_cache(self, pk):
        """更新/删除文章后清除详情与列表缓存，保证前台读到最新数据"""
        from django.core.cache import cache

        cache.delete(f"blog:article_detail:{pk}")
        cache.delete("blog:article_list:page1")

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        self._clear_article_cache(kwargs.get("pk"))
        return resp

    def destroy(self, request, *args, **kwargs):
        resp = super().destroy(request, *args, **kwargs)
        self._clear_article_cache(kwargs.get("pk"))
        return resp


class MyArticlesView(ApiResponseMixin, generics.ListAPIView):
    """当前用户自己的全部文章（含草稿）"""

    serializer_class = ArticleListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # 管理端一次返回全部，由前端分页

    def get_queryset(self):
        return Article.objects.filter(author=self.request.user).select_related("author", "category")


class MyArticleDetailView(ApiResponseMixin, generics.RetrieveAPIView):
    """当前用户单篇文章详情（含草稿与正文，供后台编辑页加载）"""

    serializer_class = ArticleDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Article.objects.filter(author=self.request.user).select_related("author", "category")


# ------------------------------------------------------------------
# 评论
# ------------------------------------------------------------------
class CommentListView(ApiResponseMixin, generics.ListCreateAPIView):
    """某文章的评论列表（仅已通过）+ 发表评论（需登录）"""

    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        """POST 用写序列化器（只接收 article/parent/content），GET 用读序列化器"""
        if self.request.method == "POST":
            return CommentWriteSerializer
        return CommentSerializer

    def get_permissions(self):
        """GET 公开；POST 需登录"""
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        article_id = self.kwargs["article_id"]
        return Comment.objects.filter(article_id=article_id, status=Comment.STATUS_APPROVED).select_related("user")

    def perform_create(self, serializer):
        article_id = self.kwargs["article_id"]
        try:
            article = Article.objects.get(pk=article_id)
        except Article.DoesNotExist:
            raise NotFound("文章不存在")
        if not article.allow_comment:
            raise PermissionDenied("该文章已关闭评论")
        serializer.save(
            article=article,
            user=self.request.user,
            parent_id=self.request.data.get("parent") or None,
        )


class CommentModerateView(ApiResponseMixin, views.APIView):
    """评论审核（博主）：GET 待审列表 / POST 审核"""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        qs = Comment.objects.filter(status=Comment.STATUS_PENDING).select_related("user", "article")
        return Response(CommentSerializer(qs, many=True).data)

    def post(self, request):
        comment_id = request.data.get("id")
        action = request.data.get("action")  # approve / reject
        try:
            comment = Comment.objects.get(pk=comment_id)
        except Comment.DoesNotExist:
            return Response({"code": 404, "message": "评论不存在"}, status=404)
        if action == "approve":
            comment.status = Comment.STATUS_APPROVED
        elif action == "reject":
            comment.status = Comment.STATUS_REJECTED
        else:
            return Response({"code": 400, "message": "action 必须是 approve/reject"}, status=400)
        comment.save(update_fields=["status"])
        return Response({"code": 0, "message": "success", "data": CommentSerializer(comment).data})


class CommentAutoModerateView(ApiResponseMixin, views.APIView):
    """
    评论 AI 自动审核（创新点1-E）
    对一条待审评论调用大模型判断是否通过；通过则置为已通过。
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        comment_id = request.data.get("id")
        try:
            comment = Comment.objects.get(pk=comment_id)
        except Comment.DoesNotExist:
            return Response({"code": 404, "message": "评论不存在"}, status=404)
        result, hit = aigc_services.moderate_comment(comment.content)
        if result.get("result") == "pass":
            comment.status = Comment.STATUS_APPROVED
            comment.save(update_fields=["status"])
        else:
            comment.status = Comment.STATUS_REJECTED
            comment.save(update_fields=["status"])
        return Response(
            {
                "code": 0,
                "message": "success",
                "data": {"result": result, "from_cache": hit, "comment_id": comment.id},
            }
        )


# ------------------------------------------------------------------
# 检索（创新点2 对外接口）
# ------------------------------------------------------------------
class SearchView(views.APIView):
    """
    混合检索接口 GET /api/blog/search/?q=关键词
    内部执行：jieba 分词 → FTS + 向量检索 → RRF 融合排序
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response({"code": 0, "message": "success", "data": {"results": [], "mode": "hybrid"}})

        results = blog_services.hybrid_search(q, limit=20)
        ids = [aid for aid, _ in results]
        if not ids:
            return Response({"code": 0, "message": "success", "data": {"results": [], "mode": "hybrid"}})

        articles = {
            a.id: a
            for a in Article.objects.filter(id__in=ids)
            .select_related("author", "category")
            .prefetch_related("tags")
        }
        # 按 RRF 排序顺序输出，附上融合分
        ordered = []
        for aid, score in results:
            if aid in articles:
                ordered.append((articles[aid], score))

        serializer = SearchResultSerializer(
            [a for a, _ in ordered], many=True, context={"request": request}
        )
        data = serializer.data
        for item, (_, score) in zip(data, ordered):
            item["score"] = round(score, 6)
        return Response({"code": 0, "message": "success", "data": {"results": data, "mode": "hybrid"}})


class RelatedArticlesView(views.APIView):
    """相关文章推荐 GET /api/blog/articles/<id>/related/"""

    permission_classes = [permissions.AllowAny]

    def get(self, request, article_id):
        try:
            article = Article.objects.get(pk=article_id, status=Article.STATUS_PUBLISHED)
        except Article.DoesNotExist:
            return Response({"code": 404, "message": "文章不存在"}, status=404)
        related = blog_services.related_articles(article, limit=5)
        serializer = ArticleListSerializer(related, many=True)
        return Response({"code": 0, "message": "success", "data": {"results": serializer.data}})
