"""
users 应用：功能/集成测试
覆盖：注册、JWT 登录、个人信息、头像上传
运行：python manage.py test users --settings=config.settings_test
"""

import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import User


class UserAuthTests(TestCase):
    """认证与资料接口测试"""

    def setUp(self):
        self.client = APIClient()
        self.register_data = {
            "username": "alice",
            "password": "pass123456",
            "password2": "pass123456",
            "nickname": "爱丽丝",
            "email": "alice@test.com",
        }

    def _register(self):
        return self.client.post("/api/users/register/", self.register_data, format="json")

    def _login(self, username="alice", password="pass123456"):
        resp = self.client.post("/api/auth/token/", {"username": username, "password": password}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.data

    def _auth_client(self, token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")
        return client

    # ---------------- 注册 ----------------
    def test_register_success(self):
        resp = self._register()
        self.assertEqual(resp.status_code, 201)
        data = resp.data["data"]
        self.assertEqual(data["username"], "alice")
        self.assertEqual(data["nickname"], "爱丽丝")
        # 密码必须加密存储（不允许明文）
        user = User.objects.get(username="alice")
        self.assertNotEqual(user.password, "pass123456")
        self.assertIn("$", user.password)

    def test_register_password_mismatch(self):
        data = dict(self.register_data, password2="different1")
        resp = self.client.post("/api/users/register/", data, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_username(self):
        self._register()
        resp = self.client.post("/api/users/register/", self.register_data, format="json")
        self.assertEqual(resp.status_code, 400)

    # ---------------- 登录 & JWT ----------------
    def test_login_wrong_password(self):
        self._register()
        resp = self.client.post("/api/auth/token/", {"username": "alice", "password": "wrong"}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_token_refresh(self):
        self._register()
        token = self._login()
        resp = self.client.post("/api/auth/token/refresh/", {"refresh": token["refresh"]}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)

    # ---------------- 个人信息 ----------------
    def test_me_requires_auth(self):
        resp = self.client.get("/api/users/me/")
        self.assertEqual(resp.status_code, 401)

    def test_me_returns_profile(self):
        self._register()
        token = self._login()
        client = self._auth_client(token)
        resp = client.get("/api/users/me/")
        self.assertEqual(resp.status_code, 200)
        data = resp.data["data"]
        self.assertEqual(data["username"], "alice")
        self.assertIn("articles_count", data)

    def test_profile_update(self):
        self._register()
        token = self._login()
        client = self._auth_client(token)
        resp = client.patch("/api/users/me/", {"nickname": "新版昵称", "bio": "测试简介"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["nickname"], "新版昵称")
        self.assertEqual(resp.data["data"]["bio"], "测试简介")

    # ---------------- 头像上传 ----------------
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="django_test_media_"))
    def test_avatar_upload(self):
        try:
            self._register()
            token = self._login()
            client = self._auth_client(token)
            png = SimpleUploadedFile(
                "avatar.png",
                b"\x89PNG\r\n\x1a\n" + b"\x00" * 64,
                content_type="image/png",
            )
            resp = client.post("/api/users/avatar/", {"file": png}, format="multipart")
            self.assertEqual(resp.status_code, 200, resp.content)
            self.assertTrue(resp.data["data"]["avatar"].startswith("/media/avatars/"))
            # me 中已更新
            me = client.get("/api/users/me/").data["data"]
            self.assertEqual(me["avatar"], resp.data["data"]["avatar"])
            # 非图片格式被拒绝
            bad = SimpleUploadedFile("bad.txt", b"hello", content_type="text/plain")
            resp2 = client.post("/api/users/avatar/", {"file": bad}, format="multipart")
            self.assertEqual(resp2.status_code, 400)
        finally:
            shutil.rmtree(tempfile.gettempdir(), ignore_errors=True)
