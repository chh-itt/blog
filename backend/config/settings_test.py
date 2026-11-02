"""
测试专用配置
=====================================================================
继承主配置（config.settings），仅覆盖与外部依赖相关的部分：
- 缓存改用本地内存（不依赖真实 Redis）
- Celery 任务同步执行（不依赖 worker / broker）
- 关闭限流（避免测试请求触发速率限制）
- 使用更快的密码哈希（MD5，仅用于测试速度）
运行方式：
    python manage.py test --settings=config.settings_test
=====================================================================
"""

from .settings import *  # noqa: F401,F403  （继承全部主配置）

# 本地内存缓存，替代 Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-default",
    },
    "local": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-local",
    },
}

# Celery 任务同步执行（写文章触发的 AI 异步任务直接在当前进程跑）
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False

# 关闭限流（论文项目测试量大，避免 300 次/分钟误伤）
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {"anon": None, "user": None}  # noqa: F405

# 加速密码哈希
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
