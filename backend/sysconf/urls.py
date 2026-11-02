"""
sysconf 应用：路由
"""

from django.urls import path

from .views import ConfigView

urlpatterns = [
    path("config/", ConfigView.as_view(), name="sysconf-config"),
]
