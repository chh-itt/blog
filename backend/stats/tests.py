"""
stats 应用：功能/集成测试
覆盖：统计接口权限、总览数据、趋势形状、热门文章
运行：python manage.py test stats --settings=config.settings_test
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from blog.models import Article, Category

User = get_user_model()


class StatsTests(TestCase):
    """博主统计面板接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username="admin1", password="pass123456", is_staff=True)
        self.normal = User.objects.create_user(username="normal1", password="pass123456")
        self.cat = Category.objects.create(name="测试分类", slug="test-cat")

    def _make_articles(self):
        author = User.objects.create_user(username="author2", password="pass123456")
        for i in range(3):
            Article.objects.create(
                title=f"热门文章{i}",
                slug=f"hot-{i}",
                summary="",
                content_md="内容",
                status=Article.STATUS_PUBLISHED,
                author=author,
                category=self.cat,
                views=10 - i,
            )

    # ---------------- 权限 ----------------
    def test_stats_requires_staff(self):
        # 匿名 → 401
        resp = self.client.get("/api/stats/overview/")
        self.assertEqual(resp.status_code, 401)
        # 普通用户 → 403
        self.client.force_authenticate(self.normal)
        resp = self.client.get("/api/stats/overview/")
        self.assertEqual(resp.status_code, 403)

    # ---------------- 数据 ----------------
    def test_overview_data(self):
        self._make_articles()
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/stats/overview/")
        self.assertEqual(resp.status_code, 200)
        data = resp.data["data"]
        for key in (
            "article_count",
            "comment_count",
            "user_count",
            "visit_count",
            "pending_comment_count",
            "total_views",
        ):
            self.assertIn(key, data)
        self.assertEqual(data["article_count"], 3)

    def test_trend_shape_and_days_clamp(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/stats/trend/", {"days": 7})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["data"]), 7)
        # 日期从旧到新
        dates = [r["date"] for r in resp.data["data"]]
        self.assertEqual(dates, sorted(dates))
        # days 上限 90
        resp2 = self.client.get("/api/stats/trend/", {"days": 999})
        self.assertEqual(len(resp2.data["data"]), 90)

    def test_categories_distribution(self):
        self._make_articles()
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/stats/categories/")
        self.assertEqual(resp.status_code, 200)
        rows = resp.data["data"]
        self.assertEqual(rows[0]["name"], "测试分类")
        self.assertEqual(rows[0]["count"], 3)

    def test_hot_articles_order(self):
        self._make_articles()
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/stats/hot-articles/")
        self.assertEqual(resp.status_code, 200)
        rows = resp.data["data"]
        self.assertEqual(rows[0]["title"], "热门文章0")  # views=10 最高
        self.assertEqual(rows[0]["views"], 10)
        self.assertEqual(len(rows), 3)
