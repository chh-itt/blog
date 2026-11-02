"""
Django 主路由配置
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)


def health_check(request):
    """健康检查接口（部署探活用）"""
    return JsonResponse({"status": "ok", "service": "blog-api"})


urlpatterns = [
    # Django 自带后台（论文管理端为 Vue 实现，此处供开发调试）
    path("django-admin/", admin.site.urls),
    # 健康检查
    path("api/health/", health_check, name="health"),
    # JWT 认证接口
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    # 业务模块
    path("api/users/", include("users.urls")),
    path("api/blog/", include("blog.urls")),
    path("api/aigc/", include("aigc.urls")),
    path("api/stats/", include("stats.urls")),
    path("api/sysconf/", include("sysconf.urls")),
]

# 开发环境静态/媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
