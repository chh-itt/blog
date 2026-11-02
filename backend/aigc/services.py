"""
aigc 应用：AI 服务层（创新点1 核心）
=====================================================================
封装 DeepSeek 大模型调用与 embedding 向量生成：
- chat()           : 调用 DeepSeek 对话补全 API（requests 同步调用）
- embed_text()     : 调用 SiliconFlow embedding API 生成语义向量（bge-m3）
- get_ai_result()  : 统一的"缓存优先"入口 —— 先查 aigc_ai_cache，未命中
                     才调用模型并把结果写回缓存（省 API 费用、加速响应）
- 各业务函数       : generate_summary / generate_tags / writing_assistant
                     / rag_qa / moderate_comment / classify_category
=====================================================================
"""

import hashlib
import json
import re

import requests

from .models import AICache
from sysconf.services import (
    get_deepseek_base_url,
    get_deepseek_key,
    get_deepseek_model,
    get_embedding_base_url,
    get_embedding_key,
    get_embedding_model,
)


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------
def _input_hash(text: str) -> str:
    """对输入文本取 MD5，作为 AI 缓存键"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _get_cached(func_type: str, text: str):
    """查询 AI 缓存，命中返回缓存结果，否则返回 None"""
    try:
        obj = AICache.objects.filter(func_type=func_type, input_hash=_input_hash(text)).first()
        return obj.output if obj else None
    except Exception:
        return None


def _set_cached(func_type: str, text: str, output) -> None:
    """写入 AI 缓存（幂等，冲突时忽略）"""
    try:
        AICache.objects.update_or_create(
            func_type=func_type,
            input_hash=_input_hash(text),
            defaults={"output": output},
        )
    except Exception:
        pass


# ------------------------------------------------------------------
# DeepSeek 对话调用
# ------------------------------------------------------------------
def chat(
    messages: list,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    json_mode: bool = False,
) -> str:
    """
    调用 DeepSeek 对话补全 API，返回回复文本。
    - json_mode=True 时强制模型输出合法 JSON
    - 未配置 API Key 时抛出 RuntimeError（由视图层转成友好提示）
    """
    api_key = get_deepseek_key()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，请在管理后台-系统设置中填写")

    url = get_deepseek_base_url().rstrip("/") + "/chat/completions"
    payload = {
        "model": model or get_deepseek_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if json_mode:
        # DeepSeek 支持 response_format 参数强制 JSON 输出
        payload["response_format"] = {"type": "json_object"}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# ------------------------------------------------------------------
# Embedding 向量生成（创新点2 依赖）
# ------------------------------------------------------------------
def embed_text(text: str) -> list:
    """
    调用 embedding API 生成文本的语义向量（默认 bge-m3，1024 维）。
    返回 float 列表；未配置 Key 时抛 RuntimeError。
    """
    api_key = get_embedding_key()
    if not api_key:
        raise RuntimeError("EMBEDDING_API_KEY 未配置，请在管理后台-系统设置中填写")

    url = get_embedding_base_url().rstrip("/") + "/embeddings"
    payload = {
        "model": get_embedding_model(),
        "input": text[:2000],  # 截断避免超限
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["data"][0]["embedding"]


# ------------------------------------------------------------------
# 统一的"缓存优先"执行器
# ------------------------------------------------------------------
def get_ai_result(func_type: str, text: str, generate_fn, force: bool = False):
    """
    通用入口：先查缓存，未命中则调用 generate_fn 生成并缓存。
    - func_type : 功能类型（summary/tags/...），参与缓存键
    - text      : 输入（参与缓存键哈希）
    - generate_fn : 无参函数，负责真正调用模型
    - force     : True 时跳过缓存强制重新生成
    """
    if not force:
        cached = _get_cached(func_type, text)
        if cached is not None:
            return cached, True  # (结果, 是否命中缓存)
    result = generate_fn()
    _set_cached(func_type, text, result)
    return result, False


# ------------------------------------------------------------------
# 各业务功能（Prompt 工程）
# ------------------------------------------------------------------
def generate_summary(content_md: str, force: bool = False) -> tuple:
    """
    创新点1-A：AI 自动摘要
    提示词要求：客观、保留技术要点、不超过 120 字、不编造
    """
    prompt = (
        "你是博客编辑，请为下面的技术文章生成一段中文摘要。\n"
        "要求：\n"
        "1. 客观准确，忠实原文，不要编造文中没有的内容；\n"
        "2. 保留核心技术要点、方案与结论；\n"
        "3. 长度控制在 100~150 字；\n"
        "4. 直接输出摘要文本，不要加任何前缀或引号。\n\n"
        "文章内容：\n" + content_md[:6000]
    )
    return get_ai_result(
        "summary",
        content_md,
        lambda: chat(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        ),
        force,
    )


def generate_tags(title: str, content_md: str, force: bool = False) -> tuple:
    """
    创新点1-B：AI 自动标签
    提示词要求：返回 JSON 数组，3~6 个短标签，必须合法 JSON
    """
    prompt = (
        "你是博客内容分类助手。请根据文章标题和正文，提取 3~6 个中文标签。\n"
        "要求：\n"
        "1. 只输出一个 JSON 数组，例如 [\"Django\", \"Redis\", \"缓存\"]；\n"
        "2. 标签要短（2~6 字），能概括文章主题与关键技术；\n"
        "3. 不要输出任何解释文字。\n\n"
        f"标题：{title}\n正文：{content_md[:4000]}"
    )
    raw, hit = get_ai_result(
        "tags",
        title + content_md[:4000],
        lambda: chat(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
            json_mode=True,
        ),
        force,
    )
    # 解析 JSON 数组（容错处理：去掉多余字符）
    try:
        tags = json.loads(raw)
        if isinstance(tags, dict):  # 有些模型会包一层
            for v in tags.values():
                if isinstance(v, list):
                    tags = v
                    break
        if not isinstance(tags, list):
            raise ValueError
        tags = [str(t).strip() for t in tags if str(t).strip()][:6]
    except Exception:
        # 兜底：从文本中正则提取"xx"/'xx' 或逗号分隔词
        found = re.findall(r"[\"']([^\"']{2,10})[\"']", raw)
        tags = [t for t in found if t][:6]
    return tags, hit


def writing_assistant(prompt: str, force: bool = False) -> tuple:
    """
    创新点1-C：AI 写作助手
    把用户给的一句话需求扩写成一段文章（连续对话，无记忆）
    """
    system = (
        "你是一位技术博客写作助手。根据用户的提示词，输出结构清晰、段落通顺、"
        "带有小标题和列表的中文技术文章。直接输出正文，不要客套。"
    )
    return get_ai_result(
        "writer",
        prompt,
        lambda: chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=1500,
        ),
        force,
    )


def _auto_recall_context(question: str, top_k: int = 5, snippet_chars: int = 500) -> str:
    """
    "自动 RAG"：未提供参考资料时，用混合检索为问题召回 Top-K 篇已发布文章，
    取"标题 + 摘要（缺省则取正文片段）"拼接成参考资料文本。
    - 延迟导入 blog.services，避免循环依赖（blog.services 顶部 import 了本模块的 embed_text）
    - 任何检索异常都降级为空上下文，不阻断问答（与论文中的自动降级策略一致）
    """
    try:
        from blog.models import Article
        from blog.services import hybrid_search

        results = hybrid_search(question, limit=top_k)
        if not results:
            return ""
        objs = Article.objects.in_bulk([rid for rid, _ in results])
        parts = []
        for rid, _score in results:
            article = objs.get(rid)
            if article is None:
                continue
            snippet = (article.summary or article.content_md).strip()
            parts.append(f"《{article.title}》：{snippet[:snippet_chars]}")
        return "\n\n".join(parts)
    except Exception:
        return ""


def rag_qa(question: str, context_text: str = "", force: bool = False) -> tuple:
    """
    创新点1-D：RAG 问答（严格依据参考资料）
    - 博主手动粘贴参考资料（context_text 非空）时，直接使用；
    - 未提供参考资料时，自动调用混合检索为问题召回 Top-5 已发布文章片段；
    - 召回为空或检索失败时不调用大模型，直接返回"资料中未找到"——
      防止模型用自身知识自由发挥，保证回答严格来自知识库。
    """
    if not context_text.strip():
        context_text = _auto_recall_context(question)
    if not context_text.strip():
        # 无可用参考资料：直接拒答，不把问题交给模型自由发挥
        return "资料中未找到：知识库中没有与该问题相关的文章。", False
    system = (
        "你是博客智能问答助手。你必须只依据下面的参考资料回答用户问题。\n"
        "规则：\n"
        "1. 参考资料是你唯一的信息来源，禁止使用你自己的知识作答；\n"
        "2. 若参考资料与问题无关或未覆盖问题，只回复：资料中未找到；\n"
        "3. 回答简洁、分点，控制在 300 字内。\n\n"
        "参考资料：\n" + context_text[:8000] + "\n\n"
        "再次强调：只依据上面的参考资料回答；若资料与问题无关，只回复\"资料中未找到\"。"
    )
    return get_ai_result(
        "qa",
        question + context_text[:8000],
        lambda: chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            temperature=0.2,
            max_tokens=800,
        ),
        force,
    )


def moderate_comment(comment_text: str, force: bool = False) -> tuple:
    """
    创新点1-E：评论自动审核
    返回 {"result": "pass"|"reject", "reason": "..."}
    """
    prompt = (
        "你是内容安全审核员。判断下面这条用户评论是否应该通过审核。\n"
        "以下情况应拒绝：辱骂/人身攻击、涉黄涉暴、广告推广、政治敏感、垃圾灌水。\n"
        "请只输出 JSON：{\"result\": \"pass\" 或 \"reject\", \"reason\": \"一句话理由\"}\n\n"
        "评论内容：" + comment_text[:500]
    )
    raw, hit = get_ai_result(
        "moderate",
        comment_text,
        lambda: chat(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100,
            json_mode=True,
        ),
        force,
    )
    try:
        result = json.loads(raw)
        if not isinstance(result, dict) or "result" not in result:
            raise ValueError
    except Exception:
        result = {"result": "pass", "reason": "AI审核异常，默认通过"}
    return result, hit


def classify_category(title: str, content_md: str, candidates: list = None, force: bool = False) -> tuple:
    """
    创新点1-F：AI 自动分类
    优先从现有分类（candidates）中选择最合适的；没有合适候选时才生成新分类名。
    返回 {"category": "分类名"}
    """
    candidate_text = "、".join(candidates) if candidates else "（无）"
    prompt = (
        "你是博客内容分类助手。请根据文章标题和正文，判断这篇文章最适合的单个分类。\n"
        "现有分类如下（优先从中选择最贴切的）：\n"
        f"{candidate_text}\n"
        "要求：\n"
        "1. 若现有分类中有合适的，直接输出该分类名（必须与列表中的名称完全一致）；\n"
        "2. 若现有分类都不合适，可以创造一个新分类名（2~8 个字，能概括文章主题）；\n"
        "3. 只输出 JSON：{\"category\": \"分类名\"}，不要输出任何其他文字。\n\n"
        f"标题：{title}\n正文：{content_md[:4000]}"
    )
    raw, hit = get_ai_result(
        "classify",
        title + content_md[:4000] + "|" + candidate_text,
        lambda: chat(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100,
            json_mode=True,
        ),
        force,
    )
    try:
        result = json.loads(raw)
        category = str(result.get("category", "")).strip()
        if not category:
            raise ValueError
    except Exception:
        # 容错兜底：正则提取引号内的词
        found = re.findall(r"[\"']([^\"']{2,20})[\"']", raw)
        category = found[0] if found else ""
    return {"category": category}, hit
