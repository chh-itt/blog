"""
aigc 应用：序列化器
"""

from rest_framework import serializers


class AIGCRequestSerializer(serializers.Serializer):
    """AI 功能通用请求参数"""

    text = serializers.CharField(max_length=12000, allow_blank=False, label="输入文本")
    force = serializers.BooleanField(required=False, default=False, label="是否跳过缓存")


class SummaryRequestSerializer(AIGCRequestSerializer):
    """自动摘要请求（text=正文）"""


class TagsRequestSerializer(serializers.Serializer):
    """自动标签请求"""

    title = serializers.CharField(max_length=200, label="标题")
    content = serializers.CharField(max_length=8000, allow_blank=True, default="", label="正文")
    force = serializers.BooleanField(required=False, default=False)


class WriterRequestSerializer(serializers.Serializer):
    """写作助手请求"""

    prompt = serializers.CharField(max_length=8000, label="写作提示词")
    force = serializers.BooleanField(required=False, default=False)


class QaRequestSerializer(serializers.Serializer):
    """RAG 问答请求"""

    question = serializers.CharField(max_length=1000, label="问题")
    context = serializers.CharField(max_length=12000, allow_blank=True, default="", label="上下文资料")
    force = serializers.BooleanField(required=False, default=False)


class ModerateRequestSerializer(serializers.Serializer):
    """评论审核请求"""

    text = serializers.CharField(max_length=1000, label="评论内容")
    force = serializers.BooleanField(required=False, default=False)


class ClassifyRequestSerializer(serializers.Serializer):
    """AI 自动分类请求（candidates=现有分类名列表，让 AI 优先复用）"""

    title = serializers.CharField(max_length=200, label="标题")
    content = serializers.CharField(max_length=8000, allow_blank=True, default="", label="正文")
    candidates = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
        label="现有分类候选",
    )
    force = serializers.BooleanField(required=False, default=False)


class AIGCResponseSerializer(serializers.Serializer):
    """AI 统一响应结构"""

    result = serializers.JSONField(label="AI结果")
    from_cache = serializers.BooleanField(label="是否命中缓存")
