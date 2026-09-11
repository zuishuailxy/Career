# MCP 客户端集成设计（tiny-claw）

> 目标：让 tiny-claw 具备 **MCP Client** 能力——连接标准 MCP Server，自动发现其工具并注册进现有 `Registry`，对模型表现为「多了一批普通工具」。
>
> 本文所有落点均在当前代码上逐行核验（2026-09-11），**非推测**。凡标注「⚠️ 难点」的地方，是这次改造真正的技术含量。

---

## 0. 这份设计解决什么

上一版方案停留在「加个 adapter 就行」的层面，核对代码后发现三处不成立，以及一处被忽略的核心矛盾。本版围绕这些重新设计：

| # | 上一版的问题 | 本版如何解决 |
|---|---|---|
| 1 | 假设 `build_engine()` 可 await | `build_engine()` 是**同步**的 → 拆分「异步预发现」与「同步注册」两步 |
| 2 | 未考虑引擎会被反复重建 | 飞书模式**每条消息新建引擎** → 连接提升为**进程级单例**，与引擎解耦 |
| 3 | 只说「挂审批中间件」 | 审批兜底是**默认放行** → 必须新增 `mcp__` 前缀策略，否则第三方工具裸奔 |
| 4 | 未处理并发 | 引擎**并发调工具** vs stdio **单通道会话** → per-server 串行锁 |

---

## 1. 目标 / 非目标

**要做**
- 作为 MCP **Client**，支持 stdio 传输连接标准 MCP Server
- 自动 `list_tools()` → 包装成 `BaseTool` → 注册进 `Registry`，**不修改引擎主循环**
- 工具调用纳入既有体系：错误码自愈、审批中间件、超时、日志
- 支持多 Server，工具名互不冲突

**不做（明确边界，面试要主动说）**
- 不实现 MCP **Server** 端
- 不实现 MCP **协议本身**（用官方 `mcp` Python SDK）
- Phase 1 不做 Streamable HTTP / SSE 传输（只做 stdio）
- 不做 MCP Resources / Prompts / Sampling（只做 **Tools**）
- 不做自动重连（失败先降级为错误码，重连留后续）

---

## 2. 现状约束（逐行核验）

| 位置 | 事实 | 对设计的硬约束 |
|---|---|---|
| `tools/base.py:9` | `BaseTool` 只有 `name()` / `definition()` / `async execute(args) -> str` | **没有 `close()` / `setup()` 生命周期钩子** → 连接不能放在工具里 |
| `schema/__init__.py:83` | `ToolDefinition(name, description, input_schema: dict)` | ✅ 与 MCP `inputSchema` **同构**，可零转换透传 |
| `tools/registry.py:56` | `register()` 重名 → **只 warning 然后覆盖** | ⚠️ 必须做命名空间，否则静默顶掉内置工具 |
| `tools/registry.py:112` | 错误判定 = `output.startswith("[ERR:")` | adapter 错误输出必须带 `[ERR:` 前缀 |
| `tools/registry.py:104` | 工具抛异常 → `f"Error executing {name}: {e}"`，**不含 `[ERR:`** | ⚠️ 靠 Registry 兜底会**丢失错误码** → adapter 必须自己捕获 |
| `engine/loop.py:203` | `asyncio.gather` + `Semaphore(5)` **并发执行工具** | ⚠️ stdout 单通道会话需串行化 |
| `engine/loop.py:83` | `run()` 无 `finally` 清理钩子 | 连接生命周期**不能**依赖引擎 |
| `cli.py:43` | `build_engine()` 是**同步函数** | ⚠️ 注册流程必须能在同步上下文完成 |
| `cli.py:166` | 飞书模式 `engine_factory` **每次消息都 `build_engine()`** | ⚠️ 连接必须进程级共享，否则每条消息重连 |
| `cli.py:177` | `engine.registry.use(create_approval_middleware(...))` | MCP 审批策略挂在这里 |
| `feishu/approve.py:52` | `is_dangerous_command()` 兜底 `return False`（放行），且只匹配裸工具名 | ⚠️ **安全缺口**：MCP 工具默认放行 |
| `context/composer.py` | 工具清单**不走** System Prompt（走 `provider.generate(tools=...)`） | ✅ 注册进 registry 即自动可见，**composer 零改动** |
| `config.py:39` | `PROJECT_ROOT = parents[2]`，SSOT 统一配置 | `mcp.json` 默认落项目根 |

