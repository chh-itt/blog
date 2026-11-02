"""
blog 应用：性能对比实验（论文第 6 章数据采集）
=====================================================================
运行：python manage.py benchmark  （需先启动后端服务 8100）
对比实验：
A. Redis 多级缓存加速：文章列表「无缓存」vs「命中缓存」响应时间
B. GIN 倒排索引 vs LIKE 全表扫描：在 3 万条临时数据上对比（测完自动清理，不污染演示库）
C. 混合检索全链路：jieba 分词 + FTS + 向量 + RRF 融合耗时与召回
结果将打印到控制台，可直接引用到论文"性能测试与分析"章节。
=====================================================================
"""

import random
import statistics
import sys
import time

import requests
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection

from blog import services as blog_services

API = "http://127.0.0.1:8100/api"

# Windows 控制台默认 GBK，强制 UTF-8 输出避免中文乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def timed(fn, n=10):
    """重复执行 n 次，返回 (平均耗时ms, 最快耗时ms)"""
    samples = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    return statistics.mean(samples), min(samples)


class Command(BaseCommand):
    help = "性能对比实验：Redis 缓存 / GIN 索引 / 混合检索"

    def handle(self, *args, **options):
        self.stdout.write("=" * 62)
        self.stdout.write("        性能对比实验（论文第 6 章数据采集）")
        self.stdout.write("=" * 62)

        self.benchmark_redis_cache()
        self.benchmark_gin_vs_like()
        self.benchmark_hybrid_search()
        self.stdout.write("=" * 62)
        self.stdout.write("实验完成：临时数据已清理，演示库未受影响")

    # --------------------------------------------------------------
    # A. Redis 缓存加速
    # --------------------------------------------------------------
    def benchmark_redis_cache(self):
        self.stdout.write("\n[A] Redis 多级缓存加速 —— 文章列表接口")
        cache.clear()
        # 冷启动：无缓存
        t0 = time.perf_counter()
        requests.get(f"{API}/blog/articles/?page=1")
        cold = (time.perf_counter() - t0) * 1000
        # 热启动：命中缓存
        mean, best = timed(lambda: requests.get(f"{API}/blog/articles/?page=1"))
        ratio = cold / max(mean, 0.01)
        self.stdout.write(
            f"  首次请求(无缓存): {cold:.1f} ms    "
            f"命中缓存平均: {mean:.1f} ms (最快 {best:.1f} ms)    "
            f"加速 ≈ {ratio:.1f}×"
        )

    # --------------------------------------------------------------
    # B. GIN 索引 vs LIKE 全表扫描（临时大数据表）
    # --------------------------------------------------------------
    def benchmark_gin_vs_like(self):
        self.stdout.write("\n[B] GIN 倒排索引 vs LIKE 全表扫描（3 万条临时数据）")
        random.seed(42)
        words = [
            "Django", "Redis", "缓存", "数据库", "人工智能", "前端", "架构",
            "PostgreSQL", "向量", "检索", "JWT", "认证", "Celery", "异步",
            "大模型", "API", "Vue", "Element", "ECharts", "Markdown",
        ]
        rows = []
        for i in range(30000):
            content = " ".join(random.choices(words, k=8))
            rows.append((f"测试文章{i}", content, content))

        with connection.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS bench_docs")
            cur.execute(
                "CREATE TABLE bench_docs (id serial PRIMARY KEY, title text, content text, search_vector tsvector)"
            )
            cur.executemany(
                "INSERT INTO bench_docs (title, content, search_vector) VALUES (%s, %s, to_tsvector('simple', %s))",
                rows,
            )
            connection.commit()

            # 无索引：LIKE 模糊匹配（全表扫描）
            def like_query():
                with connection.cursor() as c:
                    c.execute("SELECT count(*) FROM bench_docs WHERE content LIKE %s", ["%Django%"])
                    c.fetchone()

            t_like, _ = timed(like_query, n=5)

            # 建 GIN 倒排索引
            cur.execute("CREATE INDEX bench_docs_gin ON bench_docs USING gin(search_vector)")
            connection.commit()

            # 有索引：全文检索 @@
            def gin_query():
                with connection.cursor() as c:
                    c.execute(
                        "SELECT count(*) FROM bench_docs WHERE search_vector @@ plainto_tsquery('simple', %s)",
                        ["Django"],
                    )
                    c.fetchone()

            t_gin, _ = timed(gin_query, n=5)

            # 清理临时表
            cur.execute("DROP TABLE bench_docs")
            connection.commit()

        speedup = t_like / max(t_gin, 0.001)
        self.stdout.write(
            f"  关键词 'Django':  GIN 索引 {t_gin:.4f} ms  vs  LIKE 全表扫描 {t_like:.4f} ms   "
            f"(索引快 {speedup:.1f}×)"
        )

    # --------------------------------------------------------------
    # C. 混合检索全链路
    # --------------------------------------------------------------
    def benchmark_hybrid_search(self):
        self.stdout.write("\n[C] 混合检索全链路（jieba 分词 + FTS + 向量 + RRF）")
        queries = ["Django", "Redis 缓存", "PostgreSQL 数据库"]
        for q in queries:
            result = blog_services.hybrid_search(q, limit=10)
            mean, best = timed(lambda: blog_services.hybrid_search(q, limit=10))
            self.stdout.write(f"  查询 '{q}':  平均 {mean:.1f} ms (最快 {best:.1f} ms)  召回 {len(result)} 条")
