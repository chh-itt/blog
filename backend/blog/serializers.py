"""
blog 应用：序列化器
"""

from django.contrib.auth import get_user_model

from rest_framework import serializers

from .models import Article, Category, Comment, Tag

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """分类序列化器（含子分类树）"""

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "description", "level", "children"]
        read_only_fields = ["level"]

    def get_children(self, obj):
        """递归返回子分类（只取一级，防止循环）"""
        children = obj.get_children()
        if not children.exists():
            return []
        return CategorySerializer(children, many=True).data


class TagSerializer(serializers.ModelSerializer):
    """标签序列化器"""

    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class AuthorSerializer(serializers.ModelSerializer):
    """作者信息序列化器"""

    class Meta:
        model = User
        fields = ["id", "username", "nickname", "avatar"]


class ArticleListSerializer(serializers.ModelSerializer):
    """文章列表序列化器（不含正文，减载）"""

    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "cover",
            "status",
            "is_top",
            "views",
            "likes",
            "ai_summary",
            "ai_tags",
            "category",
            "tags",
            "author",
            "published_at",
            "created_at",
        ]


class ArticleDetailSerializer(serializers.ModelSerializer):
    """文章详情序列化器（含正文与 AI 字段）"""

    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "content_md",
            "content_html",
            "cover",
            "status",
            "is_top",
            "allow_comment",
            "views",
            "likes",
            "ai_summary",
            "ai_tags",
            "category",
            "tags",
            "author",
            "published_at",
            "created_at",
            "updated_at",
        ]


class ArticleWriteSerializer(serializers.ModelSerializer):
    """文章创建/编辑序列化器"""

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "summary",
            "content_md",
            "content_html",
            "cover",
            "status",
            "is_top",
            "allow_comment",
            "category",
            "tags",
            "ai_summary",
            "ai_tags",
        ]
        read_only_fields = ["id"]


class CommentSerializer(serializers.ModelSerializer):
    """评论序列化器"""

    user = AuthorSerializer(read_only=True)
    reply_count = serializers.IntegerField(source="replies.count", read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "article",
            "parent",
            "user",
            "content",
            "status",
            "likes",
            "reply_count",
            "created_at",
        ]
        read_only_fields = ["user", "status", "likes", "created_at"]
        extra_kwargs = {"article": {"write_only": True}, "parent": {"required": False}}


class CommentWriteSerializer(serializers.ModelSerializer):
    """评论创建序列化器（article 来自 URL，不由请求体提供）"""

    class Meta:
        model = Comment
        fields = ["id", "article", "parent", "content", "status"]
        extra_kwargs = {
            "parent": {"required": False},
            "article": {"read_only": True},
            "status": {"read_only": True},
        }


class SearchResultSerializer(ArticleListSerializer):
    """搜索结果序列化器（附带混合检索打分）"""

    score = serializers.FloatField(read_only=True, required=False)

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + ["score"]


class TagEnsureSerializer(serializers.Serializer):
    """AI 标签自动入库请求（批量确保标签存在）"""

    names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        max_length=20,
        allow_empty=False,
        label="标签名列表",
    )


class CategoryEnsureSerializer(serializers.Serializer):
    """AI/手动分类入库请求（同名任意层级复用，否则创建为顶层大类）"""

    name = serializers.CharField(max_length=50, label="分类名")