---

## 3. 三个核心矛盾

设计就是解这三个矛盾。

### 矛盾 A：生命周期 —— 同步构建 vs 异步连接，且引擎反复重建

```
build_engine()  同步、每次飞书消息都调
MCP 连接        异步（要 async with）、昂贵（拉子进程）
```

若连接挂在 `engine` 上：CLI 模式要改 `build_engine` 为 async（波及全部调用方），飞书模式则**每条消息重启一次 MCP server**。
→ **解法**：连接与引擎彻底解耦，提为**进程级单例** `MCPManager`。引擎只从「缓存好的工具清单」同步注册 adapter，不碰连接。

### 矛盾 B：并发 —— 引擎并发 vs 会话单通道

```
loop.py:203   asyncio.gather(同时执行 5 个工具)
MCP stdio     一个读写通道，请求-响应串行
```
→ **解法**：每个 server 一把 `asyncio.Lock`，同一 server 的调用串行；**不同 server 之间仍并行**（锁不跨 server）。

### 矛盾 C：安全 —— 未知工具默认放行

```python
# feishu/approve.py:74
    return False        # ← 兜底：放行
```
MCP 是**第三方能力**，可能是 shell / 数据库 / 飞书审批工具，语义上不能与「未命中危险词的 `bash`」同等对待。
→ **解法**：审批中间件新增 `mcp__` 前缀策略，**默认最保守（挂起审批）**，按 server 提供白名单旁路。

### ⚠️ 附加难点：AsyncExitStack 的 task 归属

官方 SDK 的 `stdio_client` 基于 anyio task group，**`enter` 与 `exit` 必须在同一个 asyncio task 内**，否则报 `Attempted to exit cancel scope in a different task`。
这意味着「启动时连接、任意地方调用、退出时关闭」不能随手写。
→ **解法见 §5.2**（两套生命周期方案，按运行模式选）。

---

## 4. 模块结构

```
src/tiny_claw/mcp/
├── __init__.py      # 导出 MCPManager / bootstrap_mcp
├── loader.py        # 读 mcp.json → 校验 → 返回 ServerConfig 列表
├── client.py        # MCPConnection（单 server）+ MCPManager（进程级单例）
├── adapter.py       # MCPToolAdapter(BaseTool)：命名空间 / schema / 错误码 / 锁
└── bootstrap.py     # bootstrap_mcp(registry)：把已发现的工具同步注册进 registry
```

新增后各模块职责：

| 模块 | 负责 | 不负责 |
|---|---|---|
| `loader.py` | 配置解析与校验 | 连接 |
| `client.py` | 连接、会话、生命周期、串行锁 | 工具语义 |
| `adapter.py` | MCP tool → BaseTool 翻译、错误码、渲染 | 连接管理 |
| `bootstrap.py` | 编排「预发现 → 注册」 | 引擎 |

**引擎主循环、Provider、Composer 全部不改。**

---

## 5. 架构设计

### 5.1 数据流

```
启动
 └─ await MCPManager.preload()          # 异步：连接 + list_tools + 缓存
      ├─ 读 mcp.json → 对每个 enabled server
      ├─ 建立 stdio 连接 / initialize
      └─ 缓存 discovered: list[(server, Tool)]
                │
                ▼
 └─ MCPManager.register_into(registry)  # 同步：包装 + 注册（幂等）
      └─ 每个 Tool → MCPToolAdapter → registry.register()
                │
                ▼
 运行期
 └─ engine 正常 get_available_tools() → 模型看到 mcp__* 工具（零改动）
      └─ registry.execute(call) → adapter.execute()
           ├─ async with self._server_lock        # 矛盾 B
           ├─ await session.call_tool(...)        # 带 timeout
           └─ content blocks → 文本 或 [ERR:CODE]  # 矛盾 C / 错误码
```

### 5.2 生命周期（⚠️ 重点）

`MCPManager` 是**进程级单例**，两种运行模式各有一套挂载方式：

