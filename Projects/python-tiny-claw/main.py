"""tiny-claw 入口 — 对应 cmd/claw/main.go

支持两种运行模式：
  - CLI 模式：  python main.py -p "任务描述"
  - 飞书模式：  python main.py --mode feishu
"""

import argparse
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from tiny_claw.engine import AgentEngine
from tiny_claw.engine.session import Session, global_session_mgr
from tiny_claw.provider import DeepSeekProvider
from tiny_claw.schema import Message, Role, ToolCall
from tiny_claw.tools import RegistryImpl
from tiny_claw.tools.builtin import (
    BashTool,
    EditFileTool,
    ReadFileTool,
    SkillTool,
    WriteFileTool,
)

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
logger = logging.getLogger("tiny-claw")


# ═══════════════════════════════════════════════════════════════
# 引擎工厂
# ═══════════════════════════════════════════════════════════════


def build_engine(work_dir: str, *, plan_mode: bool = False) -> AgentEngine:
    """组装引擎：挂载全部工具"""
    llm = DeepSeekProvider()
    registry = RegistryImpl()
    registry.register(ReadFileTool(work_dir))
    registry.register(WriteFileTool(work_dir))
    registry.register(BashTool(work_dir))
    registry.register(EditFileTool(work_dir))
    registry.register(SkillTool(work_dir))
    return AgentEngine(llm, registry, plan_mode=plan_mode, enable_thinking=False)


# ═══════════════════════════════════════════════════════════════
# CLI 模式
# ═══════════════════════════════════════════════════════════════


async def run_cli(prompt: str, session_id: str, work_dir: str) -> None:
    """CLI 模式：按给定 prompt 驱动 Agent"""
    engine = build_engine(work_dir)

    # 用固定 SessionID 实现断点续传
    session = await global_session_mgr.get_or_create(session_id, work_dir)
    await session.append(Message(role=Role.USER, content=prompt))

    await engine.run(session)


# ═══════════════════════════════════════════════════════════════
# 飞书模式
# ═══════════════════════════════════════════════════════════════


def run_feishu() -> None:
    """飞书模式：启动 FeishuBot + 注入审批中间件"""
    from tiny_claw.feishu import FeishuBot, create_approval_middleware

    work_dir = os.getcwd()
    engine = build_engine(work_dir)

    # ---- 创建持久化 Session ----
    session_id = os.getenv("FEISHU_SESSION_ID", "feishu-default")
    sess = Session(session_id, work_dir)

    # ---- 启动飞书 ----
    bot = FeishuBot(engine, sess)

    # ---- 注入审批中间件（延迟解析 reporter）----
    # bot.reporter 在 _handle_agent 时才绑定，但中间件在 execute 时才触发
    # 使用 lambda 延迟解析，确保运行时 reporter 已就绪
    engine.registry.use(
        create_approval_middleware(reporter=lambda: bot.reporter)
    )

    logger.info("🚀 tiny-claw 飞书模式启动（WebSocket 长连接）...")
    bot.start()


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="tiny-claw — 驾驭工程驱动研发助手")
    parser.add_argument(
        "-p",
        "--prompt",
        default="",
        help="要交给 Agent 执行的任务描述（CLI 模式）",
    )
    parser.add_argument(
        "-s",
        "--session-id",
        default="tiny-claw-default",
        help="会话 ID（多次运行相同 ID 可实现断点续传）",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["cli", "feishu"],
        default="cli",
        help="运行模式：cli（命令行）或 feishu（飞书机器人）",
    )
    args = parser.parse_args()

    # 环境变量检查
    if args.mode == "feishu":
        if not os.getenv("FEISHU_APP_ID") or not os.getenv("FEISHU_APP_SECRET"):
            logger.fatal("飞书模式需要设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
            sys.exit(1)

    if not os.getenv("DEEPSEEK_API_KEY"):
        logger.fatal("请先设置 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)

    work_dir = os.getcwd()

    if args.mode == "feishu":
        run_feishu()
    else:
        prompt = args.prompt or "帮我读取当前目录下的 secret_key.txt"
        logger.info("\n>>> 🚀 收到指令: %s", prompt)
        asyncio.run(run_cli(prompt, args.session_id, work_dir))


if __name__ == "__main__":
    main()
