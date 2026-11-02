"""
统一 API 响应规范
=============================================================
所有接口统一返回：
  {"code": 0, "message": "success", "data": ...}
- code   : 0 表示成功，非 0 为业务错误码（与 custom_exception_handler 对齐）
- message: 提示信息
- data   : 业务数据

用法：视图类继承 ApiResponseMixin 即可自动包装；已经按统一格式
返回的视图（如自定义 APIView 直接返回 {"code":0,...}）不会被重复包装。
=============================================================
"""

from rest_framework.response import Response


class ApiResponseMixin:
    """自动把成功响应包装成统一格式"""

    def finalize_response(self, request, response, *args, **kwargs):
        # 仅包装 2xx 成功响应；异常已由 custom_exception_handler 统一处理
        if 200 <= response.status_code < 300 and isinstance(response, Response):
            # 已经是统一格式（含 "code" 键）则不重复包装
            if not (isinstance(response.data, dict) and "code" in response.data):
                response.data = {"code": 0, "message": "success", "data": response.data}
        return super().finalize_response(request, response, *args, **kwargs)
