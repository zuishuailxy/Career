"""Agent 核心引擎 — 对应 internal/engine/loop.go

微型 OS 的核心驱动，实现标准的 ReAct 循环：
Thought → Action → Observation → Thought → ...
"""

import asyncio
import logging

from tiny_claw.provider import LLMProvider
from tiny_claw.schema import Message, Role, ToolCall
from tiny_claw.tools import Registry
from tiny_claw.engine.reporter import Reporter
from tiny_claw.engine.terminal_reporter import TerminalReporter
from tiny_claw.context.composer import PromptComposer
from tiny_claw.tracing import trace

logger = logging.getLogger("tiny-claw.engine")

MAX_TURNS = 30  # 安全阀：防止无限循环


class AgentEngine:
    """微型 OS 的核心驱动 — 对应 Go 的 AgentEngine struct"""

    def __init__(
        self,
        provider: LLMProvider,
        registry: Registry,
        work_dir: str,
        *,
        enable_thinking: bool = True,
        max_parallel_tools: int = 5,
        reporter: Reporter | None = None,
    ):
        self.provider = provider
        self.registry = registry
        self.work_dir = work_dir
        self.enable_thinking = enable_thinking
        self.reporter = reporter or TerminalReporter()
        self.composer = PromptComposer(work_dir)
        self._tool_semaphore = asyncio.Semaphore(max_parallel_tools)

    @trace("agent-run")
    async def run(self, user_prompt: str) -> None:
        """启动 Agent 的生命周期 — 对应 Go 的 Run()"""
        logger.info("引擎启动，锁定工作区: %s", self.work_dir)

        # 1. 初始化会话上下文 — 由 PromptComposer 动态生成
        context_history: list[Message] = [
            self.composer.build(),
            Message(role=Role.USER, content=user_prompt),
        ]

        turn_count = 0

        # 2. The Main Loop: ReAct 循环
        while turn_count < MAX_TURNS:
            turn_count += 1
            logger.info("========== [Turn %d] 开始 ==========", turn_count)

            # 获取当前挂载的所有工具
            available_tools = self.registry.get_available_tools()

            # ================================================================
            # Phase 1: 慢思考阶段 — 剥夺工具，强制规划
            # ================================================================
            if self.enable_thinking:
                logger.info("[Phase 1] 剥夺工具访问权，强制进入慢思考与规划阶段...")
                # 核心：传入 None 作为工具列表，模型只能输出纯文本思考
                think_resp = await self.provider.generate(context_history, None)
                if think_resp.content:
                    await self.reporter.on_thinking(think_resp.content)
                    context_history.append(think_resp)

            # ================================================================
            # Phase 2: 行动阶段 — 恢复工具，顺着规划执行
            # ================================================================
            logger.info("[Phase 2] 恢复工具挂载，等待模型采取行动...")
            response = await self.provider.generate(context_history, available_tools)

            # 将模型响应追加到上下文
            context_history.append(response)

            # 打印模型的文本输出
            if response.content:
                await self.reporter.on_message(response.content)

            # 3. 退出条件：没有工具调用 → 任务完成
            if not response.tool_calls:
                logger.info("模型未请求调用工具，任务完成。")
                break

            # 4. 并发执行行动 (Action) → 获取观察结果 (Observation)
            logger.info("模型请求并发调用 %d 个工具...", len(response.tool_calls))

            # 预分配固定长度列表，各协程通过索引安全写入
            observations: list[Message | None] = [None] * len(response.tool_calls)

            async def _execute_one(idx: int, tc: ToolCall) -> None:
                async with self._tool_semaphore:
                    await self.reporter.on_tool_call(tc.name, tc.arguments)
                    result = await trace(f"tool-{tc.name}")(self.registry.execute)(tc)
                    # Reporter 显示截断版（防飞书消息过长），LLM 拿到完整数据
                    display = (
                        result.output
                        if len(result.output) <= 200
                        else result.output[:200] + "..."
                    )
                    await self.reporter.on_tool_result(
                        tc.name, display, result.is_error
                    )
                    observations[idx] = Message(
                        role=Role.USER,
                        content=result.output,  # 完整数据给 LLM
                        tool_call_id=tc.id,
                    )

            # 并发启动所有任务
            await asyncio.gather(
                *[_execute_one(i, tc) for i, tc in enumerate(response.tool_calls)]
            )
            logger.info("所有并发工具执行完毕，开始聚合观察结果...")

            # 按原始顺序追加到上下文
            for obs in observations:
                if obs is not None:
                    context_history.append(obs)

            # 循环回到开头，模型带着 Observation 继续下一轮思考...
        else:
            logger.warning("达到最大轮次 %d，强制退出", MAX_TURNS)
