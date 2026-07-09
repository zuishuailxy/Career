"""BashTool — 对应 internal/tools/bash.go

在工作区执行 bash 命令，带超时控制、自愈机制、输出截断。
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from tiny_claw.tools.base import BaseTool
from tiny_claw.schema import ToolDefinition

logger = logging.getLogger("tiny-claw.tools.bash")

TIMEOUT = 30  # 命令最大执行秒数
MAX_OUTPUT = 8000  # 最大输出字节数


class BashTool(BaseTool):
    """在当前工作区执行 bash 命令"""

    def __init__(self, work_dir: str):
        self._work_dir = str(Path(work_dir).resolve())

    def name(self) -> str:
        return "bash"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name(),
            description=(
                "在当前工作区执行任意的 bash 命令。支持链式命令(如 &&)。"
                "返回标准输出(stdout)和标准错误(stderr)。"
                "对于常驻服务（如 npm run dev），请设置 background=true 避免阻塞。"
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 bash 命令，例如: ls -la 或 python test.py",
                    },
                    "background": {
                        "type": "boolean",
                        "description": "是否为后台常驻任务（如 npm run dev）。true 时立即返回 PID 不等待。",
                    },
                },
                "required": ["command"],
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> str:
        command = arguments.get("command", "")
        background = arguments.get("background", False)
        if not command:
            return "Error: 缺少 command 参数"

        try:
            # 通过 bash -c 执行，支持管道、&& 等 Shell 语法
            proc = await asyncio.create_subprocess_exec(
                "bash",
                "-c",
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._work_dir,
            )

            # 后台模式：不等待，直接返回 PID
            if background:
                return f"后台任务已启动 (PID: {proc.pid})。使用 `kill {proc.pid}` 可终止。"

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT)
        except asyncio.TimeoutError:
            return f"[警告: 命令执行超时({TIMEOUT}s)，已被系统强制终止。如果是启动常驻服务，请尝试将其转入后台。]"
        except FileNotFoundError:
            return "Error: bash 不可用"
        except Exception as e:
            return f"执行报错: {e}"

        output = stdout.decode("utf-8", errors="replace")
        if stderr:
            output += stderr.decode("utf-8", errors="replace")

        # 自愈机制：bash 报错不抛异常，把错误原样返回让模型自己分析
        if proc.returncode != 0:
            return (
                f"执行报错 (exit code {proc.returncode}):\n{output}"
                if output
                else f"执行报错 (exit code {proc.returncode})"
            )

        if not output:
            return "命令执行成功，无终端输出。"

        # 长度截断保护（防 OOM）
        if len(output.encode("utf-8")) > MAX_OUTPUT:
            return (
                output[:MAX_OUTPUT]
                + f"\n\n...[终端输出过长，已截断至前 {MAX_OUTPUT} 字节]..."
            )

        return output
