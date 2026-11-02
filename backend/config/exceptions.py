"""
统一异常处理：将 DRF 异常转换为 {code, message, data} 统一格式
"""

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    自定义全局异常处理器。
    返回统一格式：{"code": <int>, "message": <str>, "data": null}
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        # DRF 已处理的异常（校验错误、权限错误等）
        if isinstance(response.data, dict) and "detail" in response.data:
            message = str(response.data["detail"])
        elif isinstance(response.data, dict):
            # 字段级校验错误，取第一个错误信息
            first_key = next(iter(response.data))
            first_err = response.data[first_key]
            message = str(first_err[0]) if isinstance(first_err, list) else str(first_err)
        else:
            message = str(response.data)

        response.data = {
            "code": response.status_code,
            "message": message,
            "data": None,
        }
    else:
        # 未处理的异常（500），记录日志并返回通用错误
        import logging
        import traceback

        logging.getLogger(__name__).error(
            "Unhandled exception: %s\n%s", exc, traceback.format_exc()
        )
        response = Response(
            {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "服务器内部错误，请稍后重试",
                "data": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
