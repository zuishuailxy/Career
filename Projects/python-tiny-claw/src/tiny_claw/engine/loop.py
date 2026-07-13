"""Agent 核心引擎 — 对应 internal/engine/loop.go"""

import asyncio
import logging

from tiny_claw.provider import LLMProvider
from tiny_claw.schema import Message, Role, ToolCall, ToolResult
from tiny_claw.tools import Registry
from tiny_claw.engine.reporter import Reporter
from tiny_claw.engine.terminal_reporter import TerminalReporter
from tiny_claw.engine.session import Session
from tiny_claw.context.composer import PromptComposer
from tiny_claw.context.compactor import Compactor
from tiny_claw.context.recovery import RecoveryManager
from tiny_claw.engine.reminder import ReminderInjector
from tiny_claw.tracing_with_langsmith import trace

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
        # 慢思考模式下推理文本占用更多上下文，提高压缩阀值避免工具结果被挤出
        if compactor:
            self.compactor = compactor
        elif enable_thinking:
            self.compactor = Compactor(max_chars=8000, retain_last=10)
        else:
            self.compactor = Compactor(max_chars=4000, retain_last=6)
        self.recovery = RecoveryManager()
        self.reminder = ReminderInjector()
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

            # 2. Phase 1: 慢思考（仅注入推理链到上下文，不写入 Session）
            thinking_content = ""
            if self.enable_thinking:
                logger.info("[Phase 1] 慢思考...")
                think_resp = await self.provider.generate(context, None)
                # 使用 reasoning_content（纯推理）而非 content（含假 XML 工具调用）
                if think_resp.reasoning_content:
                    thinking_content = think_resp.reasoning_content
                    await self.reporter.on_thinking(thinking_content)
                    # 只将推理链注入上下文，不传递 content（避免污染 Phase 2）
                    context.append(
                        Message(role=Role.ASSISTANT, content=thinking_content)
                    )

            # 3. Phase 2: 行动
            logger.info("[Phase 2] 行动...")
            response = await self.provider.generate(context, available_tools)

            # 推理仅注入本轮上下文（提升 Phase 2 决策质量），
            # 不写入 Session（避免占用 Compactor 配额，导致工具结果被挤出）
            final_msg = Message(
                role=Role.ASSISTANT,
                content=response.content or "",
                tool_calls=response.tool_calls,
            )
            await session.append(final_msg)

            if response.content:
                await self.reporter.on_message(response.content)

            if not response.tool_calls:
                logger.info("任务完成，挂起等待下一条指令。")
                break

            # 4. 并发执行工具
            logger.info("并发调用 %d 个工具...", len(response.tool_calls))
            results: list[tuple[ToolCall, ToolResult | None]] = [
                (tc, None) for tc in response.tool_calls
            ]

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
                    results[idx] = (tc, result)

            await asyncio.gather(
                *[_execute_one(i, tc) for i, tc in enumerate(response.tool_calls)]
            )
            logger.info("所有并发工具执行完毕。")

            # 5. 后处理：恢复建议 → 死循环检测 → 写入 Session
            observations: list[Message] = []
            nudges: list[Message] = []  # 打断消息放在工具结果之后，保持 tool_call 配对

            # 检测本轮是否有工具失败（用于容错追踪）
            has_error = False
            for _, result in results:
                if result and result.is_error:
                    has_error = True
                    break

            if has_error:
                await session.mark_error_turn()

            for tc, result in results:
                if result is None:
                    continue

                # 5a. RecoveryManager 注入救援指南
                output = (
                    self.recovery.analyze_and_inject(result.output)
                    if result.is_error
                    else result.output
                )

                observations.append(
                    Message(role=Role.USER, content=output, tool_call_id=tc.id)
                )

                # 5b. ReminderInjector 死循环打断检测（延迟到工具结果之后）
                nudge = self.reminder.check_and_inject(tc, result)
                if nudge:
                    nudges.append(nudge)

            await session.append(*(observations + nudges))

        else:
            logger.warning("达到最大轮次 %d，强制退出", MAX_TURNS)

        # 记录本次会话的总 Turn 数（供评测系统收集顺滑度指标）
        session.total_turns = turn_count

    # ------------------------------------------------------------------
    # AgentRunner 实现 — 供 SubagentTool 反向调用
    # ------------------------------------------------------------------
    async def run_sub(
        self,
        task_prompt: str,
        read_only_registry: Registry,
        reporter: Reporter | None = None,
    ) -> str:
        """启动一个匿名的、只读的子智能体任务。

        不依赖外部 Session，使用精简的独立循环，打完就跑。
        每个子智能体拥有独立的 Semaphore、RecoveryManager，互不干扰。
        """
        import uuid

        # ---- 隔离资源：防止并行子智能体互相污染 ----
        sub_id = uuid.uuid4().hex[:6]  # 唯一 ID，用于日志和 Reporter 区分
        sub_semaphore = asyncio.Semaphore(
            3
        )  # 独立信号量（子智能体只有 2 个工具，3 足够）
        sub_recovery = RecoveryManager()  # 独立恢复管理器（不污染主引擎的失败计数器）
        sub_prefix = f"[Sub:{sub_id}]"

        # 子智能体专用 System Prompt
        context: list[Message] = [
            Message(
                role=Role.SYSTEM,
                content=(
                    "你是一个专门负责深度探索的探路者 (Explorer Subagent)。\n"
                    "你的任务是根据主架构师的指令，在当前工作区内仔细阅读代码、"
                    "查阅日志，搜集足够的信息。\n"
                    "\n"
                    "【核心纪律】\n"
                    "1. 你必须、且只能依靠内置工具（如 bash 的 find/grep，"
                    "或 read_file）去寻找答案。绝对不允许凭空捏造或猜测！\n"
                    "2. 如果你没有找到确切的答案，你必须继续使用工具深入搜索。\n"
                    "3. 当且仅当你找到了确切的线索后，停止调用工具，"
                    "直接输出一段纯文本作为你的终极汇报。"
                    "主架构师会根据你的汇报来做下一步决策。"
                ),
            ),
            Message(role=Role.USER, content=task_prompt),
        ]

        r = reporter or self.reporter
        max_sub_turns = 10
        turn_count = 0

        logger.info("[Subagent:%s] 🚀 探路者出发...", sub_id)

        while True:
            turn_count += 1
            if turn_count > max_sub_turns:
                logger.warning(
                    "[Subagent:%s] 超过 %d 轮被强制召回", sub_id, max_sub_turns
                )
                return (
                    f"子智能体探索过于深入，超过 {max_sub_turns} 轮被强制召回，"
                    "请主 Agent 给它更明确的指令"
                )

            available_tools = read_only_registry.get_available_tools()
            compacted = self.compactor.compact(context)

            # 子任务要求急速响应，不启用慢思考，直接预测行动
            response = await self.provider.generate(compacted, available_tools)
            context.append(response)

            # 子智能体一旦不调用工具了，说明它做好了总结汇报
            if not response.tool_calls:
                logger.info("[Subagent:%s] ✅ 探索完成", sub_id)
                return response.content or "(子智能体未产生输出)"

            # ---- 并发执行只读工具 ----
            results: list[tuple[ToolCall, ToolResult | None]] = [
                (tc, None) for tc in response.tool_calls
            ]

            async def _execute_sub(idx: int, tc: ToolCall) -> None:
                async with sub_semaphore:
                    await r.on_tool_call(f"{sub_prefix} {tc.name}", tc.arguments)
                    result = await trace(f"sub-{tc.name}")(read_only_registry.execute)(
                        tc
                    )

                    output = (
                        sub_recovery.analyze_and_inject(result.output)  # ← 独立恢复
                        if result.is_error
                        else result.output
                    )

                    display = output[:200] + "..." if len(output) > 200 else output
                    await r.on_tool_result(
                        f"{sub_prefix} {tc.name}", display, result.is_error
                    )
                    results[idx] = (tc, result)

            await asyncio.gather(
                *[_execute_sub(i, tc) for i, tc in enumerate(response.tool_calls)]
            )

            # 将工具观察注入上下文
            for tc, result in results:
                if result:
                    context.append(
                        Message(
                            role=Role.USER,
                            content=result.output,
                            tool_call_id=tc.id,
                        )
                    )
