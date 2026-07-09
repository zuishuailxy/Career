"""ReadFileTool — 对应 internal/tools/read_file.go

读取本地文件内容，带路径穿越防护和长度截断。
"""

import logging
import os
from pathlib import Path
from typing import Any

from tiny_claw.tools.base import BaseTool
from tiny_claw.schema import ToolDefinition

logger = logging.getLogger("tiny-claw.tools.read_file")

MAX_BYTES = 8000  # 最大读取字节数，防止 Context 爆炸


class ReadFileTool(BaseTool):
    """读取工作区内指定路径的文件内容"""

    def __init__(self, work_dir: str):
        self._work_dir = Path(work_dir).resolve()

    def name(self) -> str:
        return "read_file"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name(),
            description="读取指定路径的文件内容。请提供相对工作区的路径。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径，如 src/tiny_claw/main.py",
                    },
                },
                "required": ["path"],
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> str:
        # 1. 参数校验
        rel_path = arguments.get("path", "")
        if not rel_path:
            return "Error: 缺少 path 参数"

        # 2. 拼接并解析绝对路径，防路径穿越 (../../etc/passwd)
        full_path = (self._work_dir / rel_path).resolve()

        if not str(full_path).startswith(str(self._work_dir)):
            return f"Error: 路径穿越被拦截。'{rel_path}' 超出了工作区范围。"

        # 3. 读取文件
        try:
            content = full_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return f"Error: 文件不存在: {rel_path}"
        except PermissionError:
            return f"Error: 无权限读取: {rel_path}"
        except IsADirectoryError:
            return f"Error: '{rel_path}' 是一个目录，不是文件。"
        except UnicodeDecodeError:
            return f"Error: '{rel_path}' 不是文本文件，无法读取。"
        except Exception as e:
            return f"Error: 读取文件失败: {e}"

        # 4. 长度截断保护
        if len(content.encode("utf-8")) > MAX_BYTES:
            content = (
                content[:MAX_BYTES]
                + f"\n\n...[由于内容过长，已被系统截断至前 {MAX_BYTES} 字节]..."
            )

        return content
