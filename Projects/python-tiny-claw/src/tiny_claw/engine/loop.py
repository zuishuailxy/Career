"""Agent 核心引擎 — 对应 internal/engine/loop.go"""

import asyncio
import logging

from tiny_claw.provider import LLMProvider
from tiny_claw.schema import Message, Role, ToolCall
from tiny_claw.tools import Registry
from tiny_claw.engine.reporter import Reporter
from tiny_claw.engine.terminal_reporter import TerminalReporter
from tiny_claw.engine.session import Session
from tiny_claw.context.composer import PromptComposer
from tiny_claw.context.compactor import Compactor
from tiny_claw.tracing import trace

logger = logging.getLogger("tiny-claw.engine")

MAX_TURNS = 30
WORKING_MEMORY_LIMIT = 20  # 给压缩器充足的判断空间


class AgentEngine:
    """微型 OS 的核心驱动"""

    def __init__(
        self,
        provider: LLMProvider,
        registry: Registry,
        *,
        plan_mode: bool = False,
        enable_thinking: bool = True,
        max_parallel_tools: int = 5,
        reporter: Reporter | None = None,
        compactor: Compactor | None = None,
    ):
        self.provider = provider
        self.registry = registry
        self.plan_mode = plan_mode
        self.enable_thinking = enable_thinking
        self.reporter = reporter or TerminalReporter()
        self.compactor = compactor or Compactor(max_chars=3000, retain_last=6)
        self._tool_semaphore = asyncio.Semaphore(max_parallel_tools)

    @trace(
        "agent-run",
        process_inputs=lambda inputs: {
            "session_id": inputs["session"].id,
            "user_input": (
                inputs["session"]._history[-1].content[:200]
                if inputs["session"]._history
                else ""
            ),
        },
    )
    async def run(self, session: Session) -> None:
        """启动 Agent，处理 Session 中最后一条用户消息"""
        logger.info("唤醒会话 [%s]，锁定工作区: %s", session.id, session.work_dir)

        composer = PromptComposer(session.work_dir, plan_mode=self.plan_mode)
        system_msg = composer.build()

        turn_count = 0

        while turn_count < MAX_TURNS:
            turn_count += 1
            logger.info("========== [Turn %d] 开始 ==========", turn_count)

            # 上下文：工作记忆 + System Prompt → 压缩 → 发给 LLM
            working_memory = await session.get_working_memory(
                limit=WORKING_MEMORY_LIMIT
            )
            context = [system_msg] + working_memory
            context = self.compactor.compact(context)

            available_tools = self.registry.get_available_tools()

            # 2. Phase 1: 慢思考
            if self.enable_thinking:
                logger.info("[Phase 1] 慢思考...")
                think_resp = await self.provider.generate(context, None)
                if think_resp.content:
                    await self.reporter.on_thinking(think_resp.content)
                    await session.append(think_resp)
                    context.append(think_resp)

            # 3. Phase 2: 行动
            logger.info("[Phase 2] 行动...")
            response = await self.provider.generate(context, available_tools)
            await session.append(response)
            context.append(response)

            if response.content:
                await self.reporter.on_message(response.content)

            if not response.tool_calls:
                logger.info("任务完成，挂起等待下一条指令。")
                break

            # 4. 并发执行工具
            logger.info("并发调用 %d 个工具...", len(response.tool_calls))
            observations: list[Message | None] = [None] * len(response.tool_calls)

            async def _execute_one(idx: int, tc: ToolCall) -> None:
                async with self._tool_semaphore:
                    await self.reporter.on_tool_call(tc.name, tc.arguments)
                    result = await trace(f"tool-{tc.name}")(self.registry.execute)(tc)
                    display = (
                        result.output[:200] + "..."
                        if len(result.output) > 200
                        else result.output
                    )
                    await self.reporter.on_tool_result(
                        tc.name, display, result.is_error
                    )
                    observations[idx] = Message(
                        role=Role.USER, content=result.output, tool_call_id=tc.id
                    )

            await asyncio.gather(
                *[_execute_one(i, tc) for i, tc in enumerate(response.tool_calls)]
            )
            logger.info("所有并发工具执行完毕。")

            await session.append(*[o for o in observations if o is not None])

        else:
            logger.warning("达到最大轮次 %d，强制退出", MAX_TURNS)
