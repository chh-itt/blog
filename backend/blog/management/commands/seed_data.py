"""
blog 应用：演示数据填充命令
用法: python manage.py seed_data
生成：二级分类、标签、若干篇示例文章（含 search_vector），
配合 Celery/AI Key 配置可自动生成 AI 摘要与标签。
"""

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Article, Category, Tag

User = get_user_model()

# 演示文章数据：(分类, 标题, 正文片段)
DEMO_ARTICLES = [
    (
        "Python",
        "Django 6.0 新特性详解：异步 ORM 与连接池",
        "Django 6.0 引入了全新的异步 ORM 能力，配合 psycopg3 连接池，可以在高并发场景下显著降低数据库连接开销。本文从实战角度对比了同步与异步查询的性能差异，并给出了生产环境的推荐配置。",
    ),
    (
        "Python",
        "DRF 实战：用 Django REST Framework 构建高质量 API",
        "Django REST Framework 是构建 Web API 的事实标准。本文介绍 ModelSerializer、视图集、权限系统与限流配置的最佳实践，帮助你快速搭建规范、安全的 RESTful 接口。",
    ),
    (
        "Python",
        "JWT 认证原理与 SimpleJWT 集成指南",
        "JWT（JSON Web Token）是前后端分离架构下最流行的认证方案。本文讲解 JWT 的签名原理、过期与刷新机制，并演示如何与 SimpleJWT 库集成，实现安全的用户认证。",
    ),
    (
        "前端开发",
        "Vue3 组合式 API 入门：从 Options 到 Composition",
        "Vue3 的组合式 API 提供了更灵活的代码组织方式。本文通过一个博客前端项目，演示 setup 语法糖、响应式原理与组合式函数的复用技巧。",
    ),
    (
        "前端开发",
        "Element Plus 表单校验与表格组件的企业级用法",
        "Element Plus 是 Vue3 生态最流行的 UI 组件库。本文深入讲解表单校验规则、动态表格渲染与分页组件的组合使用，并分享封装经验。",
    ),
    (
        "前端开发",
        "ECharts 数据可视化：从柱状图到仪表盘",
        "ECharts 是功能强大的前端可视化库。本文以博客后台统计面板为例，演示折线图、饼图、柱状图的配置方法，以及大数据量的性能优化技巧。",
    ),
    (
        "数据库",
        "PostgreSQL 全文检索实战：GIN 索引与中文分词",
        "全文检索是信息系统的核心能力。本文介绍 PostgreSQL 的 tsvector/tsquery 机制与 GIN 索引原理，并讨论中文场景下的 jieba 分词集成方案。",
    ),
    (
        "数据库",
        "pgvector 语义检索：用向量数据库实现相似文章推荐",
        "pgvector 为 PostgreSQL 带来了向量检索能力。本文演示 HNSW 索引的创建、余弦相似度的计算，以及如何用它实现'相关文章推荐'功能。",
    ),
    (
        "数据库",
        "Redis 多级缓存架构：从页面缓存到结果缓存",
        "缓存是性能优化的第一手段。本文介绍 Redis 在博客系统中的多级缓存设计：热点文章缓存、AI 结果缓存与数据库查询缓存，并给出缓存击穿与雪崩的应对方案。",
    ),
    (
        "数据库",
        "数据库索引优化：从 B+ 树到复合索引",
        "索引是数据库性能的基石。本文从 B+ 树原理出发，讲解复合索引的最左前缀原则、覆盖索引与索引下推，帮助你写出更快的 SQL。",
    ),
    (
        "AI 应用",
        "大模型 API 接入实战：Prompt 工程与结果缓存",
        "接入大模型 API 并非简单调用。本文分享 DeepSeek API 的接入经验、Prompt 工程的实用技巧，以及用数据库缓存 AI 结果以节省成本的方案。",
    ),
    (
        "AI 应用",
        "RAG 检索增强生成：让大模型回答私有知识",
        "RAG（检索增强生成）是当前最热门的大模型应用范式。本文结合混合检索技术，讲解如何让大模型基于博客内容回答用户问题。",
    ),
    (
        "AI 应用",
        "AI 内容审核：自动识别垃圾评论与违规文本",
        "内容安全是社区类系统的必备能力。本文介绍如何用大模型实现评论自动审核，包括敏感词提示、审核状态机与人工兜底流程。",
    ),
    (
        "运维部署",
        "Celery 异步任务：从定时任务到消息队列",
        "Celery 是 Python 最流行的异步任务框架。本文介绍 Celery 与 Redis 的集成、任务的优先级与重试机制，以及如何用 Flower 监控任务队列。",
    ),
    (
        "运维部署",
        "Windows 环境部署 Django：从零搭建生产级服务",
        "本文记录在 Windows 环境下部署 Django + PostgreSQL + Redis 的全过程，涵盖虚拟环境、服务自启动、日志轮转与反向代理配置。",
    ),
]


