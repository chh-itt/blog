"""
Django settings for config project.
基于 Python Django 的个人博客内容管理系统 —— 项目配置
"""

import os
from datetime import timedelta
from pathlib import Path

# django-dotenv 读取 .env 配置文件
from dotenv import load_dotenv

# 项目根目录（backend/）
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 .env 环境变量
load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str = "") -> str:
    """读取环境变量，兼容 os.environ 与 .env 文件"""
    return os.environ.get(key, default)


# ------------------------------------------------------------------
# 基础配置
# ------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG", "True") == "True"

# 允许的主机：本地开发 + 前端地址
ALLOWED_HOSTS = ["*"] if DEBUG else ["localhost", "127.0.0.1", "blog.example.com"]

# 自定义用户模型（扩展 Django 默认 User）
AUTH_USER_MODEL = "users.User"

# ------------------------------------------------------------------
# 应用注册
# ------------------------------------------------------------------
INSTALLED_APPS = [
    # Django 内置
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # PostgreSQL 特有功能（全文检索等）
    # 第三方
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # JWT 黑名单（退出登录）
    "corsheaders",
    "django_filters",
    "mptt",  # 分类树形结构
    # 项目应用
    "users",
    "blog",
    "aigc",
    "stats",
    "sysconf",
]

# ------------------------------------------------------------------
# 中间件
# ------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CORS 跨域（必须放在 CommonMiddleware 之前）
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ------------------------------------------------------------------
# 数据库：PostgreSQL 18.3 + pgvector
# ------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "blog"),
        "USER": env("DB_USER", "postgres"),
        "PASSWORD": env("DB_PASSWORD", "123456"),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
        # 连接池配置（psycopg3）：池化模式与 CONN_MAX_AGE 互斥，故设为 0
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"pool": True},
    }
}

# ------------------------------------------------------------------
# 密码校验
# ------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------
# 国际化（中文）
# ------------------------------------------------------------------
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# 静态文件与媒体文件
# ------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ------------------------------------------------------------------
# Django REST Framework 配置
# ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    # 统一异常处理
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
    # 节流限流（防爬/防刷）
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/min",
        "user": "300/min",
    },
}

# ------------------------------------------------------------------
# SimpleJWT 配置
# ------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ALGORITHM": "HS256",
}

# ------------------------------------------------------------------
# CORS 跨域配置
# ------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    env("FRONTEND_URL", "http://localhost:5173"),
]
CORS_ALLOW_CREDENTIALS = True

# ------------------------------------------------------------------
# Redis 缓存配置
# ------------------------------------------------------------------
REDIS_URL = f"redis://:{env('REDIS_PASSWORD', 'blog123456')}@{env('REDIS_HOST', '127.0.0.1')}:{env('REDIS_PORT', '6379')}/{env('REDIS_DB', '0')}"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        # 全局默认缓存时间：15 分钟
        "TIMEOUT": 900,
    },
    # 本地缓存（AI 服务降级时用）
    "local": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-blog-local-cache",
    },
}

# 会话使用 Redis（可选）
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# ------------------------------------------------------------------
# Celery 异步任务配置（AI 摘要等耗时任务）
# ------------------------------------------------------------------
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 120  # 单任务最长 120 秒

# ------------------------------------------------------------------
# AI 服务配置（创新点1）
# ------------------------------------------------------------------
DEEPSEEK_API_KEY = env("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = env("DEEPSEEK_MODEL", "deepseek-chat")

# Embedding 向量模型（创新点2）
EMBEDDING_API_KEY = env("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = env("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = int(env("EMBEDDING_DIM", "1024"))
