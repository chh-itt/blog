"""
users 应用：序列化器
"""

from django.contrib.auth import get_user_model

from rest_framework import serializers

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""

    password = serializers.CharField(write_only=True, min_length=6, label="密码")
    password2 = serializers.CharField(write_only=True, min_length=6, label="确认密码")

    class Meta:
        model = User
        fields = ["id", "username", "password", "password2", "nickname", "email"]

    def validate(self, attrs):
        """校验两次密码一致"""
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "两次输入的密码不一致"})
        return attrs

    def create(self, validated_data):
        """创建用户：剔除 password2，用 set_password 加密存储"""
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """用户信息序列化器（公开信息）"""

    articles_count = serializers.IntegerField(source="articles.count", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "nickname",
            "avatar",
            "bio",
            "is_author",
            "created_at",
            "articles_count",
        ]
        read_only_fields = ["id", "username", "is_author", "created_at", "articles_count"]


class UserProfileSerializer(UserSerializer):
    """个人资料序列化器（含可编辑字段）"""

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["email"]
        read_only_fields = UserSerializer.Meta.read_only_fields

    def update(self, instance, validated_data):
        """允许编辑 nickname/avatar/bio/email"""
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