**CLI 模式**（`run_cli` 已是 async，且全程同一 task）——直接同 task 生命周期：

```python
# cli.py run_cli() 内，engine.run() 之前/之后
async def run_cli(...):
    engine = build_engine(...)
    async with MCPManager.instance().lifespan():     # enter / exit 同一 task ✅
        await bootstrap_mcp(engine.registry)
        await engine.run(session)
```

`lifespan()` 内部就是 `AsyncExitStack`：进入时 `preload()`，退出时关闭全部连接 + 回收子进程。

**飞书模式**（`bot.start()` 是同步阻塞，且 `engine_factory` 每次新建引擎）——用**专属 manager task**：

```python
# MCPManager 内部：在一个后台 task 里持有连接，直到 stop_event
async def _serve(self):
    async with AsyncExitStack() as stack:
        await self._connect_all(stack)
        self._ready.set()
        await self._stop_event.wait()      # 挂住，enter/exit 都在本 task ✅

# 启动（飞书进程内，一次性）
asyncio.run_coroutine_threadsafe(self._serve(), loop)   # 或由 bot 的 loop 启动

# engine_factory 内（同步！）——只做注册，不碰连接
def engine_factory(session):
    engine = build_engine(...)
    MCPManager.instance().register_into(engine.registry)   # 纯同步，从缓存注册
    return engine
```

这就是**矛盾 A 的解法**：`preload()` 只跑一次，`register_into()` 可以跑 N 次且零成本。

> **实施建议**：Phase 1–3 **先只支持 CLI 模式**（生命周期简单、可验证）。飞书模式的 manager task 作为 Phase 4。不要一上来两套都做，会同时被两个问题困住。

### 5.3 适配层（adapter.py 示意）

```python
class MCPToolAdapter(BaseTool):
    """把一个 MCP tool 暴露成 tiny-claw 的 BaseTool"""

    def __init__(self, server: str, tool: "MCPTool", conn: "MCPConnection"):
        self._server, self._raw_name = server, tool.name
        self._tool, self._conn = tool, conn

    def name(self) -> str:
        return f"mcp__{self._server}__{self._raw_name}"      # 决策 1：命名空间

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name(),
            description=self._tool.description or "",
            input_schema=self._tool.inputSchema or {"type": "object", "properties": {}},
        )                                                    # 决策 2：schema 直通

    async def execute(self, arguments: dict) -> str:
        try:
            async with asyncio.timeout(config.MCP_CALL_TIMEOUT):
                async with self._conn.lock:                  # 决策 4：per-server 串行
                    result = await self._conn.session.call_tool(
                        self._raw_name, arguments
                    )
        except TimeoutError:
            return format_error(ErrorCode.MCP_TIMEOUT, f"{self._server}/{self._raw_name} 调用超时")
        except Exception as e:
            return format_error(ErrorCode.MCP_TOOL_FAILED, f"{self._server}: {e}")

        if getattr(result, "isError", False):
            return format_error(ErrorCode.MCP_TOOL_ERROR, _render(result))
        return _clip(_render(result))                        # 决策 8：体积控制
```

`_render()` 负责 content blocks（`text` / `image` / `resource`）→ 单一字符串；`_clip()` 按 `MCP_MAX_OUTPUT_CHARS` 截断。

---

## 6. 关键设计决策（面试讲这些）

| # | 决策 | 不这么做会怎样 |
|---|---|---|
| 1 | **命名空间** `mcp__{server}__{tool}` | `registry.py:59` 重名只 warning 后**静默覆盖**，内置工具凭空消失 |
| 2 | **schema 直接透传**（不做字段转换） | `ToolDefinition.input_schema` 与 MCP `inputSchema` 同为 JSON Schema，转换纯属自找 bug |
| 3 | **连接进程级共享**（不在引擎上） | 飞书模式每条消息重连；CLI 被迫把 `build_engine` 改 async |
| 4 | **per-server 串行锁** | 引擎并发调同一 stdio 会话 → 请求-响应错配，结果张冠李戴 |
| 5 | **异步预发现 + 同步注册**两段式 | 迁就同步的 `build_engine`，又不阻塞主流程 |
| 6 | **错误自带 `[ERR:` 前缀** | 靠 `registry.py:104` 兜底 → 错误串不带码 → `RecoveryManager` 不注入救援提示，自愈失效 |
| 7 | **审批默认保守**（`mcp__` 前缀挂起） | `is_dangerous_command` 兜底放行 → 第三方工具裸奔；server 若暴露 `bash` 工具，因前缀反而绕过检测 |
| 8 | **输出体积上限 + 渲染** | MCP 可返回巨量文本/图片块，直接进上下文会撑爆预算 |
| 9 | **配置沿用社区 `mcpServers` 格式** | 用户可复用 Claude Desktop / Cursor 现成配置，兼容性即卖点 |
| 10 | **子智能体默认不挂 MCP** | `read_only_registry` 已是「意图层约束」（README:170 自认），再挂第三方工具会让约束更虚 |

