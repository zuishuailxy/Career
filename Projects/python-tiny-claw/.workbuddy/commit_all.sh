#!/usr/bin/env bash
# 一次性补齐所有待提交的改动，按语义拆成 12 个提交。
#
# 为什么需要脚本：git 仓库根在 ~/Project/github/Career（本项目目录之外），
# AI 的运行沙箱不允许写 .git，所以提交要在你自己的终端跑。
#
# 用法：cd 到项目根后执行
#     bash .workbuddy/commit_all.sh
#
# 说明：
# - RESUME.md 与根目录的 4 张图**不在提交范围内**（前者含面试准备稿，后者用途未定）；
#   要入库就把它们加进最后一条 `git add`。
# - pyproject.toml 同时含「依赖表清理 / entry point / MCP extra」三类改动，
#   按文件拆不开，统一归到第 7 条并在信息里注明。
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(git rev-parse --show-toplevel)"
rm -f "$REPO_ROOT/.git/index.lock"

# ── 1. 压缩五档 + System Reminders ──
git add src/tiny_claw/context/compactor.py \
        src/tiny_claw/context/reminders.py \
        src/tiny_claw/engine/reminder.py
git commit -q -m "feat(context): 压缩按信息价值五档渐进淘汰，并新增 System Reminders 总线" -m "排序改为价值而非时间：远期成功工具输出先掩码（可用行号重取）、近期工具输出掐头去尾、推理折叠、失败记录仅兜底截断（错误码在头、救援提示在尾）、System/用户指令永不淘汰；淘汰渐进式进行，一降到阈值即停手。新增 ReminderBus 把运行时状态回灌给模型（上下文压力 / 轮数预警），带冷却、限流、不写 Session 三约束，注入点固定在压缩之前。修掉静默 bug：提醒走 user 通道且无 tool_call_id，原被判为「用户原始指令」永不淘汰，形成越满越打断的正反馈；现按 is_system_reminder 单独分档。"

# ── 2. 引擎循环参数化 + 提醒接线 ──
git add src/tiny_claw/engine/loop.py
git commit -q -m "feat(engine): 双阶段推理循环参数化，接通提醒总线与子智能体隔离" -m "循环参数全部改读 config；max_turns 支持按调用方收紧（此前 TestCase.max_turns 定义却从未生效，属死代码）。每轮在工作记忆之后、压缩之前注入运行时提醒。子智能体沿用独立循环：只读注册表、独立信号量与失败计数器、独立 prompt、10 轮上限。"

# ── 3. 价格表修正 ──
git add src/tiny_claw/tracing.py
git commit -q -m "fix(tracing): 价格表按官方定价修正，成本不再静默归零" -m "deepseek-v4-pro 原写 1.0/4.0，实际闲时未命中 4.5/13.5；补录 deepseek-v4-flash（原不在表内导致成本恒为 0 且无告警）。未知模型改为打 WARNING 并支持环境变量覆盖单价，未收录官方价格不编造数字。"

# ── 4. 助手消息回填 reasoning_content ──
git add src/tiny_claw/provider/openai.py
git commit -q -m "feat(provider): 翻译助手消息时回填 reasoning_content" -m "推理模型的思维链在多轮里需要原样带回，否则部分端点会报错或丢失上下文。配合 schema 的 reasoning 归一化字段，引擎侧仍不感知厂商。"

# ── 5. 评测插桩 + 离线重放 ──
git add src/tiny_claw/eval/ run_benchmark.py tools/replay_thresholds.py
git commit -q -m "feat(eval): 一次录制离线重放，调参零 API 成本 + 预算硬止损" -m "三件插桩代理（Tracker/Compactor/Registry）在单次跑分中录下本地估算 vs 真实计费 token、工具输出体积分布、压缩前上下文快照；tools/replay_thresholds.py 用最小二乘校准 + 网格搜索在本地重放任意阈值组合。跑分新增金额 + token 双轨预算止损。判卷脚本修掉跨平台坑：BSD grep 不支持交替符，曾把正确产出判成假阴性。"

# ── 6. 既有单测 ──
git add tests/conftest.py tests/test_config.py tests/test_context.py \
        tests/test_provider_parity.py tests/test_read_file.py \
        tests/test_reminders.py tests/test_tool_concurrency.py
git commit -q -m "test: 补 111 个用例（协议对照 / 上下文治理 / 长文件 / 提醒 / 配置口径）" -m "覆盖双协议翻译对照、Compactor 五档与孤儿清理、read_file 中文截断与卸载后读回、ReminderBus 触发与冷却、config 常量与工具口径、并发结果回填保序。夹具含真实 140KB 日志与卸载后读回用例（证明不制造死循环）。"

