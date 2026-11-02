"""
users 应用：用户与认证模块路由
"""

from django.urls import path

from . import views

urlpatterns = [
    # 注册
    path("register/", views.RegisterView.as_view(), name="register"),
    # 当前用户信息
    path("me/", views.MeView.as_view(), name="me"),
    # 头像上传
    path("avatar/", views.AvatarUploadView.as_view(), name="avatar"),
]
