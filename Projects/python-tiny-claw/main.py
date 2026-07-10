"""tiny-claw 入口 — 对应 cmd/claw/main.go

支持通过命令行接收任务、断点续传（Plan Mode）。
"""

import argparse
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from tiny_claw.engine import AgentEngine
from tiny_claw.engine.session import global_session_mgr
from tiny_claw.provider import DeepSeekProvider
from tiny_claw.schema import Message, Role
from tiny_claw.tools import RegistryImpl
from tiny_claw.tools.builtin import BashTool, EditFileTool, ReadFileTool, SkillTool, WriteFileTool

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
logger = logging.getLogger("tiny-claw")


def build_engine(work_dir: str) -> AgentEngine:
    """组装引擎：挂载全部工具 + 开启计划模式"""
    llm = DeepSeekProvider()
    registry = RegistryImpl()
    registry.register(ReadFileTool(work_dir))
    registry.register(WriteFileTool(work_dir))
    registry.register(BashTool(work_dir))
    registry.register(EditFileTool(work_dir))
    registry.register(SkillTool(work_dir))
    return AgentEngine(llm, registry, plan_mode=True, enable_thinking=False)


async def run(prompt: str, session_id: str, work_dir: str) -> None:
    """核心执行：按给定 prompt 驱动 Agent"""
    engine = build_engine(work_dir)

    # 用固定 SessionID 实现断点续传：
    # 即便进程重启、内存丢失，只要 TODO.md 还在，任务就能继续
    session = await global_session_mgr.get_or_create(session_id, work_dir)
    await session.append(Message(role=Role.USER, content=prompt))

    await engine.run(session)


def main():
    parser = argparse.ArgumentParser(description="tiny-claw — 驾驭工程驱动研发助手")
    parser.add_argument(
        "-p", "--prompt",
        required=True,
        help="要交给 Agent 执行的任务描述",
    )
    parser.add_argument(
        "-s", "--session-id",
        default="tiny-claw-default",
        help="会话 ID（多次运行相同 ID 可实现断点续传）",
    )
    args = parser.parse_args()

    if not os.getenv("DEEPSEEK_API_KEY"):
        logger.fatal("请先设置 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)

    work_dir = os.getcwd()
    logger.info("\n>>> 🚀 收到指令: %s", args.prompt)

    asyncio.run(run(args.prompt, args.session_id, work_dir))


if __name__ == "__main__":
    main()
