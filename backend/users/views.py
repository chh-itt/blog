"""
users 应用：视图
- 注册 /api/users/register/
- 个人信息 /api/users/me/
- 头像上传 /api/users/avatar/
"""

import os
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api import ApiResponseMixin

from .serializers import UserProfileSerializer, UserRegisterSerializer, UserSerializer

User = get_user_model()

# 允许的头像图片格式与大小限制
ALLOWED_AVATAR_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


class RegisterView(ApiResponseMixin, generics.CreateAPIView):
    """用户注册接口"""

    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        """注册成功直接返回 201 与用户信息"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class MeView(ApiResponseMixin, generics.RetrieveUpdateAPIView):
    """当前登录用户信息查看与修改"""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """返回当前登录用户"""
        return self.request.user


class AvatarUploadView(ApiResponseMixin, APIView):
    """头像上传接口（multipart/form-data，字段名 file）"""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            raise ValidationError({"detail": "请选择要上传的头像图片"})
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_AVATAR_EXTS:
            raise ValidationError({"detail": "仅支持 jpg/png/gif/webp 格式的图片"})
        if file.size > MAX_AVATAR_SIZE:
            raise ValidationError({"detail": "头像图片大小不能超过 2MB"})

        # 以 用户名_随机串.扩展名 命名，避免重名与路径穿越
        avatar_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        filename = f"{request.user.username}_{uuid.uuid4().hex[:8]}{ext}"
        dest = os.path.join(avatar_dir, filename)
        with open(dest, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        url = f"{settings.MEDIA_URL}avatars/{filename}"
        request.user.avatar = url
        request.user.save(update_fields=["avatar"])
        return Response({"avatar": url})