class Command(BaseCommand):
    help = "填充演示数据：分类、标签、示例文章"

    def handle(self, *args, **options):
        # 0. 演示账号（幂等：不存在则创建，存在则更新密码/角色，保证文档默认账号可登录）
        for username, password, extra in [
            ("admin", "admin123456", {"is_superuser": True, "is_staff": True, "is_author": True, "nickname": "博主小张"}),
            ("testuser", "test123456", {"is_author": False, "nickname": "测试用户"}),
        ]:
            user, _ = User.objects.get_or_create(username=username, defaults=extra)
            user.set_password(password)
            for k, v in extra.items():
                setattr(user, k, v)
            user.save()
        self.stdout.write(self.style.SUCCESS("演示账号完成：admin/admin123456、testuser/test123456"))

        # 1. 分类（两级）
        parent_map = {}
        parent_names = ["Python", "前端开发", "数据库", "AI 应用", "运维部署"]
        child_map = {
            "Python": ["Django", "DRF", "异步编程"],
            "前端开发": ["Vue3", "组件库", "数据可视化"],
            "数据库": ["PostgreSQL", "Redis", "索引优化"],
            "AI 应用": ["大模型", "RAG", "内容审核"],
            "运维部署": ["Celery", "部署上线"],
        }
        for name in parent_names:
            cat, _ = Category.objects.get_or_create(name=name, parent=None)
            parent_map[name] = cat
            for child in child_map.get(name, []):
                Category.objects.get_or_create(name=child, parent=cat)
        self.stdout.write(self.style.SUCCESS(f"分类完成：{Category.objects.count()} 个"))

        # 2. 标签
        tag_names = [
            "Django", "DRF", "JWT", "Vue3", "Element Plus", "ECharts",
            "PostgreSQL", "pgvector", "Redis", "索引", "大模型", "RAG",
            "内容审核", "Celery", "部署", "缓存", "全文检索", "语义检索",
        ]
        for name in tag_names:
            Tag.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS(f"标签完成：{Tag.objects.count()} 个"))

        # 3. 文章
        author = User.objects.filter(is_superuser=True).first() or User.objects.first()
        tags = list(Tag.objects.all())
        created = 0
        for cat_name, title, body in DEMO_ARTICLES:
            if Article.objects.filter(title=title).exists():
                continue
            cat = Category.objects.filter(name=cat_name).first() or Category.objects.first()
            article = Article.objects.create(
                title=title,
                summary=body[:80] + "...",
                content_md=f"# {title}\n\n{body}\n\n## 小节\n\n- 要点一：实践驱动\n- 要点二：性能优先\n\n```python\nprint('hello blog')\n```",
                content_html=f"<h1>{title}</h1><p>{body}</p>",
                status=Article.STATUS_PUBLISHED,
                allow_comment=True,
                author=author,
                category=cat,
                views=random.randint(50, 2000),
                likes=random.randint(5, 300),
                published_at=timezone.now() - timezone.timedelta(days=random.randint(0, 30)),
            )
            # 随机挂 2~4 个标签
            article.tags.set(random.sample(tags, k=min(4, len(tags))))
            created += 1
        self.stdout.write(self.style.SUCCESS(f"文章完成：新增 {created} 篇，共 {Article.objects.count()} 篇"))

        self.stdout.write(self.style.SUCCESS("演示数据填充完毕！"))
