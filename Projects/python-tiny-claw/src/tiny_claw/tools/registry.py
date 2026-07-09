"""工具注册表 — 对应 internal/tools/registry.go"""

import logging
from abc import ABC, abstractmethod

from tiny_claw.schema import ToolCall, ToolDefinition, ToolResult
from tiny_claw.tools.base import BaseTool

logger = logging.getLogger("tiny-claw.tools")


class Registry(ABC):
    """工具的注册与分发执行接口 — 对应 Go 的 Registry interface"""

    @abstractmethod
    def register(self, tool: BaseTool) -> None:
        """挂载一个新的工具到系统中"""
        ...

    @abstractmethod
    def get_available_tools(self) -> list[ToolDefinition]:
        """返回当前系统挂载的所有可用工具的 Schema"""
        ...

    @abstractmethod
    async def execute(self, call: ToolCall) -> ToolResult:
        """实际路由并执行模型请求的工具调用"""
        ...


class RegistryImpl(Registry):
    """Registry 的默认实现 — 基于 dict 的 O(1) 工具路由"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        name = tool.name()
        if name in self._tools:
            logger.warning("工具 '%s' 已被注册，将被覆盖。", name)
        self._tools[name] = tool
        logger.info("成功挂载工具: %s", name)

    def get_available_tools(self) -> list[ToolDefinition]:
        return [tool.definition() for tool in self._tools.values()]

    async def execute(self, call: ToolCall) -> ToolResult:
        # 1. 路由查找：找不到工具说明模型产生了幻觉
        tool = self._tools.get(call.name)
        if tool is None:
            err_msg = f"Error: 系统中不存在名为 '{call.name}' 的工具。"
            return ToolResult(tool_call_id=call.id, output=err_msg, is_error=True)

        # 2. 执行工具逻辑
        try:
            output = await tool.execute(call.arguments)
        except Exception as e:
            return ToolResult(
                tool_call_id=call.id,
                output=f"Error executing {call.name}: {e}",
                is_error=True,
            )

        # 3. 封装结果
        return ToolResult(tool_call_id=call.id, output=output, is_error=False)
