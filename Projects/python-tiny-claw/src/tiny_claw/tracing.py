"""LangSmith 追踪集成 — 为 Agent 调用链添加可观测性。

使用 LangSmith 的 @traceable 装饰器，不依赖 LangChain。
"""

import os
from functools import wraps

from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()

# ---- LangSmith 初始化 ----
os.environ.setdefault("LANGSMITH_TRACING", "true")
os.environ.setdefault("LANGSMITH_PROJECT", "tiny-claw")
os.environ.setdefault("LANGSMITH_API_KEY", os.getenv("LANGSMITH_API_KEY", ""))


def trace(name: str | None = None, **kwargs):
    """轻量封装：为函数添加 LangSmith 追踪。

    用法：
        @trace("agent-think")
        async def generate(...): ...

    等同于 langsmith.traceable()，但提供项目级默认值。
    """
    return traceable(
        name=name,
        project_name=os.getenv("LANGSMITH_PROJECT", "tiny-claw"),
        **kwargs,
    )


def trace_llm(func):
    """为 LLM 调用添加 LangSmith 追踪标记。"""
    return traceable(
        run_type="llm",
        name="llm-generate",
        project_name=os.getenv("LANGSMITH_PROJECT", "tiny-claw"),
    )(func)


def trace_tool(func):
    """为工具执行添加 LangSmith 追踪标记。"""
    return traceable(
        run_type="tool",
        name="tool-execute",
        project_name=os.getenv("LANGSMITH_PROJECT", "tiny-claw"),
    )(func)
