"""MCP 客户端接入 — 让 Agent 无需改代码即可使用标准 MCP Server 的工具

只做 **Client 侧**：连接标准 MCP server、发现工具、包装成 `BaseTool` 注册进
现有 `Registry`。协议本身由官方 `mcp` SDK 负责，本包不做协议实现。

连接管理基于官方 `ClientSessionGroup`（边界划分见 `docs/MCP_INTEGRATION_PLAN.md` §12.9）：
SDK 管协议与连接，本包管配置降级、适配、错误码与审批接缝。

依赖是 optional extra：`pip install -e ".[mcp]"`
"""

from tiny_claw.mcp.client import MCPManager, tool_input_schema
from tiny_claw.mcp.loader import ServerConfig, load_servers

__all__ = [
    "MCPManager",
    "ServerConfig",
    "load_servers",
    "tool_input_schema",
]