---

## 7. 配置设计

### 7.1 `mcp.json`（项目根）

沿用社区 `mcpServers` schema，追加 `tiny-claw` 扩展字段（未知字段对社区工具无害）：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/workspace"],
      "enabled": true,
      "approval": "always"
    }
  }
}
```

| 扩展字段 | 取值 | 含义 |
|---|---|---|
| `enabled` | bool，默认 `true` | 是否连接 |
| `approval` | `always` \| `never` \| `dangerous`，默认 `always` | 该 server 工具的审批策略 |
| `timeout` | int 秒 | 覆盖全局调用超时 |

### 7.2 `config.py` 新增（延续 SSOT）

```python
# ── MCP ──
MCP_ENABLED          = get_bool("TINY_CLAW_MCP_ENABLED", True)
MCP_CONFIG_PATH      = get_str("TINY_CLAW_MCP_CONFIG", "mcp.json")
MCP_CONNECT_TIMEOUT  = get_int("TINY_CLAW_MCP_CONNECT_TIMEOUT", 30)
MCP_CALL_TIMEOUT     = get_int("TINY_CLAW_MCP_CALL_TIMEOUT", 60)
MCP_MAX_OUTPUT_CHARS = get_int("TINY_CLAW_MCP_MAX_OUTPUT_CHARS", 8000)
```

### 7.3 `context/recovery.py` 新增

```python
# ---- MCP ----
MCP_SERVER_UNAVAILABLE = "MCP_SERVER_UNAVAILABLE"
MCP_TOOL_FAILED        = "MCP_TOOL_FAILED"
MCP_TOOL_ERROR         = "MCP_TOOL_ERROR"     # server 返回 isError=True
MCP_TIMEOUT            = "MCP_TIMEOUT"
```

并补 `_RECOVERY_HINTS`，例如：

> `MCP_SERVER_UNAVAILABLE` → 「该 MCP Server 当前不可用（进程未启动或已退出）。请改用内置工具完成当前步骤，不要反复重试同一 MCP 工具。」

### 7.4 审批策略（`feishu/approve.py` 修改）

`is_dangerous_command()` 顶部加一段 MCP 分支——**先于**原有裸工具名匹配：

```python
if tool_name.startswith("mcp__"):
    server = tool_name.split("__", 2)[1]
    policy = config.mcp_approval_for(server)     # always / never / dangerous
    if policy == "never":
        return False
    if policy == "always":
        return True
    # dangerous：退回到关键字匹配（沿用 _DANGEROUS_BASH_PATTERNS 扫参数）
    return any(p.search(args) for p in _DANGEROUS_BASH_PATTERNS)
