"""MCP 客户端测试（重构后：连接管理交给官方 ClientSessionGroup）

**全部使用假 group**，不发真实请求、不起子进程 —— 单测不该依赖网络与 npx。
真实连通性由 `tools/probe_mcp.py`（Phase 0 探针）负责。

这里守住的四件事：
1. 配置加载**坏配置不能崩启动**（外部依赖不可靠是常态）
2. SDK 字段名坑：属性是 `input_schema`，协议名 `inputSchema` 只是 alias
3. 命名空间：MCP 工具与内置工具同名时不能静默覆盖（Phase 0 实测撞上）
4. 单例 + 幂等 + 清理：因为引擎会被反复重建（飞书每条消息一次）
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

from tiny_claw.mcp.client import MCPManager, _name_hook, tool_input_schema
from tiny_claw.mcp.loader import ServerConfig, load_servers

# ─────────────────────────────────────────────────────────────
# 假对象
# ─────────────────────────────────────────────────────────────


@dataclass
class FakeTool:
    name: str
    description: str = ""
    input_schema: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )


class FakeGroup:
    """模拟 ClientSessionGroup 的相关行为（tools 聚合 + sessions + 连接失败）"""

    def __init__(self, tools_by_marker: dict | None = None, fail_markers=()):
        self._tools = tools_by_marker or {}
        self._fail = set(fail_markers)
        self.tools: dict[str, FakeTool] = {}
        self.sessions: dict[str, object] = {}
        self.connected: list[str] = []
        self.session_params: list[object] = []

    async def connect_to_server(self, params, session_params=None):
        # 用 args[0] 当可识别的 server 标记
        marker = params.args[0] if params.args else params.command
        if marker in self._fail:
            raise RuntimeError(f"连不上 {marker}")
        self.connected.append(marker)
        self.session_params.append(session_params)
        self.sessions[marker] = object()
        for tool in self._tools.get(marker, []):
            # 用真实的 hook 生成名字：命名规则变了测试要能发现
            self.tools[_name_hook(tool, SimpleNamespace(name=marker))] = FakeTool(tool)


def cfg(name: str, **kw) -> ServerConfig:
    """构造一个把 name 塞进 args 的配置，便于 FakeGroup 识别"""
    return ServerConfig(name=name, command="npx", args=[name], **kw)


def write_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


# ─────────────────────────────────────────────────────────────
# 1. 配置加载：坏配置绝不能崩启动
# ─────────────────────────────────────────────────────────────


def test_load_servers_parses_community_format(tmp_path):
    p = write_config(
        tmp_path,
        {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "env": {"FOO": "bar"},
                    "approval": "never",
                    "timeout": 120,
                }
            }
        },
    )
    servers = load_servers(p)
    assert len(servers) == 1
    s = servers[0]
    assert (s.name, s.command) == ("filesystem", "npx")
    assert s.args[-1] == "/tmp"
    assert s.env == {"FOO": "bar"}
    assert s.approval == "never" and s.timeout == 120
    assert s.enabled is True


def test_missing_file_is_not_an_error(tmp_path):
    """没配 MCP 是完全正常的用法，不该报错"""
    assert load_servers(tmp_path / "nope.json") == []


def test_broken_json_does_not_raise(tmp_path):
    p = tmp_path / "mcp.json"
    p.write_text("{ this is not json", encoding="utf-8")
    assert load_servers(p) == []


def test_missing_mcpservers_key_does_not_raise(tmp_path):
    p = write_config(tmp_path, {"servers": {}})
    assert load_servers(p) == []


def test_one_bad_server_does_not_kill_the_others(tmp_path):
    """单条配置写错只跳过它自己"""
    p = write_config(
        tmp_path,
        {
            "mcpServers": {
                "broken": {"args": ["x"]},  # 缺 command
                "notobj": "oops",
                "good": {"command": "npx"},
            }
        },
    )
    assert [s.name for s in load_servers(p)] == ["good"]


def test_illegal_approval_falls_back_to_safest(tmp_path):
    """approval 写错时必须回退到最保守的 always，不能变成放行"""
    p = write_config(
        tmp_path, {"mcpServers": {"x": {"command": "c", "approval": "yolo"}}}
    )
    assert load_servers(p)[0].approval == "always"


def test_bad_args_and_env_are_coerced(tmp_path):
    p = write_config(
        tmp_path,
        {"mcpServers": {"x": {"command": "c", "args": "not-a-list", "env": [1]}}},
    )
    s = load_servers(p)[0]
    assert s.args == [] and s.env == {}


def test_merged_env_appends_extra_path(monkeypatch):
    """npx 不在默认 PATH 时会连不上，且报错只有 No such file or directory"""
    monkeypatch.setenv("PATH", "/usr/bin")
    merged = ServerConfig(name="x", command="npx", env={"A": "1"}).merged_env(
        "/opt/node/bin"
    )
    assert merged["A"] == "1"
    assert merged["PATH"].startswith("/opt/node/bin")
    assert "/usr/bin" in merged["PATH"]


# ─────────────────────────────────────────────────────────────
# 2. 命名空间：交给官方 hook（Phase 0 实测：与内置工具同名）
# ─────────────────────────────────────────────────────────────


def test_name_hook_isolates_from_builtin_names():
    # 实测：filesystem server 的工具就叫 read_file / write_file / edit_file
    got = _name_hook("read_file", SimpleNamespace(name="secure-filesystem-server"))
    assert got == "mcp__secure-filesystem-server__read_file"
    assert got != "read_file"  # 不会顶掉内置工具


def test_name_hook_tolerates_missing_server_name():
    assert _name_hook("t", SimpleNamespace()) == "mcp__unknown__t"


# ─────────────────────────────────────────────────────────────
# 3. SDK 字段名坑（input_schema vs inputSchema）
# ─────────────────────────────────────────────────────────────


def test_input_schema_prefers_sdk_v2_field():
    tool = FakeTool(name="t", input_schema={"type": "object", "properties": {"p": {}}})
    assert tool_input_schema(tool)["properties"] == {"p": {}}


def test_input_schema_falls_back_to_protocol_name():
    """老/新 SDK 只暴露协议名时也要能取到，不能 AttributeError"""

    class LegacyTool:
        inputSchema = {"type": "object", "properties": {"legacy": {}}}

    assert tool_input_schema(LegacyTool())["properties"] == {"legacy": {}}


def test_input_schema_defaults_when_absent():
    assert tool_input_schema(object()) == {"type": "object", "properties": {}}


# ─────────────────────────────────────────────────────────────
# 4. MCPManager：聚合 / 降级 / 幂等 / 清理
# ─────────────────────────────────────────────────────────────


async def test_preload_aggregates_namespaced_tools():
    group = FakeGroup({"fs": ["read_file", "list_directory"]})
    mgr = MCPManager(servers=[cfg("fs")])
    names = await mgr.preload(group=group)
    # preload 对名字排序：工具清单顺序确定，便于复现与比对
    assert names == ["mcp__fs__list_directory", "mcp__fs__read_file"]
    assert mgr.discovered == names
    assert group.session_params[0] is not None  # 超时参数传给了 SDK
    await mgr.aclose()


async def test_preload_skips_disabled_server():
    group = FakeGroup({"fs": ["a"]})
    mgr = MCPManager(servers=[cfg("fs", enabled=False)])
    assert await mgr.preload(group=group) == []
    assert group.connected == []
    await mgr.aclose()


async def test_one_server_failing_does_not_break_the_other():
    """外部依赖不可靠是常态：一个连不上，其余照常，且启动不失败"""
    group = FakeGroup({"good": ["t"]}, fail_markers={"bad"})
    mgr = MCPManager(servers=[cfg("bad"), cfg("good")])
    names = await mgr.preload(group=group)
    assert names == ["mcp__good__t"]
    await mgr.aclose()


async def test_connect_timeout_is_skipped_not_fatal():
    """连接超时只 warning，不能让 Agent 起不来"""

    class TimeoutGroup(FakeGroup):
        async def connect_to_server(self, params, session_params=None):
            raise TimeoutError

    mgr = MCPManager(servers=[cfg("slow")])
    assert await mgr.preload(group=TimeoutGroup()) == []
    await mgr.aclose()


async def test_preload_is_idempotent():
    """飞书模式每条消息都会重建引擎 → 注册可重复，连接只建立一次"""
    group = FakeGroup({"fs": ["a"]})
    mgr = MCPManager(servers=[cfg("fs")])
    first = await mgr.preload(group=group)
    second = await mgr.preload(group=group)
    assert first == second == ["mcp__fs__a"]
    assert group.connected == ["fs"]  # 没有重复连接
    await mgr.aclose()


async def test_lifespan_cleans_up_after_exit():
    group = FakeGroup({"fs": ["a"]})
    mgr = MCPManager(servers=[cfg("fs")])
    async with mgr.lifespan(group=group) as m:
        assert m.discovered == ["mcp__fs__a"]
    assert mgr.discovered == []
    assert mgr.group is None


async def test_tools_snapshot_exposes_raw_objects_for_adapter():
    """Phase 2 的 adapter 需要拿到原始 Tool 对象来读 input_schema"""
    group = FakeGroup({"fs": ["read_file"]})
    mgr = MCPManager(servers=[cfg("fs")])
    await mgr.preload(group=group)
    snap = mgr.tools_snapshot()
    assert list(snap) == ["mcp__fs__read_file"]
    assert tool_input_schema(snap["mcp__fs__read_file"])["type"] == "object"
    await mgr.aclose()


def test_no_config_means_no_servers(tmp_path):
    """没配 MCP 时应该是个空壳，而不是报错"""
    mgr = MCPManager(config_path=tmp_path / "absent.json")
    assert mgr.servers == []
    assert mgr.discovered == []
    assert mgr.tools_snapshot() == {}


def test_singleton_is_shared_and_resettable():
    MCPManager.reset_instance()
    a = MCPManager.instance()
    assert a is MCPManager.instance()
    MCPManager.reset_instance()
    assert MCPManager.instance() is not a
