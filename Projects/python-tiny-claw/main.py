"""tiny-claw 入口 — 对应 cmd/claw/main.go

支持两种运行模式：
  - CLI 模式：  python main.py -p "任务描述" [-d /path/to/workdir] [-s session_id]
  - 飞书模式：  python main.py --mode feishu
"""

import argparse
import asyncio
import logging
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from tiny_claw.engine import AgentEngine
from tiny_claw.engine.session import Session, global_session_mgr
from tiny_claw.engine.terminal_reporter import TerminalReporter
from tiny_claw.provider import DeepSeekProvider
from tiny_claw.schema import Message, Role
from tiny_claw.tools import RegistryImpl
from tiny_claw.tools.subagent import SubagentTool
from tiny_claw.tools.builtin import (
    BashTool,
    EditFileTool,
    ReadFileTool,
    SkillTool,
    WriteFileTool,
)
from tiny_claw.tracing import CostTracker, start_span, end_span, export_trace

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
logger = logging.getLogger("tiny-claw")


# ═══════════════════════════════════════════════════════════════
# 引擎工厂
# ═══════════════════════════════════════════════════════════════


def build_engine(
    work_dir: str, *, plan_mode: bool = False, enable_thinking: bool = True
) -> AgentEngine:
    """组装引擎：挂载全部工具 + 子智能体 + 费用追踪"""
    raw_llm = DeepSeekProvider()
    llm = CostTracker(raw_llm, model=raw_llm.model)

    main_registry = RegistryImpl()
    main_registry.register(ReadFileTool(work_dir))
    main_registry.register(WriteFileTool(work_dir))
    main_registry.register(BashTool(work_dir))
    main_registry.register(EditFileTool(work_dir))
    main_registry.register(SkillTool(work_dir))

    engine = AgentEngine(
        llm,
        main_registry,
        plan_mode=plan_mode,
        enable_thinking=enable_thinking,
    )

    # 只读子智能体注册表（防御沙箱）
    read_only_registry = RegistryImpl()
    read_only_registry.register(ReadFileTool(work_dir))
    read_only_registry.register(BashTool(work_dir))

    main_registry.register(
        SubagentTool(
            runner=engine,
            read_only_registry=read_only_registry,
            reporter=engine.reporter,
        )
    )

    return engine


# ═══════════════════════════════════════════════════════════════
# CLI 模式
# ═══════════════════════════════════════════════════════════════


async def run_cli(
    prompt: str,
    session_id: str,
    work_dir: str,
    *,
    plan_mode: bool = False,
    enable_thinking: bool = True,
) -> None:
    """CLI 模式：按给定 prompt 驱动 Agent"""
    print("=" * 50)
    print("🚀 启动 tiny-claw CLI 引擎...")
    print(f"📁 锁定工作区: {work_dir}")
    print(
        f"🧠 慢思考: {'开启' if enable_thinking else '关闭'} | 📋 计划模式: {'开启' if plan_mode else '关闭'}"
    )
    print("=" * 50)

    engine = build_engine(
        work_dir, plan_mode=plan_mode, enable_thinking=enable_thinking
    )

    # 获取持久化 Session + 绑定 CostTracker
    session = await global_session_mgr.get_or_create(session_id, work_dir)
    if isinstance(engine.provider, CostTracker):
        engine.provider.bind_session(session)

    # 全息追踪：开启根 Span
    root_span = start_span("CLI.TaskRun")
    root_span.add_attribute("prompt", prompt[:200])

    # 初始化彩色终端输出器
    engine.reporter = TerminalReporter()

    print(f"\n🎯 收到任务: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n")

    await session.append(Message(role=Role.USER, content=prompt))

    try:
        await engine.run(session)
    except Exception as e:
        logger.error("引擎运行崩溃: %s", e)
        raise
    finally:
        end_span(root_span)
        export_trace(work_dir, session.id)

    # 打印汇总
    print("\n" + "=" * 50)
    print("✨ 任务圆满结束。")
    if session.total_prompt_tokens:
        print(
            f"💰 Session 累计消耗: ¥{session.total_cost_cny:.6f} | "
            f"Token: 输入 {session.total_prompt_tokens}, "
            f"输出 {session.total_completion_tokens}"
        )
        print(f"📊 容错: {session.error_turns} 次失败轮 / 共 {session.total_turns} 轮")
    print("=" * 50)


# ═══════════════════════════════════════════════════════════════
# 飞书模式
# ═══════════════════════════════════════════════════════════════


def run_feishu(work_dir: str) -> None:
    """飞书模式（AgentOps）：启动 FeishuBot + 审批中间件 + 生产级配置"""
    from tiny_claw.feishu import FeishuBot, create_approval_middleware

    work_dir = os.path.abspath(work_dir)
    logger.info("🚀 正在启动 tiny-claw AgentOps 飞书服务端...")
    logger.info("📁 工作区: %s", work_dir)

    # 引擎工厂：每次消息创建独立引擎（计费隔离 + 安全防御）
    def engine_factory(session: Session) -> AgentEngine:
        # AgentOps 生产环境：关闭慢思考（省 Token）、关闭计划模式（运维不需要）
        engine = build_engine(
            work_dir,
            plan_mode=False,
            enable_thinking=False,
        )
        if isinstance(engine.provider, CostTracker):
            engine.provider.bind_session(session)
        # 注入审批中间件：高危操作挂起等待飞书人工确认
        engine.registry.use(create_approval_middleware(reporter=lambda: bot.reporter))
        return engine

    bot = FeishuBot(engine_factory, work_dir)

    logger.info("🛡️ 安全防御 Middleware 已挂载。")
    logger.info("📡 飞书长连接已启动，等待消息...")
    bot.start()


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="tiny-claw — 驾驭工程驱动研发助手")
    parser.add_argument(
        "-p",
        "--prompt",
        default=None,
        help="要交给 Agent 执行的任务描述（CLI 模式必填）",
    )
    parser.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Agent 运行的工作区目录路径（默认为当前目录）",
    )
    parser.add_argument(
        "-s",
        "--session-id",
        default="cli_default_session",
        help="会话 ID（多次运行相同 ID 可实现断点续传）",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["cli", "feishu"],
        default="cli",
        help="运行模式：cli（命令行）或 feishu（飞书机器人）",
    )
    parser.add_argument(
        "--plan-mode",
        action="store_true",
        default=False,
        help="开启计划模式（自动创建 PLAN.md / TODO.md，支持断点续传）",
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        default=False,
        help="关闭慢思考（Phase 1 Thinking），减少 Token 消耗",
    )
    args = parser.parse_args()

    # 环境变量检查
    if args.mode == "feishu":
        if not os.getenv("FEISHU_APP_ID") or not os.getenv("FEISHU_APP_SECRET"):
            logger.fatal("飞书模式需要设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
            sys.exit(1)
    else:
        if not args.prompt:
            parser.error("CLI 模式必须指定 -p/--prompt")

    if not os.getenv("DEEPSEEK_API_KEY"):
        logger.fatal("请先设置 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)

    work_dir = os.path.abspath(args.dir)

    if args.mode == "feishu":
        run_feishu(work_dir)
    else:
        asyncio.run(
            run_cli(
                args.prompt,
                args.session_id,
                work_dir,
                plan_mode=args.plan_mode,
                enable_thinking=not args.no_thinking,
            )
        )


if __name__ == "__main__":
    main()
