"""
blog 应用：核心业务模型
- Category 分类（MPTT 树形结构，支持二级分类）
- Tag 标签
- Article 文章（含全文检索向量字段 + pgvector 语义向量字段）
- Comment 评论（含审核状态）
"""

import re

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from config.settings import EMBEDDING_DIM
from mptt.models import MPTTModel, TreeForeignKey
from pgvector.django import HnswIndex, VectorField


class Category(MPTTModel):
    """
    文章分类（支持父子二级结构）
    使用 django-mptt 实现树形结构，字段：parent/lft/rght/tree_id/level
    """

    name = models.CharField("分类名", max_length=50)
    slug = models.SlugField("URL标识", max_length=100, unique=True, blank=True)
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父分类",
    )
    description = models.CharField("描述", max_length=255, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = "分类"
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        """自动生成 slug（保留中文；空则退化为分类名）"""
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True) or self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """文章标签（多对多）"""

    name = models.CharField("标签名", max_length=50, unique=True)
    slug = models.SlugField("URL标识", max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "标签"
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        """
        自动生成 slug；与已有 slug 冲突时追加后缀保证唯一
        （例：标签 "C++" 的 slugify 结果是 "c"，再建标签 "c" 时 slug 应为 "c-2"）
        """
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or self.name
            slug = base
            i = 2
            while Tag.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(models.Model):
    """
    文章模型（核心表）
    - content_md：Markdown 原文
    - content_html：渲染后的 HTML（前端展示用，入库前用 bleach 清洗防 XSS）
    - search_vector：全文检索向量（创新点2，GIN 索引加速）
    - embedding：语义向量（创新点2，pgvector 字段，维度与 embedding 模型一致）
    """

    # 文章状态
    STATUS_DRAFT = 0
    STATUS_PUBLISHED = 1
    STATUS_CHOICES = (
        (STATUS_DRAFT, "草稿"),
        (STATUS_PUBLISHED, "已发布"),
    )

    title = models.CharField("标题", max_length=200)
    slug = models.SlugField("URL标识", max_length=220, unique=True, blank=True)
    summary = models.TextField("摘要", blank=True)
    content_md = models.TextField("Markdown正文")
    content_html = models.TextField("渲染后HTML", blank=True)
    cover = models.URLField("封面图", max_length=255, blank=True)
    status = models.SmallIntegerField("状态", choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_top = models.BooleanField("置顶", default=False)
    allow_comment = models.BooleanField("允许评论", default=True)

    # 统计字段
    views = models.PositiveIntegerField("浏览量", default=0)
    likes = models.PositiveIntegerField("点赞数", default=0)

    # AI 生成内容（创新点1）
    ai_summary = models.TextField("AI摘要", blank=True)
    ai_tags = models.JSONField("AI标签", default=list, blank=True)

    # 检索相关（创新点2）
    search_vector = SearchVectorField(null=True, editable=False)
    # pgvector 向量字段：dimensions 与 embedding 模型输出维度一致（EMBEDDING_DIM=1024）
    embedding = VectorField(
        "语义向量",
        dimensions=EMBEDDING_DIM,
        null=True,
        blank=True,
        editable=False,
    )

    # 关联
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles", verbose_name="分类"
    )
    tags = models.ManyToManyField(Tag, related_name="articles", blank=True, verbose_name="标签")
    author = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="articles", verbose_name="作者"
    )

    # 时间戳
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    published_at = models.DateTimeField("发布时间", null=True, blank=True)

    class Meta:
        verbose_name = "文章"
        verbose_name_plural = verbose_name
        ordering = ["-is_top", "-published_at"]
        indexes = [
            models.Index(fields=["status", "published_at"], name="idx_article_status_pub"),
        ]
        # 全文检索 GIN 索引
        indexes.append(GinIndex(fields=["search_vector"], name="idx_article_search"))
        # 语义向量 HNSW 索引（创新点2：加速向量近邻查询；vector_cosine_ops 对应余弦距离 <=>，与查询算子一致）
        indexes.append(
            HnswIndex(
                fields=["embedding"],
                name="idx_article_embedding",
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        )

    def save(self, *args, **kwargs):
        """自动生成 slug；发布时记录发布时间；更新全文检索向量"""
        from django.db import connection

        from .services import tokenize

        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or "article"
            self.slug = base
            # 处理 slug 冲突（追加序号）
            counter = 1
            while Article.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{counter}"
                counter += 1
        if self.status == self.STATUS_PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

        # 全文检索向量：jieba 分词后写入 search_vector（GIN 索引加速）
        try:
            words = tokenize(f"{self.title} {self.summary} {self.content_md}")
            joined = " ".join(words)
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE blog_article SET search_vector = to_tsvector('simple', %s) WHERE id = %s",
                    [joined, self.pk],
                )
        except Exception:
            pass  # 检索向量失败不影响保存主流程

        # 发布时异步触发 AI 摘要/标签生成（创新点1 + Celery 支撑点）
        if self.status == self.STATUS_PUBLISHED and (not self.ai_summary or not self.ai_tags):
            try:
                from aigc.tasks import generate_article_ai

                generate_article_ai.delay(self.pk)
            except Exception:
                pass

    def __str__(self):
        return self.title


class Comment(models.Model):
    """文章评论（支持楼中楼回复 + 审核状态）"""

    # 审核状态
    STATUS_PENDING = 0
    STATUS_APPROVED = 1
    STATUS_REJECTED = 2
    STATUS_CHOICES = (
        (STATUS_PENDING, "待审核"),
        (STATUS_APPROVED, "已通过"),
        (STATUS_REJECTED, "已拒绝"),
    )

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="comments", verbose_name="文章"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies", verbose_name="父评论"
    )
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="comments", verbose_name="评论者"
    )
    content = models.TextField("内容")
    status = models.SmallIntegerField("审核状态", choices=STATUS_CHOICES, default=STATUS_PENDING)
    likes = models.PositiveIntegerField("点赞数", default=0)
    created_at = models.DateTimeField("评论时间", auto_now_add=True)

    class Meta:
        verbose_name = "评论"
        verbose_name_plural = verbose_name
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} 评论 {self.article}: {self.content[:20]}"
