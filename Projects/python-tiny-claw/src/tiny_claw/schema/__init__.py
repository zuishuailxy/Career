"""公共数据结构 — 对应 internal/schema/message.go"""

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---- Role 角色定义 ----


class Role(StrEnum):
    """消息角色，与大模型沟通的基石"""

    SYSTEM = "system"  # 系统提示词：确立 Agent 的性格与红线
    USER = "user"  # 用户输入 / 工具执行的返回结果 (Observation)
    ASSISTANT = "assistant"  # 模型的输出：推理(Reasoning) 或工具调用(ToolCall)


# ---- 核心消息结构 ----


@dataclass
class ToolCall:
    """模型请求调用某个具体的工具"""

    id: str  # 工具调用的唯一 ID
    name: str  # 工具名称 (例如 "bash")
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, id: str, name: str, arguments: str) -> ToolCall:
        """从 JSON 字符串参数构建 (对应 Go 的 json.RawMessage 延迟解析)"""
        return cls(id=id, name=name, arguments=json.loads(arguments))


@dataclass
class Message:
    """上下文中传递的单条消息"""

    role: str  # system / user / assistant / tool
    content: str = ""  # 纯文本内容
    tool_calls: list[ToolCall] = field(default_factory=list)  # 模型决定调用工具时填充
    tool_call_id: str = ""  # 工具调用响应的关联 ID


@dataclass
class ToolResult:
    """工具在本地执行完毕后返回的物理结果"""

    tool_call_id: str
    output: str  # 控制台输出或报错堆栈
    is_error: bool = False  # 是否失败，供后续错误自愈


@dataclass
class ToolDefinition:
    """工具元信息，供模型理解工具有什么用"""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)  # JSON Schema


__all__ = [
    "Role",
    "Message",
    "ToolCall",
    "ToolResult",
    "ToolDefinition",
]
