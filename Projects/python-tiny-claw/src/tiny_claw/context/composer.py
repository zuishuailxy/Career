"""Prompt 组装器 — 对应 internal/context/composer.go

根据工作区环境动态生成 System Prompt。
"""

import logging
from pathlib import Path

from tiny_claw.context.skill import SkillLoader
from tiny_claw.schema import Message, Role

logger = logging.getLogger("tiny-claw.context.composer")

CORE_PROMPT = """# 核心身份
你名叫 tiny-claw，一个由驾驭工程驱动的骨灰级研发助手。
你具备极简主义哲学，拒绝废话。你能通过系统提供的内置工具，创建、读取、修改和执行工作区中的代码。

# 核心纪律 (CRITICAL)
1. 如需检查文件是否存在，请使用 bash 的 ls 或 test -f，而不是对目录使用 read_file。
2. 创建新文件时，务必使用 write_file，并同时提供 path 和 content 参数。
3. 编辑文件前务必先读取现有文件，以理解上下文。
4. 无论何时你需要写代码或创建文件，都要直接使用 write_file 工具。
5. 遇到工具执行报错时，仔细阅读 stderr，尝试自己修正命令并重试。
6. 始终用中文回复，以便传达你的进展和想法。
{agents_section}{skills_section}"""


class PromptComposer:
    """动态生成 System Prompt"""

    def __init__(self, work_dir: str):
        self._work_dir = Path(work_dir).resolve()
        self._skill_loader = SkillLoader(work_dir)

    def build(self) -> Message:
        """组装并返回一条完整的 SYSTEM 消息"""
        agents_section = self._load_agents_md()
        skills_section = self._skill_loader.load_metadata()  # 只注入元数据

        content = CORE_PROMPT.format(
            agents_section=agents_section,
            skills_section=skills_section,
        )
        return Message(role=Role.SYSTEM, content=content)

    def _load_agents_md(self) -> str:
        """加载项目专属规范 AGENTS.md"""
        agents_path = self._work_dir / "AGENTS.md"
        if not agents_path.is_file():
            return ""

        try:
            content = agents_path.read_text(encoding="utf-8")
        except Exception:
            return ""

        return (
            "\n\n# 项目专属指南 (来自 AGENTS.md)\n"
            "以下是当前工作区特有的架构规范与注意事项，你的行为必须绝对符合以下要求：\n\n"
            f"{content}\n"
        )
