"""LLM Provider 层 — 大模型接口抽象与具体厂商实现。

支持:
- DeepSeek (deepseek-chat / deepseek-reasoner)
- Qwen (通义千问, OpenAI 兼容)
- MiMo (小米 MiMo, OpenAI 兼容)
"""

from tiny_claw.provider.base import LLMProvider
from tiny_claw.provider.openai import DeepSeekProvider

__all__ = ["LLMProvider", "DeepSeekProvider"]
