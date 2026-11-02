"""
aigc 应用：Celery 异步任务（支撑点：异步 AI 处理）
- generate_article_ai：异步为文章生成 AI 摘要 + AI 标签（草稿状态发布时触发）
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_article_ai(self, article_id: int):
    """
    异步为指定文章生成 AI 摘要与 AI 标签，并写回数据库。
    发布文章时由视图触发；失败自动重试 2 次。
    """
    from blog.models import Article

    from .services import generate_summary, generate_tags

    try:
        article = Article.objects.get(pk=article_id)
    except Article.DoesNotExist:
        logger.warning("文章 %s 不存在，跳过 AI 生成", article_id)
        return {"ok": False, "reason": "article not found"}

    changed = False
    try:
        if not article.ai_summary:
            summary, _ = generate_summary(article.content_md)
            article.ai_summary = summary
            changed = True
    except Exception as e:
        logger.error("AI 摘要生成失败 article=%s: %s", article_id, e)

    try:
        if not article.ai_tags:
            tags, _ = generate_tags(article.title, article.content_md)
            article.ai_tags = tags
            changed = True
    except Exception as e:
        logger.error("AI 标签生成失败 article=%s: %s", article_id, e)

    if changed:
        article.save(update_fields=["ai_summary", "ai_tags", "updated_at"])
    return {"ok": True, "article_id": article_id, "changed": changed}
