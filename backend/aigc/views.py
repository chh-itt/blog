"""
aigc 应用：视图
创新点1 的 REST 接口：
- POST /api/aigc/summary/    AI 自动摘要
- POST /api/aigc/tags/       AI 自动标签
- POST /api/aigc/writer/     AI 写作助手
- POST /api/aigc/qa/         RAG 问答
- POST /api/aigc/moderate/   评论自动审核
- POST /api/aigc/classify/   AI 自动分类
"""

from rest_framework import status, views
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from . import services
from .serializers import (
    ClassifyRequestSerializer,
    ModerateRequestSerializer,
    QaRequestSerializer,
    SummaryRequestSerializer,
    TagsRequestSerializer,
    WriterRequestSerializer,
)


class BaseAIGCView(views.APIView):
    """
    AI 功能基类：
    - 读操作所有人可见，写操作需登录（限流已在全局配置）
    - 捕获 services 抛出的 RuntimeError（未配置 API Key）转为友好错误
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def _call(self, fn):
        try:
            result, hit = fn()
        except RuntimeError as e:
            return Response(
                {"code": 503, "message": str(e), "data": None},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            return Response(
                {"code": 500, "message": f"AI 服务调用失败：{e}", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"code": 0, "message": "success", "data": {"result": result, "from_cache": hit}})


class SummaryView(BaseAIGCView):
    """AI 自动摘要"""

    def post(self, request):
        s = SummaryRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return self._call(lambda: services.generate_summary(s.validated_data["text"], s.validated_data.get("force", False)))


class TagsView(BaseAIGCView):
    """AI 自动标签"""

    def post(self, request):
        s = TagsRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        return self._call(
            lambda: services.generate_tags(data["title"], data.get("content", ""), data.get("force", False))
        )


class WriterView(BaseAIGCView):
    """AI 写作助手"""

    def post(self, request):
        s = WriterRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return self._call(lambda: services.writing_assistant(s.validated_data["prompt"], s.validated_data.get("force", False)))


class QaView(BaseAIGCView):
    """RAG 问答"""

    def post(self, request):
        s = QaRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        return self._call(
            lambda: services.rag_qa(data["question"], data.get("context", ""), data.get("force", False))
        )


class ModerateView(BaseAIGCView):
    """评论自动审核"""

    def post(self, request):
        s = ModerateRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return self._call(lambda: services.moderate_comment(s.validated_data["text"], s.validated_data.get("force", False)))


class ClassifyView(BaseAIGCView):
    """AI 自动分类（优先复用现有分类，无合适才新建）"""

    def post(self, request):
        s = ClassifyRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        return self._call(
            lambda: services.classify_category(
                data["title"],
                data.get("content", ""),
                data.get("candidates") or [],
                data.get("force", False),
            )
        )
