# AGENTS.md — 工作区说明

**tiny-claw**：自主编码 Agent 运行时的 Python 实现，复刻 Go 版架构
（各模块 docstring 标注对应的 `internal/xxx.go`）。

> ⚠️ 这个文件会被 `context/composer.py` 读进 **System Prompt**（`work_dir/AGENTS.md`），
> 每一轮都在，且属于永不淘汰的 System 档。**所以它必须短**：只写干活真需要的。
> 工程流程（测试 / 提交 / 打包 / 删文件）在 `CONTRIBUTING.md`，不要往这里搬。

## 目录结构

| 模块 | 职责 |
|---|---|
| `src/tiny_claw/context/` | 提示词组装、压缩、token 计量、错误自愈、提醒总线 |
| `src/tiny_claw/engine/` | 双阶段推理循环、会话、死循环打断、Reporter |
| `src/tiny_claw/tools/` | Registry 路由 + 中间件链、内置工具、子智能体 |
| `src/tiny_claw/provider/` | 双协议（OpenAI / Anthropic）双向翻译 |
| `src/tiny_claw/feishu/` | 长连接 + 人工审批回路 |
| `src/tiny_claw/cli.py` | 入口（CLI / 飞书模式） |

## 红线

1. **配置只有一处来源**：常量与凭据都从 `config.py` 取，不要硬编码，不要直接 `os.getenv`。
2. **工具失败用返回值，不抛异常**：错误以 `[ERR:CODE]` 前缀返回；新增错误码要补救援提示。
3. **压缩不改写历史**：`compact()` 返回副本；引擎注入的运行时消息必须打
   `is_system_reminder=True`，否则会被判成「用户原始指令」而永不淘汰。
4. **单位不要混**：阈值判定用 token，给人 / 给模型看的提示语写字符数。
5. **不要删除**：`.workbuddy/`（工作记忆）、`workspace/`（演示工作区）。
   删任何文件前先确认它不是夹具 / 记忆 / 单一事实源。
6. **`Message.reasoning` 厂商中立**：代码里不出现 `reasoning_content` / `thinking` 这类私有字段名。

## 动手时的约定

- 日志：中文 + `[ClassName]` 前缀 + key=value；不用 `print` 做日志。
- 注释写「为什么」（取舍、踩过的坑、边界），不复述代码。
- 新工具：实现 `BaseTool` 并注册进 Registry；子智能体能力改在
  `src/tiny_claw/cli.py` 的 `read_only_registry`（不是主注册表）。
- 新可调参数：`config.py` + `.env.example` 双写（注释写清取值理由）。

## 已知边界（别当成 bug 去"修"）

- 慢思考缺 A/B 实测数据；错误自愈没有量化收益数据。
- 子智能体的「只读」是**意图层不是强制层**（bash 仍可写，且没挂审批中间件）。
- Provider 层错误（429 / 超时）尚未纳入错误码体系。
- 只对 `read_file` 做了输出卸载，bash 的大输出未处理。