```

---

## 8. 实施步骤（每步独立可验证）

**进度（2026-09-11）**

| Phase | 状态 | 产出 |
|---|---|---|
| 0 · 环境打通 | ✅ 完成 | `tools/probe_mcp.py`；结论见 §12 |
| 1 · 连接层 | ✅ 完成 | `src/tiny_claw/mcp/{loader,client}.py`；`tests/test_mcp.py` 21 用例；真实 server 验收见 §12.7 |
| 2 · 注册与调用 | ⬜ 待做 | `adapter.py` / `bootstrap.py` / `cli.py` 接线 |
| 3 · 接入既有体系 | ⬜ 待做 | 4 个 ErrorCode + 审批 `mcp__` 策略 + 超时/截断 |
| 4 · 飞书 + 演示 | ⬜ 待做（**建议裁剪**：manager task 收益讲不清，见 §5.2 实施建议） | |


### Phase 0 · 环境打通（约 30 分钟）
1. `uv add mcp`
2. 写一次性脚本：连 `@modelcontextprotocol/server-filesystem`，`initialize()` → `list_tools()` → 打印工具名与 `inputSchema`
3. **验证点**：能看到工具列表，且 schema 打印出来是标准 JSON Schema

### Phase 1 · 连接层（半天）
4. `loader.py`：解析 `mcp.json`，坏配置只 warning 不崩启动
5. `client.py`：`MCPConnection`（连接 + `initialize` + 锁）+ `MCPManager`（单例 + `preload`）
6. **验证点**：单测里 `preload()` 后能拿到 `discovered` 列表

### Phase 2 · 注册与调用（半天）
7. `adapter.py`：命名空间 + schema 透传 + 错误码 + 锁
8. `bootstrap.py` + `cli.py` 接线（`async with MCPManager...lifespan()`）
9. **验证点**：
   ```bash
   python main.py -p "用 MCP 的 filesystem 工具列出工作区文件"
   ```
   模型能选中 `mcp__filesystem__list_directory` 并拿到结果

### Phase 3 · 接入既有体系（半天）
10. 新增 4 个 `ErrorCode` + 救援提示
11. 审批中间件加 `mcp__` 分支
12. 超时 + 输出截断
13. **验证点**：故意 kill 掉 server 进程，确认返回 `[ERR:MCP_...]` 且模型收到救援提示、不再硬刚

### Phase 4 · 飞书模式 + 测试 + 演示（1 天）
14. 飞书：manager task 方案（§5.2 第二套）
15. 单测：schema 映射、命名空间隔离、错误码渲染、超时、**并发串行化**
16. 端到端：CLI 跑真实任务并**录屏**
17. README 补 MCP 章节

---

## 9. 验证方式（必须可复现）

| 层级 | 方式 |
|---|---|
| 单元 | `pytest tests/test_mcp.py`——**fake session** 测适配层，不发真实请求 |
| 集成 | 真起 stdio server（filesystem），测 `list` + `call` |
| 并发 | 单测里并发触发同 server 两个工具，断言实际串行（用计数/时序断言） |
| 回归 | **现有 110 个用例必须全绿**（证明未破坏既有工具链） |
| 端到端 | `python main.py -p "<依赖 MCP 工具的任务>"`，录屏存仓库 |

---

## 10. 风险与边界（诚实记录）

1. **AsyncExitStack 的 task 归属**：跨 task 关闭会异常。CLI 用同 task lifespan；飞书用专属 manager task。**这是最容易踩的坑。**
2. **stdio server 是子进程**：异常退出会留孤儿进程。需在 manager 里记录 PID，`atexit` / signal 兜底回收；自动重连**本期不做**。
3. **`npx` 首次启动慢**（要下载包）：`MCP_CONNECT_TIMEOUT` 默认给 30s，且启动阶段只 warning 不阻塞。
4. **命名空间让工具名变长**（`mcp__filesystem__list_directory`），可能影响模型选中准确率——需实测，必要时缩短前缀或加缩写映射。
5. **审批「全挂起」会很吵**：实际使用需要按 server 开白名单（`approval: never`）。
6. **只做 Tools**：MCP 的 Resources / Prompts / Sampling 本期不涉及，面试要说清这是**有意裁剪**，不是不知道。

---

## 11. 做完之后，简历上能写什么

> **为 Agent 运行时新增 MCP（Model Context Protocol）客户端能力**
> - 实现基于 stdio 的 MCP Server 连接与会话生命周期管理（`AsyncExitStack` + 进程级单例，与引擎解耦）
> - 实现工具自动发现与适配层：MCP `inputSchema` → 内部 `ToolDefinition`，即插即用注册
> - 设计多 Server 命名空间隔离，规避注册表重名**静默覆盖**风险
> - 解决「引擎并发调度」与「stdio 单通道会话」的冲突，实现 per-server 串行化 + 跨 server 并行
> - 将 MCP 调用错误接入既有 `[ERR:CODE]` 自愈体系，并为第三方工具补齐默认保守的审批策略
> - 使 Agent 无需改代码即可接入标准 MCP Server 生态

**口径红线**：每条都要能在代码里指出来。**不要写「设计并实现了 MCP 协议」**——实现的是**客户端接入**，协议是官方 SDK 的。

---

## 12. Phase 0 实测结论（2026-09-11，已执行）

探针脚本：`tools/probe_mcp.py`（新起 server → initialize → list_tools → schema 直通验证）。

```
✅ [1/3] initialize 成功      冷启动 48.8s（含 npx 首次下载）/ 热启动 4.7s
✅ [2/3] list_tools 成功      14 个工具，1 页，0.03s
✅ [3/3] schema 直通验证      ToolDefinition 构造成功，schema.type='object'
   server = secure-filesystem-server 0.2.0（@modelcontextprotocol/server-filesystem）
   环境：node 22.22.2 / npx 10.9.7（WorkBuddy 托管，需显式补 PATH）
   SDK：mcp 2.2.0
