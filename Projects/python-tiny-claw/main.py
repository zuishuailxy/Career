"""tiny-claw 入口 — 对应 cmd/claw/main.go"""

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

# LangSmith 追踪
import tiny_claw.tracing
from tiny_claw.engine import AgentEngine
from tiny_claw.feishu import FeishuBot
from tiny_claw.provider import DeepSeekProvider
from tiny_claw.tools import RegistryImpl
from tiny_claw.tools.builtin import ReadFileTool, WriteFileTool, BashTool, EditFileTool, SkillTool

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
logger = logging.getLogger("tiny-claw")
USE_FEISHU = False


def build_engine(work_dir: str | None = None) -> AgentEngine:
    """构建引擎：Provider + Registry + Tools"""
    work_dir = work_dir or os.getcwd()

    llm = DeepSeekProvider()

    registry = RegistryImpl()
    registry.register(ReadFileTool(work_dir))
    registry.register(WriteFileTool(work_dir))
    registry.register(BashTool(work_dir))
    registry.register(EditFileTool(work_dir))
    registry.register(SkillTool(work_dir))

    return AgentEngine(llm, registry, work_dir, enable_thinking=False)


def main():
    logger.info("tiny-claw starting...")
    engine = build_engine()

    if os.getenv("FEISHU_APP_ID") and USE_FEISHU:
        # 飞书模式：长连接，无需 ngrok
        FeishuBot(engine).start()
    else:
        # CLI 模式
        asyncio.run(engine.run("列出当前目录的文件"))


if __name__ == "__main__":
    main()
