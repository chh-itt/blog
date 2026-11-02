"""
users 应用：用户模型
继承 Django 内置 AbstractUser，扩展个人博客所需字段
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    自定义用户模型
    - 复用 Django 内置的 username/password 等字段
    - 扩展昵称、头像、简介、博主标记
    """

    # 昵称（显示名）
    nickname = models.CharField("昵称", max_length=50, blank=True)
    # 头像（URL 或 /media/avatars/ 相对路径，留空使用默认首字符头像）
    avatar = models.CharField("头像", max_length=255, blank=True)
    # 个人简介
    bio = models.TextField("个人简介", blank=True)
    # 是否为博主（系统管理员角色）
    is_author = models.BooleanField("博主", default=False)
    # 注册时间
    created_at = models.DateTimeField("注册时间", auto_now_add=True)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = verbose_name
        ordering = ["-date_joined"]

    def __str__(self):
        return self.nickname or self.username
