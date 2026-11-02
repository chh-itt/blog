"""
aigc 应用：单元/集成测试
覆盖：AI 结果缓存命中、标签 JSON 解析容错、未配置 Key 的降级行为、
      RAG 问答自动召回（无参考资料时自动混合检索 Top-5）
运行：python manage.py test aigc --settings=config.settings_test
说明：所有真实模型调用均用 mock 替代（无外网依赖）
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from blog.models import Article

from . import services
from .models import AICache


class AIGCCacheTests(TestCase):
    """ai_cache 结果缓存（创新点1 支撑）"""

    def test_get_ai_result_cache_hit(self):
        calls = []

        def generate():
            calls.append(1)
            return "result-1"

        r1, hit1 = services.get_ai_result("summary", "text", generate)
        r2, hit2 = services.get_ai_result("summary", "text", generate)
        r3, hit3 = services.get_ai_result("summary", "other", generate)
        # 相同输入：第二次命中缓存，不再调用生成函数
        self.assertEqual((r1, hit1), ("result-1", False))
        self.assertEqual((r2, hit2), ("result-1", True))
        # 不同输入：不命中
        self.assertEqual((r3, hit3), ("result-1", False))
        self.assertEqual(len(calls), 2)
        # 缓存已落库
        self.assertTrue(AICache.objects.filter(func_type="summary").exists())

    def test_force_skip_cache(self):
        calls = []

        def generate():
            calls.append(1)
            return "x"

        services.get_ai_result("summary", "t", generate)
        services.get_ai_result("summary", "t", generate, force=True)
        self.assertEqual(len(calls), 2)  # force 跳过缓存


class TagsParseTests(TestCase):
    """AI 自动标签：JSON 解析与容错"""

    def test_generate_tags_normal_json(self):
        with patch("aigc.services.chat", return_value='["Django", "缓存", "Redis"]'):
            tags, hit = services.generate_tags("标题", "正文")
            self.assertEqual(tags, ["Django", "缓存", "Redis"])
            self.assertFalse(hit)

    def test_generate_tags_wrapped_dict(self):
        with patch("aigc.services.chat", return_value='{"tags": ["Django", "Redis"]}'):
            tags, _ = services.generate_tags("标题", "正文")
            self.assertEqual(tags, ["Django", "Redis"])

    def test_generate_tags_fallback_regex(self):
        # 模型输出非 JSON 时，走正则兜底提取引号内的词
        with patch("aigc.services.chat", return_value='他推荐了 "Django" 和 "Redis" 这两个技术'):
            tags, _ = services.generate_tags("标题", "正文")
            self.assertIn("Django", tags)


class NoKeyBehaviorTests(TestCase):
    """未配置 API Key 时优雅降级（抛 RuntimeError 由视图转 503）"""

    def test_chat_without_key_raises(self):
        with patch("sysconf.services.get_deepseek_key", return_value=""):
            with self.assertRaises(RuntimeError):
                services.chat([{"role": "user", "content": "hi"}])

    def test_embed_text_without_key_raises(self):
        with patch("sysconf.services.get_embedding_key", return_value=""):
            with self.assertRaises(RuntimeError):
                services.embed_text("hello")


class ClassifyCategoryTests(TestCase):
    """AI 自动分类：JSON 解析、缓存命中、容错兜底、无 key 降级"""

    def test_classify_category_normal_json(self):
        with patch("aigc.services.chat", return_value='{"category": "后端技术"}'):
            result, hit = services.classify_category("标题", "正文", ["后端技术", "前端开发"])
            self.assertEqual(result, {"category": "后端技术"})
            self.assertFalse(hit)

    def test_classify_category_cache_hit(self):
        with patch("aigc.services.chat", return_value='{"category": "Python"}'):
            r1, hit1 = services.classify_category("标题", "正文", ["Python"])
            r2, hit2 = services.classify_category("标题", "正文", ["Python"])
            self.assertFalse(hit1)
            self.assertTrue(hit2)  # 相同输入命中 ai_cache

    def test_classify_category_fallback_regex(self):
        with patch("aigc.services.chat", return_value='推荐分类是 "Rust 编程"'):
            result, _ = services.classify_category("标题", "正文")
            self.assertEqual(result["category"], "Rust 编程")

    def test_classify_category_without_key_raises(self):
        with patch("sysconf.services.get_deepseek_key", return_value=""):
            with self.assertRaises(RuntimeError):
                services.classify_category("标题", "正文")


class RagQaAutoRecallTests(TestCase):
    """RAG 问答自动召回：无参考资料时自动混合检索 Top-5（创新点1×创新点2 联动）"""

    def setUp(self):
        User = get_user_model()
        author = User.objects.create_user(username="author", password="pwd123456")
        self.article = Article.objects.create(
            title="Django 混合检索原理",
            content_md="本文介绍 PostgreSQL 全文检索与 pgvector 语义检索的 RRF 融合方案。",
            status=Article.STATUS_PUBLISHED,
            author=author,
        )

    def test_auto_recall_injects_context(self):
        # 未传参考资料：应自动调用混合检索，并把召回片段拼进系统提示词
        with patch("blog.services.hybrid_search", return_value=[(self.article.id, 0.5)]), patch(
            "aigc.services.chat", return_value="根据资料回答"
        ) as mock_chat:
            answer, hit = services.rag_qa("什么是混合检索")
        self.assertEqual(answer, "根据资料回答")
        self.assertFalse(hit)
        system_msg = mock_chat.call_args[0][0][0]["content"]
        self.assertIn("Django 混合检索原理", system_msg)

    def test_manual_context_skips_recall(self):
        # 已手动粘贴参考资料：不再触发自动检索
        with patch("blog.services.hybrid_search") as mock_search, patch(
            "aigc.services.chat", return_value="ok"
        ):
            answer, _ = services.rag_qa("问题", context_text="手动粘贴的资料")
        mock_search.assert_not_called()
        self.assertEqual(answer, "ok")

    def test_recall_failure_degrades_to_refusal(self):
        # 检索异常：不调用大模型，直接固定拒答（防止模型用自身知识自由发挥）
        with patch("blog.services.hybrid_search", side_effect=Exception("db down")), patch(
            "aigc.services.chat"
        ) as mock_chat:
            answer, hit = services.rag_qa("问题")
        self.assertIn("资料中未找到", answer)
        self.assertFalse(hit)
        mock_chat.assert_not_called()

    def test_recall_empty_result_returns_refusal(self):
        # 召回结果为空：同样不调用大模型，直接拒答
        with patch("blog.services.hybrid_search", return_value=[]), patch(
            "aigc.services.chat"
        ) as mock_chat:
            answer, hit = services.rag_qa("冷门问题")
        self.assertIn("资料中未找到", answer)
        self.assertFalse(hit)
        mock_chat.assert_not_called()

    def test_strict_rag_prompt_rule(self):
        # 有参考资料时：系统提示词包含强约束规则（唯一信息来源 + 无关即拒答）
        with patch("blog.services.hybrid_search", return_value=[(self.article.id, 0.5)]), patch(
            "aigc.services.chat", return_value="ok"
        ) as mock_chat:
            services.rag_qa("什么是混合检索")
        system_msg = mock_chat.call_args[0][0][0]["content"]
        self.assertIn("唯一的信息来源", system_msg)
        self.assertIn("资料中未找到", system_msg)