```

### 12.1 🔴 阻塞级：SDK 字段名与协议名不一致（本 plan §5.3 会直接崩）

MCP **线协议**字段是 `inputSchema`，但 Python SDK v2 的模型属性是 **`input_schema`**
（`inputSchema` 只是 alias）。实测报错：

```
AttributeError: 'Tool' object has no attribute 'inputSchema'
```

→ §5.3 的 `self._tool.inputSchema` 必须改成 `input_schema`。
建议 adapter 里写成兼容取法（两个都试），SDK 再改名时不至于整条链断。

### 12.2 🟠 遗漏：`list_tools` 是分页接口

`ListToolsResult` 带 **`next_cursor`**，只取第一页会**静默漏掉工具**。
本次 filesystem server 只有 14 个工具（1 页），所以不测就发现不了。
→ `preload()` 必须循环收到 `next_cursor` 为空。

### 12.3 ✅ 实证：命名空间不是"防患于未然"，是**必须做**

该 server 暴露的 14 个工具里，**`read_file` / `write_file` / `edit_file` 与本项目内置工具完全同名**。
而 `registry.register()` 遇重名是 warning 后**静默覆盖** →
不做 `mcp__{server}__{tool}` 命名空间，**内置工具会凭空消失**。§6 决策 1 从"理论风险"升级为"实测撞上"。

### 12.4 ✅ 实证：`mcp__` 前缀确实会**绕过**现有审批

`is_dangerous_command()` 是按**裸工具名**匹配的（`tool_name in ("write_file","edit_file")`）。
MCP 工具名变成 `mcp__filesystem__write_file` 后不再匹配任何规则，落到兜底 `return False` →
**一个能写文件、能移动文件的第三方工具默认放行**。§6 决策 7 同样得到实证。

### 12.5 补充：`content` block 不只是文本

`read_media_file` 会返回 **base64 编码的 content block**（图片/音频）。
`_render()` 不仅要拼接多块，还必须处理非 text 块；base64 体积极大，
§6 决策 8 的 `_clip()` 要有明确上限（建议复用 `MCP_MAX_OUTPUT_CHARS`）。

### 12.6 Phase 1 真实 server 验收（`MCPManager.lifespan()` 全链路）

```
配置: filesystem (npx -y @modelcontextprotocol/server-filesystem ./workspace)
preload 完成  13.6s
连接: ['filesystem']
发现 14 个工具 → mcp__filesystem__read_file / read_text_file / read_media_file / …
✅ 命名空间隔离生效：内置 read_file 未被顶掉
✅ 生命周期清理正常（同 task 内 enter/exit，无 cancel scope 跨 task 报错）
```

两个坑已「钉进代码」而不是只写在文档里：

| 坑 | 落点 |
|---|---|
| `input_schema` 字段名 | `client.tool_input_schema()`（兼容两种命名）—— **保留** |
| `list_tools` 分页 | 改用官方 `group.tools`（已聚合；原自写 `list_all_tools` 见 §12.9 已删） |
| 命名空间防覆盖 | 改用官方 `component_name_hook`（`client._name_hook`），格式仍是 `mcp__{server}__{tool}` |

新增配置（`config.py` + `.env.example` 同步）：
`MCP_ENABLED` / `MCP_CONFIG_PATH` / `MCP_CONNECT_TIMEOUT` / **`MCP_EXTRA_PATH`**（后者是实测必需项：
node/npx 不在默认 PATH 时，连接失败只报 `No such file or directory`）。

依赖登记：`mcp>=2.0` 先进 `[project.optional-dependencies].mcp`，避免 uvicorn/starlette
这类 SDK 传递依赖混进核心依赖；Phase 2 落地后可提升。

### 12.8 🔴 规范代际差异：MCP 2026-07-28 已「无状态化」，客户端必须两条路都走

**外部事实**（查证于 2026-09-11）：MCP 在 **2026-07-28** 发布了自诞生以来最大的改版 ——
**协议层去掉了会话**：

| 旧（≤ 2025-11-25） | 新（2026-07-28） |
|---|---|
| `initialize` / `initialized` 握手 | **移除**；改用可选 `server/discover` |
| `Mcp-Session-Id` 会话头 | **移除**；每个请求自带 `_meta`（版本/客户端身份/能力） |
| 服务端主动请求（elicitation / sampling / roots）靠长连接 | **MRTR**：返回 `input_required`，客户端带答案重试 |
| 列表结果不可缓存 | `ttlMs` / `cacheScope`（对齐 HTTP Cache-Control） |
| 需粘性路由 + 共享会话存储 | 任何实例都能处理任意请求（普通轮询负载均衡即可） |

**本地实测的三条硬事实**：

```
SDK mcp 2.2.0 的 LATEST_PROTOCOL_VERSION = 2026-07-28   ← 已是新规范
discover()   → MCPError: Method not found               ← server 0.2.0 还是旧规范
initialize() → ✅ 协商到 2025-11-25                      ← 唯一走得通的路
list_tools() → 14 个工具，ttl_ms=0 / cache_scope=private（新字段已在 SDK 中）
```

**结论：客户端必须「先 discover、失败回退 initialize」**，两条路都留。
SDK 文档明确写了这一点 —— *「Any other error … propagates; the legacy `initialize()`
fallback is the caller's policy.」* 只走 initialize 就永远用不上新规范；
只走 discover 就完全连不上当前生态里的老 server。

落点：`client.negotiate_session()`（§12.6 之后新增，含 2 个单测：
新规范走 discover、旧 server 回退）。

⚠️ **对原 plan 的影响**：§5.2 的生命周期设计（AsyncExitStack / 专属 manager task）
是**基于旧规范的会话语义**推出的。若上游 server 普遍迁移到 2026-07-28，
「同 task 内 enter/exit」这条约束会随会话一起消失 —— 但对**当前生态**仍必须保留，
所以本期不改。这一点面试要说清：**我实现的是「跨代兼容的客户端」**，
不是「按最新规范重写的客户端」。

### 12.9 ⚠️ 自我盘点：官方 SDK 已有 `ClientSessionGroup`，我的 `MCPManager` 有重复劳动（**已重构**）

**问题的由来**：有人问「现在有现成的 Python 包，为什么要自己实现？」核对后发现
——**协议确实用的是官方 SDK**（`mcp` 2.2.0 负责 JSON-RPC 编解码、stdio 传输、握手/发现、
`list_tools`/`call_tool`），但**连接管理这一层我重复实现了 SDK 已提供的东西**。

**官方 `ClientSessionGroup` 实测能力**（`mcp.client.session_group`，真机跑过）：

| 能力 | 官方 group | 我的 `MCPManager` |
|---|---|---|
| 多 server 连接生命周期 | ✅ async context manager | 手写 AsyncExitStack |
| 工具聚合 | ✅ `group.tools` → `dict[命名空间名, Tool]` | 手写 `discovered` 列表 |
| **命名空间** | ✅ `component_name_hook=fn(name, server_info)` | 手写 `namespaced_name()` |
| **按命名空间路由调用** | ✅ `group.call_tool(全名, args)`（实测调通） | 未实现（Phase 2 计划里） |
| 超时 / 进度 / **MRTR**（`input_responses`） | ✅ 内建参数 | 未实现 |
| 旧 server 容错 | ✅ prompts/resources 缺失只 warning | 未涉及（我只做 tools） |

**结论（已执行，2026-09-11）**：「连接管理 + 工具聚合 + 命名空间」三块**已改用 `ClientSessionGroup`**。

| | 重构前 | 重构后 |
|---|---|---|
| `client.py` | 296 行（自写 AsyncExitStack / 聚合 / 命名空间 / 分页） | **218 行**（薄封装） |
| `mcp/` 合计 | 470 行 | **374 行** |
| 单测 | 23（含分页与握手策略） | **22**（去掉测内部实现的，改为测接缝） |
| 白得的能力 | — | `read_timeout_seconds` + `progress_callback` + **MRTR**（`input_responses`） |

**被取代的实现**（已删，勿再写回）：
- 自写 `AsyncExitStack` 会话管理 → `ClientSessionGroup(exit_stack=...)`
- 自写工具聚合 + `list_all_tools()` 分页收集 → 官方 `group.tools`（已聚合）
- 自写 `negotiate_session()`（discover→initialize 双路径）→ **官方 group 内部处理**：
  实测对旧规范 server 自动降级，且容忍 `prompts`/`resources` 缺失（只 warning）
- 自写 per-server 串行锁 → 官方 group 内置（`_tool_to_session` 路由）

⚠️ **命名空间细节**：官方 hook 只传 `(tool_name, server_info)`，**拿不到我们的配置 key**，
所以命名用的是 server 自报名 → `mcp__secure-filesystem-server__read_file`
（比用配置 key 长，但更准确、不依赖用户怎么命名）。

**重构后真实链路验收**：
```
INFO [MCP] 配置加载完成：1 个 server（其中 1 个启用）
WARNING Could not fetch prompts/resources: Method not found   ← 旧规范 server，官方已容错
INFO [MCP] server 'filesystem' 已接入
INFO [MCP] 就绪：1 个 server / 14 个工具
✅ 真实调用 mcp__secure-filesystem-server__list_directory → [DIR] .claw | [FILE] AGENTS.md | …
退出后 group: None | discovered: 0
```

**必须自己写的部分**（SDK 不可能知道本项目的约定）：

1. `loader.py` —— 配置从哪来、坏配置如何降级（SDK 只接受参数字典/对象）
2. **adapter** —— MCP `Tool` → 本项目的 `BaseTool` / `ToolDefinition`
3. **错误映射** —— MCP 的 `isError` → `[ERR:MCP_*]`，接进 `RecoveryManager` 自愈体系
4. **审批策略** —— `mcp__` 前缀走 `is_dangerous_command`（§12.4 的实证缺口）
5. **接缝** —— 进程级单例 + 同步 `register_into()`：因为 `build_engine()` 是同步的，
   且飞书模式每条消息都新建引擎（这正是 §3 矛盾 A 的根因）

**甄别标准（值得写进面试话术）**：能不能被替换，取决于**替换后是否丢失本项目已有的契约**
——错误码体系、审批回路、`BaseTool` 抽象、同步构建的接缝。丢契约的就是「不该外包」的；
只是重写一遍 SDK 已有机制的，就是「不该自己写」的。

⚠️ **教训**：原 plan 的模块划分（loader/client/adapter/bootstrap）是在**没盘点 SDK 现有能力**的
前提下定的，于是默认「连接管理要自己写」。正确顺序是：**先列出 SDK 提供了什么 → 再划自己该写的边界**。
另外命名空间有个细节：官方 hook 给的是 **server 自报名**（`secure-filesystem-server`），
而我用的是**配置里的 key**（`filesystem`）——前者更准（用户 key 可随意写），
但名字更长，重构时要做个明确取舍。

### 12.7 SDK v2 新增、本 plan 未涉及（Phase 2 可顺手利用）

`Tool.output_schema`（结构化输出）、`execution`（执行时长/重试元数据）、
`annotations`（危险提示等）以及 `ListToolsResult.ttl_ms` / `cache_scope`（工具列表缓存语义）。
本期不做，但**面试被问到"你还知道 MCP 的哪些能力"时可以说**。