# ── 7. 入口与依赖（pyproject 混了三类改动，在此统一交代）──
git add main.py src/tiny_claw/cli.py pyproject.toml run.sh .gitignore
git commit -q -m "feat(cli): 入口移入包内 + 修正 entry point + 依赖表校正" -m "入口从仓库根移入 src/tiny_claw/cli.py，根目录保留 24 行兼容壳（未安装时自挂 sys.path），使 python main.py 与 tiny-claw 两种用法都成立；entry point 原指向不存在的 tiny_claw.main。依赖表 13 → 5：删掉 fastapi / uvicorn / langgraph / langchain×3 / httpx / pydantic（全仓库 0 处 import，属课程脚手架遗留）。pyproject 同时新增 mcp extra（实现见下一条提交）与构建产物忽略规则。"

# ── 8. 门面文档 ──
git add README.md CONTRIBUTING.md AGENTS.md
git commit -q -m "docs: 补齐 README / CONTRIBUTING，改写 AGENTS.md" -m "README 缺文件会让 readme = \"README.md\" 直接构建失败，现补齐定位/架构图/快速开始/配置/测试/评测/目录结构/已知边界。AGENTS.md 原为别的项目模板残留（写着「所有 API 必须返回 JSON」但项目无 HTTP 路由），按受众拆两份：AGENTS.md 会被 composer 读进 System Prompt（每轮常驻，压到 1013 token），工程流程移入不注入的 CONTRIBUTING.md。"

# ── 9. MCP 客户端 ──
git add src/tiny_claw/mcp/ src/tiny_claw/config.py .env.example \
        mcp.json.example tests/test_mcp.py
git commit -q -m "feat(mcp): MCP 客户端接入（配置加载 + 基于官方 ClientSessionGroup 的连接与发现）" -m "只做 Client 侧：连接标准 MCP server、发现工具，为 Phase 2 的 BaseTool 适配预留接缝。协议与连接管理交给官方 mcp SDK 的 ClientSessionGroup（多 server 生命周期、工具聚合、命名空间 hook、按命名空间路由调用、超时/MRTR 都是它提供的），本项目只保留 SDK 不可能知道的部分：配置来源与坏配置降级（外部依赖不可靠是常态）、进程级单例 + 同步注册接缝（适配「build_engine 同步 + 飞书每条消息新建引擎」）、以及 tool_input_schema 字段名兼容（SDK v2 属性是 input_schema，协议名 inputSchema 只是 alias，照协议名写会 AttributeError）。新增 MCP_ENABLED / CONFIG_PATH / CONNECT_TIMEOUT / CALL_TIMEOUT / EXTRA_PATH 常量；EXTRA_PATH 是实测必需项（node/npx 不在默认 PATH 时连接失败只报 No such file or directory）。"

# ── 10. Phase 0 探针 ──
git add tools/probe_mcp.py
git commit -q -m "chore(mcp): 新增 Phase 0 连接探针" -m "在写适配层之前先验证地基：起真实 stdio server → initialize → list_tools（含分页）→ 用真实 schema 构造 ToolDefinition 验证可直接透传。这一步在写代码前抓出 4 个设计缺陷（SDK 字段名、list_tools 分页、命名空间必要性、mcp__ 前缀绕过审批），结论见 docs/MCP_INTEGRATION_PLAN.md §12。探针会递归展开 ExceptionGroup，否则 anyio 只报「unhandled errors in a TaskGroup」，挖不到叶子异常。"

# ── 11. MCP 设计文档 ──
git add docs/MCP_INTEGRATION_PLAN.md
git commit -q -m "docs(mcp): MCP 集成设计与 Phase 0/1 实测结论" -m "含逐行核验的现状约束、三个核心矛盾（生命周期 / 并发 / 安全）、关键设计决策与风险边界；§12 记录 Phase 0 探针的实测发现，§12.9 记录自查后按官方能力盘点做的重构（删掉自写的连接管理、聚合、命名空间，client.py 296 → 218 行）与甄别标准。"

# ── 12. 工作记忆 ──
git add .workbuddy/memory/
git commit -q -m "chore(memory): 记录配置层、压缩、提醒、评测、MCP 接入与门面修复的工作日志"

echo
echo "=== 完成，最近 14 条 ==="
git log --oneline -14
echo
echo "=== 仍未跟踪（有意排除）==="
git status --short
