"""
Celery 异步任务配置
用于 AI 摘要生成、访问统计落库等耗时任务
"""

import os

from celery import Celery

# 设置 Django 默认配置模块
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("blog_project")

# 从 Django settings 读取配置（CELERY_ 前缀）
app.config_from_object("django.conf:settings", namespace="CELERY")

# 自动发现各 app 中的 tasks.py
app.autodiscover_tasks()
