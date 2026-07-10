"""上下文压缩器 — 对应 internal/context/compactor.go

监控和压缩上下文内存，防止大模型 OOM。
双重降级防线：远期历史全量掩码 + 短期记忆掐头去尾截断。
"""

import logging

from tiny_claw.schema import Message, Role

logger = logging.getLogger("tiny-claw.context.compactor")


class Compactor:
    """上下文压缩器"""

    def __init__(self, max_chars: int = 8000, retain_last: int = 6):
        self.max_chars = max_chars
        self.retain_last = retain_last

    def compact(self, messages: list[Message]) -> list[Message]:
        """压缩消息列表，返回压缩后的副本（不修改原数组）。"""
        current_len = self._estimate_length(messages)

        if current_len < self.max_chars:
            return messages

        logger.info(
            "⚠️ 内存告警：上下文长度 (%d) 超过阈值 (%d)，触发压缩...",
            current_len,
            self.max_chars,
        )

        msg_count = len(messages)
        protect_start = max(0, msg_count - self.retain_last)
        compacted: list[Message] = []

        for i, msg in enumerate(messages):
            # System Prompt 绝对不能动
            if msg.role == Role.SYSTEM:
                compacted.append(msg)
                continue

            in_working_memory = i >= protect_start
            new_msg = Message(
                role=msg.role,
                content=msg.content,
                tool_calls=list(msg.tool_calls),
                tool_call_id=msg.tool_call_id,
            )

            if msg.tool_call_id:
                # 工具返回结果
                if not in_working_memory:
                    # 远期历史：全量掩码
                    if len(msg.content) > 200:
                        new_msg.content = f"...[为了节省内存，早期的工具输出已被系统强制清理。原始长度: {len(msg.content)} 字节]..."
                else:
                    # 短期记忆：掐头去尾截断
                    max_keep = 1000
                    if len(msg.content) > max_keep:
                        head = msg.content[:500]
                        tail = msg.content[-500:]
                        new_msg.content = f"{head}\n\n...[内容过长，中间 {len(msg.content) - max_keep} 字节已被系统截断]...\n\n{tail}"

            elif msg.role == Role.ASSISTANT and msg.content:
                # 模型推理废话
                if not in_working_memory and len(msg.content) > 200:
                    new_msg.content = "...[早期的推理思考过程已折叠]..."

            # tool_calls 绝不改动 — 这是维系逻辑链的关键
            compacted.append(new_msg)

        new_len = self._estimate_length(compacted)
        logger.info("✅ 压缩完成。上下文长度从 %d 降至 %d 字符。", current_len, new_len)
        return compacted

    def _estimate_length(self, messages: list[Message]) -> int:
        """估算上下文总字符长度"""
        total = 0
        for msg in messages:
            total += len(msg.content)
            for tc in msg.tool_calls:
                total += len(tc.name) + len(str(tc.arguments))
        return total
