"""
blog 应用：功能/集成测试
覆盖：文章列表/详情/创作权限、分类树、评论审核流、
     混合检索（FTS + mock 向量）、相关推荐降级
运行：python manage.py test blog --settings=config.settings_test
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Article, Category, Comment, Tag

User = get_user_model()


class BlogAPITests(TestCase):
    """文章/分类/评论/检索接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.author = User.objects.create_user(
            username="author1", password="pass123456", is_author=True, is_staff=True
        )
        self.reader = User.objects.create_user(username="reader1", password="pass123456")
        self.cat = Category.objects.create(name="后端技术", slug="backend")
        self.tag_django = Tag.objects.create(name="Django", slug="django")
        self.tag_redis = Tag.objects.create(name="Redis", slug="redis")
        self.article = Article.objects.create(
            title="Django 与 Redis 缓存实践",
            slug="django-redis-cache",
            summary="介绍多级缓存方案",
            content_md="# 标题\n正文：Redis 缓存与 Django 结合",
            status=Article.STATUS_PUBLISHED,
            author=self.author,
            category=self.cat,
        )
        self.article.tags.add(self.tag_django, self.tag_redis)

    # ---------------- 文章列表/详情 ----------------
    def test_article_list_public(self):
        resp = self.client.get("/api/blog/articles/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["data"]["count"], 1)
        # 列表不含正文
        first = resp.data["data"]["results"][0]
        self.assertNotIn("content_md", first)

    def test_article_detail_increments_views(self):
        before = Article.objects.get(pk=self.article.pk).views
        resp = self.client.get(f"/api/blog/articles/{self.article.pk}/")
        self.assertEqual(resp.status_code, 200)
        after = Article.objects.get(pk=self.article.pk).views
        self.assertEqual(after, before + 1)
        self.assertIn("content_md", resp.data["data"])

    def test_draft_not_in_public_list(self):
        Article.objects.create(
            title="草稿",
            slug="draft-1",
            summary="",
            content_md="x",
            status=Article.STATUS_DRAFT,
            author=self.author,
            category=self.cat,
        )
        resp = self.client.get("/api/blog/articles/")
        titles = [r["title"] for r in resp.data["data"]["results"]]
        self.assertNotIn("草稿", titles)

    # ---------------- 文章创作权限 ----------------
    def test_create_article_requires_login(self):
        resp = self.client.post(
            "/api/blog/author/articles/",
            {"title": "x", "content_md": "y"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_create_and_update_article(self):
        self.client.force_authenticate(self.author)
        resp = self.client.post(
            "/api/blog/author/articles/",
            {
                "title": "新文章",
                "content_md": "内容",
                "status": 1,
                "category": self.cat.pk,
                "tags": [self.tag_django.pk],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        new_id = resp.data["data"]["id"]
        self.assertEqual(resp.data["data"]["title"], "新文章")
        self.assertEqual(resp.data["data"]["category"], self.cat.pk)

        # 非作者编辑 → 404（查询集按作者过滤）
        self.client.force_authenticate(self.reader)
        resp = self.client.patch(f"/api/blog/author/articles/{new_id}/", {"title": "hack"}, format="json")
        self.assertEqual(resp.status_code, 404)

        # 作者编辑成功
        self.client.force_authenticate(self.author)
        resp = self.client.patch(f"/api/blog/author/articles/{new_id}/", {"title": "改后标题"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["title"], "改后标题")

    # ---------------- 分类树 ----------------
    def test_category_tree_with_children(self):
        sub = Category.objects.create(name="Django 教程", slug="django-tut", parent=self.cat)
        resp = self.client.get("/api/blog/categories/")
        self.assertEqual(resp.status_code, 200)
        top = resp.data["data"]
        self.assertEqual(top[0]["id"], self.cat.pk)
        self.assertEqual(top[0]["children"][0]["id"], sub.pk)

    # ---------------- 评论审核流 ----------------
    def test_comment_flow(self):
        # 未登录不能评论
        resp = self.client.post(
            f"/api/blog/articles/{self.article.pk}/comments/", {"content": "好文"}, format="json"
        )
        self.assertEqual(resp.status_code, 401)

        # 登录发表 → 待审状态
        self.client.force_authenticate(self.reader)
        resp = self.client.post(
            f"/api/blog/articles/{self.article.pk}/comments/", {"content": "写得很棒"}, format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        cid = resp.data["data"]["id"]

        # 待审评论对外不可见
        resp = self.client.get(f"/api/blog/articles/{self.article.pk}/comments/")
        self.assertEqual(resp.data["data"]["count"], 0)

        # 博主审核通过
        self.client.force_authenticate(self.author)
        resp = self.client.post("/api/blog/comments/moderate/", {"id": cid, "action": "approve"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["status"], 1)

        # 通过后公开可见
        resp = self.client.get(f"/api/blog/articles/{self.article.pk}/comments/")
        self.assertEqual(resp.data["data"]["count"], 1)
        self.assertEqual(resp.data["data"]["results"][0]["content"], "写得很棒")

        # 拒绝评论不公开
        self.client.force_authenticate(self.reader)
        self.client.post(f"/api/blog/articles/{self.article.pk}/comments/", {"content": "垃圾"}, format="json")
        cid2 = Comment.objects.filter(content="垃圾").first().pk
        self.client.force_authenticate(self.author)
        self.client.post("/api/blog/comments/moderate/", {"id": cid2, "action": "reject"}, format="json")
        resp = self.client.get(f"/api/blog/articles/{self.article.pk}/comments/")
        self.assertEqual(resp.data["data"]["count"], 1)

    # ---------------- 混合检索（创新点2） ----------------
    def test_search_fts(self):
        resp = self.client.get("/api/blog/search/", {"q": "Django 缓存"})
        self.assertEqual(resp.status_code, 200)
        results = resp.data["data"]["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("score", results[0])

    def test_search_empty_query(self):
        resp = self.client.get("/api/blog/search/", {"q": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["results"], [])

    @patch("blog.services.embed_text", return_value=[0.1] * 1024)
    def test_search_hybrid_with_vector(self, mock_embed):
        # 给文章写向量（模拟已生成 embedding）
        a = Article.objects.get(pk=self.article.pk)
        a.embedding = [0.1] * 1024
        a.save(update_fields=["embedding"])
        resp = self.client.get("/api/blog/search/", {"q": "Django 缓存"})
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["data"]["results"]), 1)

    # ---------------- AI 字段保存（创新点1 集成到文章） ----------------
    def test_author_save_ai_fields(self):
        """作者可把 AI 摘要/标签保存到自己的文章（ai_summary/ai_tags 可写）"""
        self.client.force_authenticate(self.author)
        resp = self.client.patch(
            f"/api/blog/author/articles/{self.article.pk}/",
            {"ai_summary": "这是 AI 生成的摘要", "ai_tags": ["缓存", "Django"]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["data"]["ai_summary"], "这是 AI 生成的摘要")
        self.assertEqual(resp.data["data"]["ai_tags"], ["缓存", "Django"])
        # 仅存建议标签，不影响文章实际 M2M 标签
        self.assertEqual(set(self.article.tags.values_list("name", flat=True)), {"Django", "Redis"})

    def test_non_author_cannot_save_ai_fields(self):
        """非作者不能给文章写入 AI 字段（仍按作者过滤返回 404）"""
        self.client.force_authenticate(self.reader)
        resp = self.client.patch(
            f"/api/blog/author/articles/{self.article.pk}/",
            {"ai_summary": "hack"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_my_article_detail_contains_content(self):
        """编辑页：作者能取到自己的单篇文章详情（含草稿正文）"""
        draft = Article.objects.create(
            title="我的草稿",
            slug="my-draft",
            summary="",
            content_md="草稿正文内容",
            status=Article.STATUS_DRAFT,
            author=self.author,
            category=self.cat,
        )
        # 作者可取到（含草稿）
        self.client.force_authenticate(self.author)
        resp = self.client.get(f"/api/blog/my/articles/{draft.pk}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["data"]["content_md"], "草稿正文内容")
        self.assertEqual(resp.data["data"]["status"], Article.STATUS_DRAFT)
        # 非作者看不到别人的文章
        self.client.force_authenticate(self.reader)
        resp = self.client.get(f"/api/blog/my/articles/{draft.pk}/")
        self.assertEqual(resp.status_code, 404)

    def test_tag_ensure_creates_and_reuses(self):
        """AI 标签自动入库：已有标签复用、新标签自动创建、未登录 401"""
        # 未登录 401
        resp = self.client.post("/api/blog/tags/ensure/", {"names": ["Django"]}, format="json")
        self.assertEqual(resp.status_code, 401)
        # 登录：新标签创建 + 已有标签复用
        self.client.force_authenticate(self.author)
        resp = self.client.post(
            "/api/blog/tags/ensure/",
            {"names": ["全新标签A", "Django"]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.data["data"]
        created = [t for t in data if t["created"]]
        reused = [t for t in data if not t["created"]]
        self.assertEqual(len(created), 1)  # 全新标签A 被创建
        self.assertEqual(created[0]["name"], "全新标签A")
        self.assertEqual(len(reused), 1)  # Django 复用已有
        self.assertEqual(reused[0]["name"], "Django")
        # 再次调用应全部复用（幂等）
        resp2 = self.client.post(
            "/api/blog/tags/ensure/",
            {"names": ["全新标签A", "Django"]},
            format="json",
        )
        self.assertTrue(all(not t["created"] for t in resp2.data["data"]))

    def test_tag_ensure_slug_conflict(self):
        """AI 标签入库：不同标签 slugify 结果相同时不冲突（如 C++ -> c，再建 c 时应加后缀）"""
        self.client.force_authenticate(self.author)
        # 先建 "C++"，其 slugify 结果为 "c"
        r1 = self.client.post("/api/blog/tags/ensure/", {"names": ["C++"]}, format="json")
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(Tag.objects.get(name="C++").slug, "c")
        # 再建单字符 "c"：slug 冲突时自动加后缀，绝不能 500
        r2 = self.client.post("/api/blog/tags/ensure/", {"names": ["c"]}, format="json")
        self.assertEqual(r2.status_code, 200, r2.content)
        tag_c = Tag.objects.get(name="c")
        self.assertNotEqual(tag_c.slug, "c")  # 应为 c-2
        self.assertTrue(tag_c.slug.startswith("c"))
        # 幂等：再次 ensure "c" 仍复用，不重复创建
        r3 = self.client.post("/api/blog/tags/ensure/", {"names": ["c"]}, format="json")
        self.assertEqual(r3.status_code, 200, r3.content)
        self.assertEqual(Tag.objects.filter(name="c").count(), 1)

    def test_category_ensure_creates_and_reuses(self):
        """AI/手动分类入库：未登录 401；新分类建为顶层；同名任意层级复用；幂等；空名校验"""
        # 未登录 401
        resp = self.client.post("/api/blog/categories/ensure/", {"name": "新分类"}, format="json")
        self.assertEqual(resp.status_code, 401)
        # 登录：新分类建为顶层大类
        self.client.force_authenticate(self.author)
        resp = self.client.post("/api/blog/categories/ensure/", {"name": "新分类A"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.data["data"]
        self.assertTrue(data["created"])
        self.assertEqual(data["level"], 0)  # 顶层
        # 同名任意层级复用（先建一个同名子分类）
        child = Category.objects.create(name="Python", slug="python-child", parent=self.cat)
        resp2 = self.client.post("/api/blog/categories/ensure/", {"name": "Python"}, format="json")
        self.assertEqual(resp2.status_code, 200, resp2.content)
        d2 = resp2.data["data"]
        self.assertFalse(d2["created"])
        self.assertEqual(d2["id"], child.id)  # 复用了同名子分类
        # 幂等：再次调用同名不再新建
        resp3 = self.client.post("/api/blog/categories/ensure/", {"name": "新分类A"}, format="json")
        self.assertEqual(resp3.status_code, 200, resp3.content)
        self.assertFalse(resp3.data["data"]["created"])
        self.assertEqual(Category.objects.filter(name="新分类A").count(), 1)
        # 空名校验
        resp4 = self.client.post("/api/blog/categories/ensure/", {"name": "   "}, format="json")
        self.assertEqual(resp4.status_code, 400)

    # ---------------- 相关推荐 ----------------
    def test_related_articles_fallback(self):
        # 另一篇同分类同标签文章
        other = Article.objects.create(
            title="Redis 深入解析",
            slug="redis-deep",
            summary="",
            content_md="内容",
            status=Article.STATUS_PUBLISHED,
            author=self.author,
            category=self.cat,
        )
        other.tags.add(self.tag_redis)
        resp = self.client.get(f"/api/blog/articles/{self.article.pk}/related/")
        self.assertEqual(resp.status_code, 200)
        ids = [r["id"] for r in resp.data["data"]["results"]]
        self.assertIn(other.pk, ids)
