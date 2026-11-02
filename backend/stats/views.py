"""
stats 应用：视图（博主数据统计，供 ECharts 面板使用）
- /api/stats/overview/      总览卡片
- /api/stats/trend/         近 N 天访问趋势
- /api/stats/categories/    分类文章分布
- /api/stats/hot-articles/  热门文章 TOP10
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone

from rest_framework import permissions, views
from rest_framework.response import Response

from blog.models import Article, Comment

from .models import VisitLog

User = get_user_model()


class StatsBaseView(views.APIView):
    """统计接口仅博主可访问"""

    permission_classes = [permissions.IsAdminUser]

    def ok(self, data):
        return Response({"code": 0, "message": "success", "data": data})


class OverviewView(StatsBaseView):
    """总览数据"""

    def get(self, request):
        data = {
            "article_count": Article.objects.count(),
            "comment_count": Comment.objects.count(),
            "user_count": User.objects.count(),
            "visit_count": VisitLog.objects.count(),
            "pending_comment_count": Comment.objects.filter(status=Comment.STATUS_PENDING).count(),
            "total_views": Article.objects.aggregate(total=Sum("views"))["total"] or 0,
        }
        return self.ok(data)


class TrendView(StatsBaseView):
    """近 N 天（默认 14 天）访问量与发文数趋势"""

    def get(self, request):
        days = int(request.query_params.get("days", 14))
        days = max(1, min(days, 90))
        today = timezone.localdate()

        # 逐天统计访问日志
        visits = (
            VisitLog.objects.filter(created_at__date__gte=today - timedelta(days=days - 1))
            .extra(select={"day": "date(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
        )
        visit_map = {str(v["day"]): v["count"] for v in visits}

        # 逐天统计发文数
        articles = (
            Article.objects.filter(published_at__date__gte=today - timedelta(days=days - 1))
            .extra(select={"day": "date(published_at)"})
            .values("day")
            .annotate(count=Count("id"))
        )
        article_map = {str(a["day"]): a["count"] for a in articles}

        trend = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            key = str(d)
            trend.append({"date": key, "views": visit_map.get(key, 0), "articles": article_map.get(key, 0)})
        return self.ok(trend)


class CategoriesView(StatsBaseView):
    """各分类文章数量分布（饼图）"""

    def get(self, request):
        rows = (
            Article.objects.filter(status=Article.STATUS_PUBLISHED)
            .values("category__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        data = [{"name": r["category__name"] or "未分类", "count": r["count"]} for r in rows]
        return self.ok(data)


class HotArticlesView(StatsBaseView):
    """热门文章 TOP10（按浏览量）"""

    def get(self, request):
        rows = Article.objects.filter(status=Article.STATUS_PUBLISHED).order_by("-views", "-likes")[:10]
        data = [{"id": a.id, "title": a.title, "views": a.views, "likes": a.likes} for a in rows]
        return self.ok(data)
