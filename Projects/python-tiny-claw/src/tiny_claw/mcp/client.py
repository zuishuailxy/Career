"""MCP 连接管理 — 官方 `ClientSessionGroup` 的薄封装

**边界划清楚**（甄别标准见 `docs/MCP_INTEGRATION_PLAN.md` §12.9）：

| 谁负责 | 内容 |
|---|---|
| **官方 SDK** | 协议（JSON-RPC / stdio）、握手与发现、**多 server 生命周期**、**工具聚合**、**命名空间**、**按命名空间路由调用**、超时/进度/MRTR |
| **本项目** | 配置从哪来 + 坏配置降级、`Tool` → `BaseTool` 适配（Phase 2）、MCP 错误 → `[ERR:MCP_*]`、审批策略、以及「同步 `build_engine()` + 飞书每条消息新建引擎」的接缝 |

为什么不自写连接管理：SDK 的 `ClientSessionGroup` 已经做好且做得更多（实测见 plan §12.9）。
自己再写一遍 = 重复劳动 + 白白少掉 MRTR / 超时这些内建能力。

⚠️ **task 归属**：SDK 基于 anyio task group，`enter` 与 `exit` 必须在同一个 asyncio task 内。
所以本模块只暴露 `lifespan()`（同 task 成对）与 `aclose()`，不要跨 task 调用。
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any, ClassVar

from tiny_claw import config
from tiny_claw.mcp.loader import ServerConfig, load_servers

logger = logging.getLogger("tiny-claw.mcp.client")


def tool_input_schema(tool: Any) -> dict:
    """取 MCP tool 的入参 schema。

    ⚠️ 字段名坑（Phase 0 实测）：MCP **线协议**上的字段叫 `inputSchema`，
    但 Python SDK v2 的模型属性是 **`input_schema`**（`inputSchema` 只是 pydantic
    alias），照协议名写会直接 `AttributeError: 'Tool' object has no attribute
    'inputSchema'`。这里两个都试，SDK 再改名也不至于整条链断掉。
    """
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)
    return schema or {"type": "object", "properties": {}}


def _name_hook(name: str, server_info: Any) -> str:
    """命名空间：`mcp__{server}__{tool}`。

    为什么必须有：Phase 0 实测 filesystem server 的工具叫
    `read_file` / `write_file` / `edit_file`，与本项目内置工具**完全同名**，
    而 `registry.register()` 遇重名是 warning 后**静默覆盖** —— 内置工具会凭空消失。

    为什么用 `server_info.name`（自报名）而不是配置里的 key：官方 hook 只传
    `(tool_name, server_info)`，**拿不到我们的配置 key**。自报名的代价是名字更长
    （`mcp__secure-filesystem-server__read_file`），但更准确、不依赖用户怎么命名。
    """
    server = getattr(server_info, "name", None) or "unknown"
    return f"mcp__{server}__{name}"


def _to_stdio_params(cfg: ServerConfig) -> Any:
    """ServerConfig → SDK 的 StdioServerParameters（含 PATH 补齐）"""
    from mcp import StdioServerParameters

    return StdioServerParameters(
        command=cfg.command,
        args=cfg.args,
        env=cfg.merged_env(config.MCP_EXTRA_PATH),
    )


def _new_group() -> Any:
    """延迟 import：`mcp` 是 optional extra，没装也不该让本包 import 失败"""
    from mcp.client.session_group import ClientSessionGroup

    return ClientSessionGroup(component_name_hook=_name_hook)


def _new_session_params(timeout: float | None) -> Any:
    from mcp.client.session_group import ClientSessionParameters

    return ClientSessionParameters(read_timeout_seconds=timeout)


class MCPManager:
    """MCP 连接的进程级持有者（单例）

    **为什么连接不挂在引擎上**（plan §3 矛盾 A）：`cli.py:43` 的 `build_engine()`
    是同步函数，而连接是异步且昂贵的（要拉子进程）；飞书模式还**每条消息都新建引擎**。
    → 连接提为进程级单例，`preload()` 只跑一次；引擎每次重建只做零成本的注册。

    用法（CLI 模式，同 task 生命周期）：

        async with MCPManager.instance().lifespan() as mgr:
            mgr.register_into(engine.registry)      # Phase 2
            await engine.run(session)
    """

    _instance: ClassVar["MCPManager | None"] = None

    @classmethod
    def instance(cls) -> "MCPManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """测试用：丢弃单例"""
        cls._instance = None

    def __init__(
        self,
        config_path: str | Path | None = None,
        servers: list[ServerConfig] | None = None,
    ):
        if servers is None and config.MCP_ENABLED:
            servers = load_servers(config_path or config.MCP_CONFIG_PATH)
        self._servers: list[ServerConfig] = servers or []
        self._stack = AsyncExitStack()
        self._group: Any | None = None
        self._names: list[str] = []
        self._preloaded = False

    # ------------------------------------------------------------------
    # 只读视图
    # ------------------------------------------------------------------
    @property
    def servers(self) -> list[ServerConfig]:
        return list(self._servers)

    @property
    def group(self) -> Any | None:
        """底层 ClientSessionGroup（Phase 2 的 adapter 与测试消费）"""
        return self._group

    @property
    def discovered(self) -> list[str]:
        """聚合到的工具全名（已带命名空间）"""
        return list(self._names)

    def tools_snapshot(self) -> dict[str, Any]:
        """工具全名 → 原始 MCP `Tool` 对象（Phase 2 的 adapter 消费）"""
        if self._group is None:
            return {}
        return dict(self._group.tools)

    # ------------------------------------------------------------------
    # 预发现（异步，只跑一次）
    # ------------------------------------------------------------------
    async def preload(self, group: Any | None = None) -> list[str]:
        """接入所有启用的 server，返回聚合到的工具全名。

        **任何一个 server 失败都不影响其他 server，也不阻塞启动** ——
        外部依赖不可靠是常态（npx 下载失败、路径写错、server 崩了），
        不能让 Agent 起不来。

        Args:
            group: 供测试注入的假 group（不传则用官方 `ClientSessionGroup`）
        """
        if self._preloaded:
            return list(self._names)

        if group is not None:
            self._group = group
        else:
            # 交给自己的 exit_stack 管生命周期，保证 enter/exit 同 task
            self._group = await self._stack.enter_async_context(_new_group())

        for cfg in self._servers:
            if not cfg.enabled:
                logger.info("[MCP] server '%s' 已禁用，跳过", cfg.name)
                continue
            timeout = cfg.timeout or config.MCP_CONNECT_TIMEOUT
            try:
                async with asyncio.timeout(timeout):
                    await self._group.connect_to_server(
                        _to_stdio_params(cfg),
                        _new_session_params(config.MCP_CALL_TIMEOUT),
                    )
            except TimeoutError:
                logger.warning(
                    "[MCP] server '%s' 连接超时（%ds），已跳过", cfg.name, timeout
                )
                continue
            except Exception as e:  # noqa: BLE001 —— 外部依赖，失败即降级
                logger.warning("[MCP] server '%s' 接入失败，已跳过: %s", cfg.name, e)
                continue
            logger.info("[MCP] server '%s' 已接入", cfg.name)

        self._names = sorted(self._group.tools.keys())
        self._preloaded = True
        logger.info(
            "[MCP] 就绪：%d 个 server / %d 个工具",
            len(getattr(self._group, "sessions", {}) or {}),
            len(self._names),
        )
        return list(self._names)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    @asynccontextmanager
    async def lifespan(self, group: Any | None = None) -> AsyncIterator["MCPManager"]:
        """CLI 模式：preload 与 aclose 在**同一个 task** 内成对出现"""
        await self.preload(group)
        try:
            yield self
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        """关闭全部连接并回收子进程"""
        try:
            await self._stack.aclose()
        except Exception as e:  # noqa: BLE001 —— 关闭失败不应掩盖主流程
            logger.warning("[MCP] 关闭连接时出错: %s", e)
        self._group = None
        self._names = []
        self._preloaded = False
