# CONTRIBUTING.md — 工程流程与纪律

本文件是**给工程师和 AI 协作者**的流程说明。它**不会被注入 System Prompt**
（运行时只读 `AGENTS.md`），所以这里可以写长。

---

## 环境

```bash
uv venv .venv                    # 本项目用 uv 管理环境
source .venv/bin/activate
uv pip install -e ".[dev]"       # 注意：uv 建的 venv 里没有 pip，别用 pip install
```

- 密钥写在项目根 `.env`（**不入库**，仓库里只有 `.env.example`）。
- 所有常量与凭据的唯一来源是 `src/tiny_claw/config.py`；新增可调参数要同时补
  `.env.example` 注释，写清**取值理由**而不只是当前值。
- 单测需要隔离真实 `.env`：设 `TINY_CLAW_DISABLE_DOTENV=1`（`tests/conftest.py` 已设）。

## 测试

```bash
pytest -q          # 当前基线：110 passed
```

**三条硬纪律：**

1. **必须后台跑**。前台执行会因导入 langsmith 超时被 SIGTERM（exit 137），
   不是代码问题。
2. `pyproject.toml` 里已用 `--basetemp=/tmp/tiny-claw-pytest` 固定临时目录——
   系统默认位置曾残留他人身份创建的 `pytest-of-*` 目录，一次挂掉 19 个用例。
3. 改哪块跑哪块，别只看总数：

| 改动范围 | 必跑 |
|---|---|
| 压缩 / 提醒 / token 计量 | `tests/test_context.py`、`tests/test_reminders.py` |
| `read_file` / 长文件 | `tests/test_read_file.py` |
| Provider / 协议翻译 | `tests/test_provider_parity.py` |
| 配置与常量 | `tests/test_config.py` |

## 编辑纪律

- **改完 `pyproject.toml` / 任何 JSON 后立刻用解析器验一次**：

  ```bash
  python -c "import tomllib,pathlib;tomllib.loads(pathlib.Path('pyproject.toml').read_text())"
  ```

  真实事故：一个不可见的 `U+00B7`（`·`）混进依赖数组（`"langsmith>=0.3",·`），
  导致 pytest 报 `Invalid value (at line 15, column 22)`，
  **110 个用例一个都收集不到**——排查成本远高于验证成本。

- 注释写「为什么」：设计取舍、踩过的坑、边界条件。不复述代码。
- 日志：中文 + `[ClassName]` 前缀 + key=value，级别用 INFO/WARN/ERROR。
- **不要用 `print` 做日志**（CLI 面向用户的交互输出除外）。

## 提交

- **按语义拆分**，不要一次大提交——出问题时要能单独 revert：

  | 前缀 | 内容 |
  |---|---|
  | `feat(模块)` | 新能力 |
  | `fix(模块)` | 修 bug（提交信息里写清现象与根因） |
  | `test` | 用例 |
  | `docs` | 文档 |
  | `chore` / `chore(memory)` | 工程配置 / 工作记忆 |

- `.env` 与 `.claw/` 下的运行产物不入库（已 gitignore）。
- ⚠️ **git 仓库根在上层的 `Career/` 目录**，不在本项目目录。
  `Projects/` 下的其他项目（如 `MCP-A2A/`）是独立练习，改动互不影响，
  提交时注意只 `git add` 本项目内的路径。

## 文件与清理

- 删除任何文件前先确认它不是**测试夹具 / 工作记忆 / 单一事实源**：
  - `workspace/`：演示工作区（`error.log` 约 140KB 是真实大文件测试的输入）
  - `workspace/AGENTS.md`：演示工作区的**角色提示词**（不是夹具）
  - `.workbuddy/`：跨机器同步的工作记忆
- 清理类操作**先出清单、经确认再动手**，批量删除要分批并逐批校验。

## 打包与入口

- 入口在包内：`src/tiny_claw/cli.py`，entry point 为 `tiny-claw = "tiny_claw.cli:main"`。
- 根目录 `main.py` 是 **24 行兼容壳**：未安装时把 `src` 挂进 `sys.path`，
  使 `python main.py` 与 `tiny-claw` 两种用法都成立。
- 入口曾在包外（`packages.find` 只扫 `src/`），导致安装后没有可用命令——别再移回去。
- editable 安装需在本机终端验证；自动化沙箱里 setuptools 的构建会撞
  `EEXIST: mkdir .../builds-v0/.tmpXXXX/...`（环境问题，与本项目配置无关）。

## 已知工程噪音

- `langsmith` 在无 Key 时会打 401 认证失败的噪音日志（用例仍全绿）；
  跑评测时可用 `LANGSMITH_TRACING=false` 抑制（必须在 import 之前设置，config 是 import 时快照）。
- 系统临时目录残留可能导致构建/测试报 `EEXIST`，用 `TMPDIR` 指向工作区内目录可绕过。
