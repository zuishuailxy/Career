"""Agent 核心引擎 — 对应 internal/engine/loop.go

微型 OS 的核心驱动，实现标准的 ReAct 循环：
Thought → Action → Observation → Thought → ...
"""

import logging

from tiny_claw.provider import LLMProvider
from tiny_claw.schema import Message, Role
from tiny_claw.tools import Registry
from tiny_claw.tracing import trace, trace_tool

logger = logging.getLogger("tiny-claw.engine")

MAX_TURNS = 30  # 安全阀：防止无限循环


class AgentEngine:
    """微型 OS 的核心驱动 — 对应 Go 的 AgentEngine struct"""

    def __init__(
        self,
        provider: LLMProvider,
        registry: Registry,
        work_dir: str,
        enable_thinking: bool = True,
    ):
        self.provider = provider
        self.registry = registry
        self.work_dir = work_dir  # 工作区：Agent 的物理边界
        self.enable_thinking = enable_thinking  # 【新增】慢思考模式开关

    @trace("agent-run")
    async def run(self, user_prompt: str) -> None:
        """启动 Agent 的生命周期 — 对应 Go 的 Run()"""
        logger.info("引擎启动，锁定工作区: %s", self.work_dir)

        # 1. 初始化会话上下文
        # TODO: 后续由动态 Prompt 组装器加载 AGENTS.md
        context_history: list[Message] = [
            Message(
                role=Role.SYSTEM,
                content=(
                    "You are tiny-claw, an expert coding assistant. "
                    "You have full access to tools in the workspace."
                ),
            ),
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
                    print(f"🧠 [内部思考 Trace]: {think_resp.content}")
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
                print(f"🤖 [对外回复]: {response.content}")

            # 3. 退出条件：没有工具调用 → 任务完成
            if not response.tool_calls:
                logger.info("模型未请求调用工具，任务完成。")
                break

            # 4. 执行行动 (Action) → 获取观察结果 (Observation)
            logger.info("模型请求调用 %d 个工具...", len(response.tool_calls))

            for tc in response.tool_calls:
                logger.info("  -> 🛠️ 执行工具: %s, 参数: %s", tc.name, tc.arguments)

                result = await trace_tool(self.registry.execute)(tc)

                if result.is_error:
                    logger.info("  -> ❌ 工具执行报错: %s", result.output)
                else:
                    logger.info(
                        "  -> ✅ 工具执行成功 (返回 %d 字节)", len(result.output)
                    )

                # Observation 封装为 User Message 追加到上下文
                # ToolCallID 必须携带！这是维系推理链条的关键
                observation = Message(
                    role=Role.USER,
                    content=result.output,
                    tool_call_id=tc.id,
                )
                context_history.append(observation)

            # 循环回到开头，模型带着 Observation 继续下一轮思考...
        else:
            logger.warning("达到最大轮次 %d，强制退出", MAX_TURNS)
