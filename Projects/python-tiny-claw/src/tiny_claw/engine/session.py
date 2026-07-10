"""会话管理 — 对应 internal/engine/session.go"""

import asyncio
from datetime import datetime, timezone

from tiny_claw.schema import Message


class Session:
    """一次持续的人机交互过程"""

    def __init__(self, session_id: str, work_dir: str):
        self.id = session_id
        self.work_dir = work_dir
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self._history: list[Message] = []
        self._lock = asyncio.Lock()

    async def append(self, *msgs: Message) -> None:
        """线程安全地追加消息"""
        async with self._lock:
            self._history.extend(msgs)
            self.updated_at = datetime.now(timezone.utc)

    async def get_working_memory(self, limit: int = 0) -> list[Message]:
        """获取短期工作记忆 — 截取最近 N 条。

        自动剔除截断产生的孤儿工具响应。
        """
        async with self._lock:
            total = len(self._history)
            if limit <= 0 or total <= limit:
                return list(self._history)

            recent = self._history[total - limit :]
            while recent and recent[0].tool_call_id:
                recent.pop(0)
            return recent

    def __len__(self) -> int:
        return len(self._history)


class SessionManager:
    """全局会话管理器 — 多用户/多终端隔离"""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: str, work_dir: str) -> Session:
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = Session(session_id, work_dir)
            return self._sessions[session_id]


global_session_mgr = SessionManager()
