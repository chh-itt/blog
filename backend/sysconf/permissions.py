"""
sysconf 应用：自定义权限
"""

from rest_framework.permissions import BasePermission


class IsAuthor(BasePermission):
    """仅博主（is_author=True）可访问的权限"""

    message = "需要博主权限"

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_author
        )
