"""
sysconf 应用：功能/集成测试
覆盖：配置读写权限、敏感项脱敏、白名单过滤、数据库优先回退
运行：python manage.py test sysconf --settings=config.settings_test
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import SysConfig
from .serializers import mask_secret
from .services import get_config, set_config

User = get_user_model()


def make_user(username, is_author=False):
    return User.objects.create_user(username=username, password="pass123456", is_author=is_author)


class SysConfigTests(TestCase):
    """系统配置 API 测试"""

    def setUp(self):
        self.author = make_user("author1", is_author=True)
        self.normal = make_user("normal1")
        self.client = APIClient()

    # ---------------- 脱敏工具 ----------------
    def test_mask_secret(self):
        self.assertEqual(mask_secret(""), "")
        self.assertEqual(mask_secret("abcd"), "****")
        self.assertEqual(mask_secret("sk-1234567890abcdef"), "sk-1****cdef")

    # ---------------- 服务层 ----------------
    def test_get_config_db_priority(self):
        # 未设置时返回默认值
        self.assertEqual(get_config("NOT_EXIST", "default"), "default")
        # 设置后数据库优先
        set_config("DEEPSEEK_API_KEY", "sk-abc")
        self.assertEqual(get_config("DEEPSEEK_API_KEY", "fallback"), "sk-abc")

    # ---------------- 权限 ----------------
    def test_config_requires_author(self):
        # 匿名 → 401
        resp = self.client.get("/api/sysconf/config/")
        self.assertEqual(resp.status_code, 401)
        # 普通用户 → 403
        self.client.force_authenticate(self.normal)
        resp = self.client.get("/api/sysconf/config/")
        self.assertEqual(resp.status_code, 403)
        # 博主 → 200
        self.client.force_authenticate(self.author)
        resp = self.client.get("/api/sysconf/config/")
        self.assertEqual(resp.status_code, 200)

    # ---------------- 写与脱敏 ----------------
    def test_put_updates_and_masks(self):
        self.client.force_authenticate(self.author)
        resp = self.client.put(
            "/api/sysconf/config/",
            {"DEEPSEEK_API_KEY": "sk-1234567890abcdef", "DEEPSEEK_MODEL": "deepseek-chat"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        rows = {r["key"]: r for r in resp.data["data"]}
        self.assertIn("DEEPSEEK_API_KEY", rows)
        # 敏感项脱敏返回
        self.assertEqual(rows["DEEPSEEK_API_KEY"]["value"], "sk-1****cdef")
        self.assertTrue(rows["DEEPSEEK_API_KEY"]["is_secret"])
        # 非敏感项原样返回
        self.assertEqual(rows["DEEPSEEK_MODEL"]["value"], "deepseek-chat")
        # 数据库存的是明文（仅供服务层使用，前端不可见）
        self.assertEqual(SysConfig.objects.get(pk="DEEPSEEK_API_KEY").value, "sk-1234567890abcdef")

    def test_put_whitelist_ignores_unknown(self):
        self.client.force_authenticate(self.author)
        self.client.put("/api/sysconf/config/", {"NOT_A_REAL_KEY": "x"}, format="json")
        self.assertFalse(SysConfig.objects.filter(pk="NOT_A_REAL_KEY").exists())
