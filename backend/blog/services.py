"""
blog 应用：检索服务层（创新点2 核心）
=====================================================================
实现"全文检索 + 语义检索 + RRF 融合排序"三段式混合检索：

1. 全文检索（FTS）
   - 中文分词：后端 jieba 分词（避免 Windows 编译 zhparser 的坑）
   - 索引：PostgreSQL GIN 倒排索引（search_vector 字段）
2. 语义检索
   - 用 bge-m3 把查询文本转成向量（1024 维）
   - pgvector HNSW 索引加速最近邻查询
3. RRF（Reciprocal Rank Fusion）融合
   - score = Σ 1/(k + rank)，k 取 60，综合两个检索结果排序
=====================================================================
"""

import jieba

from django.db import connection
from django.db.models import Q

from aigc.services import embed_text
from .models import Article

RRF_K = 60  # RRF 融合常数


# ------------------------------------------------------------------
# 中文分词工具
# ------------------------------------------------------------------
def tokenize(text: str) -> list:
    """jieba 分词，返回词列表（过滤空白与单字噪声）"""
    words = [w.strip() for w in jieba.cut(text) if w.strip()]
    # 去掉纯标点/单字（保留长度>=2 的词，提升检索质量）
    return [w for w in words if len(w) >= 2]


def build_query_tsquery(text: str) -> str:
    """把查询文本分词后用 & 连接，构造 tsquery"""
    words = tokenize(text)
    if not words:
        return ""
    return " & ".join(words)


# ------------------------------------------------------------------
# 检索一：全文检索（PostgreSQL FTS + GIN 索引）
# ------------------------------------------------------------------
def fts_search(query_text: str, limit: int = 30):
    """
    用 PostgreSQL 全文检索查询文章。
    返回 [(article_id, rank), ...] 按相关度降序。
    中文策略：jieba 分词后以 'simple' 配置构造 tsquery。
    """
    tsquery = build_query_tsquery(query_text)
    if not tsquery:
        return []
    # 用 raw SQL 走 GIN 索引 + ts_rank 打分
    sql = """
        SELECT id, ts_rank(search_vector, plainto_tsquery('simple', %s)) AS rank
        FROM blog_article
        WHERE status = 1
          AND search_vector @@ plainto_tsquery('simple', %s)
        ORDER BY rank DESC
        LIMIT %s
    """
    with connection.cursor() as cur:
        cur.execute(sql, [tsquery, tsquery, limit])
        rows = cur.fetchall()
    return [(r[0], float(r[1])) for r in rows]


# ------------------------------------------------------------------
# 检索二：语义检索（pgvector）
# ------------------------------------------------------------------
def vector_search(query_text: str, limit: int = 30):
    """
    用 pgvector 余弦/欧式距离找语义相似文章。
    返回 [(article_id, similarity), ...] 按距离升序（越近越相似）。
    若未配置 embedding API Key 或查询失败，返回空列表（降级为纯全文检索）。
    """
    try:
        query_vec = embed_text(query_text)
    except RuntimeError:
        return []
    except Exception:
        return []

    # 余弦距离 <=> 越小越相似（bge-m3 官方建议余弦相似度；HNSW 索引 opclass 已用 vector_cosine_ops 与之匹配）
    sql = """
        SELECT id, 1 - (embedding <=> %s::vector) AS similarity
        FROM blog_article
        WHERE status = 1 AND embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"
    try:
        with connection.cursor() as cur:
            cur.execute(sql, [vec_str, vec_str, limit])
            rows = cur.fetchall()
    except Exception:
        return []
    return [(r[0], float(r[1])) for r in rows]


# ------------------------------------------------------------------
# RRF 融合排序
# ------------------------------------------------------------------
def rrf_merge(*ranked_lists: list, k: int = RRF_K):
    """
    输入多个 [(id, score), ...] 列表，输出融合后的 [(id, rrf_score), ...]。
    每个列表按各自相关度排序，位置即 rank（从 1 开始）。
    RRF 公式：score(id) = Σ_i 1/(k + rank_i(id))
    """
    score_map = {}
    for ranked in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked, start=1):
            score_map[doc_id] = score_map.get(doc_id, 0.0) + 1.0 / (k + rank)
    # 按融合分降序
    merged = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
    return merged


# ------------------------------------------------------------------
# 对外统一入口：混合检索
# ------------------------------------------------------------------
def hybrid_search(query_text: str, limit: int = 20):
    """
    混合检索主流程：
    1. 全文检索候选集
    2. 语义检索候选集（失败则降级）
    3. RRF 融合
    返回 [(article_id, rrf_score), ...]
    """
    fts_results = fts_search(query_text, limit=limit * 2)
    vec_results = vector_search(query_text, limit=limit * 2)

    if not fts_results and not vec_results:
        return []

    merged = rrf_merge(fts_results, vec_results)
    # 融合后取 top-N（保留融合分）
    return merged[:limit]


# ------------------------------------------------------------------
# 相关文章推荐（基于语义相似度）
# ------------------------------------------------------------------
def related_articles(article, limit: int = 5):
    """
    给定一篇文章，推荐相关文章：
    1. 优先用 embedding 做语义近邻（向量距离，创新点2）
    2. 无向量或结果不足时，降级为"标签 + 分类"重叠推荐（保证功能可用）
    用于文章详情页"相关推荐"模块。
    """
    ids = []
    # 第一步：语义相似（有 embedding 时才执行）
    if article.embedding:
        vec_str = "[" + ",".join(str(float(x)) for x in article.embedding) + "]"
        sql = """
            SELECT id FROM blog_article
            WHERE status = 1 AND id != %s AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        try:
            with connection.cursor() as cur:
                cur.execute(sql, [article.id, vec_str, limit])
                rows = cur.fetchall()
        except Exception:
            rows = []
        ids = [r[0] for r in rows]

    # 第二步：标签/分类重叠后备推荐（语义结果不足时补齐）
    if len(ids) < limit:
        fallback = (
            Article.objects.filter(
                Q(status=Article.STATUS_PUBLISHED)
                & ~Q(id=article.id)
                & (Q(category=article.category) | Q(tags__in=article.tags.all()))
            )
            .exclude(id__in=ids)
            .distinct()
            .order_by("-views")[: limit - len(ids)]
        )
        ids += [a.id for a in fallback]

    if not ids:
        return []
    # 保持顺序
    objs = {a.id: a for a in Article.objects.filter(id__in=ids)}
    return [objs[i] for i in ids if i in objs]
