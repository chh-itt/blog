"""
stats 应用：序列化器（统计面板响应）
"""

from rest_framework import serializers


class TrendPointSerializer(serializers.Serializer):
    """趋势图单点"""

    date = serializers.CharField(label="日期")
    views = serializers.IntegerField(label="浏览量")
    articles = serializers.IntegerField(label="发文数")


class CategoryStatsSerializer(serializers.Serializer):
    """分类统计"""

    name = serializers.CharField(label="分类名")
    count = serializers.IntegerField(label="文章数")


class HotArticleSerializer(serializers.Serializer):
    """热门文章"""

    id = serializers.IntegerField()
    title = serializers.CharField()
    views = serializers.IntegerField()
    likes = serializers.IntegerField()


class OverviewSerializer(serializers.Serializer):
    """总览卡片数据"""

    article_count = serializers.IntegerField(label="文章总数")
    comment_count = serializers.IntegerField(label="评论总数")
    user_count = serializers.IntegerField(label="用户总数")
    visit_count = serializers.IntegerField(label="总访问量")
    pending_comment_count = serializers.IntegerField(label="待审评论数")
    total_views = serializers.IntegerField(label="文章总浏览量")
