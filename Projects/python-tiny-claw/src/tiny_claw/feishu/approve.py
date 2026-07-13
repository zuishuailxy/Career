"""飞书审批管理器 — 对应 internal/feishu/approval.go

高危操作在执行前挂起，通过飞书发送审批请求，等待人工确认后放行或拒绝。
"""

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from tiny_claw.feishu.bot import FeishuReporter

# Reporter 可以是一个直接引用，也可以是一个延迟解析的 callable
ReporterLike = Union["FeishuReporter", Callable[[], "FeishuReporter | None"], None]

logger = logging.getLogger("tiny-claw.feishu.approve")

# =========================================================================
# 数据结构
# =========================================================================


@dataclass
class ApprovalResult:
    """审批结果"""

    allowed: bool
    reason: str = ""


# =========================================================================
# 高危命令检测
# =========================================================================

# Bash 高危模式正则
_DANGEROUS_BASH_PATTERNS: list[re.Pattern] = [
    # --- 文件/目录删除 ---
    re.compile(r"\brm\b", re.IGNORECASE),  # 任何 rm 命令（含 rm -rf / rm -r / rm file）
    re.compile(r"\bunlink\b", re.IGNORECASE),  # unlink 删除
    re.compile(r"\brmdir\b", re.IGNORECASE),  # 删除目录
    # --- 权限提升 ---
    re.compile(r"\bsudo\b", re.IGNORECASE),  # 提权
    # --- 数据库/系统 ---
    re.compile(r"\bdrop\b", re.IGNORECASE),  # 数据库 DROP
    # --- 覆盖写入 ---
    re.compile(
        r">\s*\S+\.(py|go|rs|js|ts|java|cpp|c|h|sh|yaml|yml|toml|json)", re.IGNORECASE
    ),
    # --- 磁盘危险操作 ---
    re.compile(r"\bmkfs\.", re.IGNORECASE),  # 格式化磁盘
    re.compile(r"\bdd\s+if=", re.IGNORECASE),  # 磁盘写入
    re.compile(r"\bmount\b", re.IGNORECASE),  # 挂载操作
    # --- 权限变更 ---
    re.compile(r"\bchmod\s+777", re.IGNORECASE),  # 危险权限
    re.compile(r"\bchown\b", re.IGNORECASE),  # 更改所有者
    # --- 进程/网络 ---
    re.compile(r"\bkill\s+-9", re.IGNORECASE),  # 强制杀进程
    re.compile(r"\bgit\s+push\s+.*--force", re.IGNORECASE),  # 强制推送
    re.compile(r"\bgit\s+reset\s+--hard", re.IGNORECASE),  # 硬重置
    re.compile(r"\bcurl.*\|\s*(ba)?sh", re.IGNORECASE),  # curl shell 管道执行
    re.compile(r"\bwget.*\|\s*(ba)?sh", re.IGNORECASE),  # wget shell 管道执行
    # --- 系统破坏 ---
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", re.IGNORECASE),  # fork bomb
    re.compile(r"\b>\/dev\/sda", re.IGNORECASE),  # 直接写磁盘设备
]


def is_dangerous_command(tool_name: str, args: str) -> bool:
    """判断该工具调用是否需要触发审批。

    纯读取工具（read_file）默认 YOLO 放行；
    bash 命中高危正则时需审批；
    write_file / edit_file 一律需审批。
    """
    # 只读工具 — 直接放行
    if tool_name not in ("bash", "write_file", "edit_file"):
        return False

    # write_file / edit_file — 始终需要审批（修改文件是高危操作）
    if tool_name in ("write_file", "edit_file"):
        return True

    # bash — 按高危模式匹配
    if tool_name == "bash":
        for pattern in _DANGEROUS_BASH_PATTERNS:
            if pattern.search(args):
                return True

    return False


# =========================================================================
# 审批管理器
# =========================================================================


class ApprovalManager:
    """统一管理当前正在等待人工审批的任务。

    作为全局单例，在 Registry Middleware 和飞书消息回调之间共享状态：
    - Middleware 调用 wait_for_approval() 挂起协程
    - 飞书 Webhook 收到 "approve/reject <task_id>" 时调用 resolve_approval() 唤醒
    """

    def __init__(self):
        # task_id → asyncio.Future[ApprovalResult]
        self._pending: dict[str, asyncio.Future[ApprovalResult]] = {}

    # ------------------------------------------------------------------
    # 挂起等待
    # ------------------------------------------------------------------
    async def wait_for_approval(
        self,
        tool_name: str,
        args: str,
        reporter: ReporterLike = None,
        timeout: float = 300.0,
    ) -> ApprovalResult:
        """发送审批通知，挂起协程等待人工批复。

        Args:
            tool_name: 工具名
            args: 工具参数（用于展示）
            reporter: 飞书消息发送器（None 时回退到终端打印）
            timeout: 超时秒数，超时后自动拒绝

        Returns:
            ApprovalResult(allowed, reason)
        """
        task_id = uuid.uuid4().hex[:8]  # 短 ID 方便人类输入

        # 创建 Future 用于阻塞
        loop = asyncio.get_running_loop()
        future: asyncio.Future[ApprovalResult] = loop.create_future()
        self._pending[task_id] = future

        # 构建通知消息
        notice = (
            f"⚠️ **高危操作审批请求**\n"
            f"Agent 试图执行以下动作:\n"
            f"- 工具: `{tool_name}`\n"
            f"- 参数: `{args}`\n"
            f"\n"
            f"任务 ID: **{task_id}**\n"
            f"\n"
            f"👉 请回复 `approve {task_id}` 或 `reject {task_id}` 来决定是否放行。\n"
            f"⏰ 超时 {timeout:.0f}s 后将自动拒绝。"
        )

        # 延迟解析 reporter（支持 callable 模式）
        r = reporter() if callable(reporter) else reporter

        # 发送通知
        if r:
            await r.send_msg(notice)
        else:
            # 回退到终端
            print(f"\n\033[31m[需要审批 TaskID: {task_id}]\033[0m")
            print(notice)

        logger.info("[Approval] 已发送审批请求 (TaskID: %s)，协程挂起等待...", task_id)

        try:
            # 挂起等待（带超时）
            result = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("[Approval] 审批超时 (TaskID: %s)，自动拒绝", task_id)
            result = ApprovalResult(allowed=False, reason="审批超时，自动拒绝")

        # 清理
        self._pending.pop(task_id, None)
        return result

    # ------------------------------------------------------------------
    # 回调唤醒
    # ------------------------------------------------------------------
    def resolve_approval(self, task_id: str, allowed: bool, reason: str = "") -> bool:
        """由飞书消息回调触发，向挂起的协程发送审批结果。

        Returns:
            bool: 是否成功唤醒（task_id 不存在时返回 False）
        """
        future = self._pending.get(task_id)
        if future is None:
            logger.info(
                "[Approval] 找不到对应的 TaskID: %s，可能已超时或处理完毕", task_id
            )
            return False

        if future.done():
            logger.info("[Approval] TaskID: %s 已完成，忽略重复回调", task_id)
            return False

        logger.info(
            "[Approval] 收到审批结果 (TaskID: %s, Allowed: %s)",
            task_id,
            allowed,
        )
        future.set_result(ApprovalResult(allowed=allowed, reason=reason))
        return True


# =========================================================================
# 全局单例
# =========================================================================

global_approval_mgr = ApprovalManager()


# =========================================================================
# 便捷工厂：创建审批中间件
# =========================================================================


def create_approval_middleware(
    reporter: ReporterLike = None,
    timeout: float = 300.0,
):
    """生成一个可与 Registry.use() 配合的审批中间件。

    Usage:
        from tiny_claw.feishu.approve import create_approval_middleware

        # 直接引用（CLI 模式）
        registry.use(create_approval_middleware(reporter=None))

        # 延迟解析（飞书模式，reporter 在 handle_agent 时才绑定）
        registry.use(create_approval_middleware(reporter=bot.reporter))

    Args:
        reporter: 飞书消息发送器，或返回 Reporter 的可调用对象。
                  None 时回退到终端打印。
        timeout: 审批超时秒数。
    """
    import json

    async def _mw(call):
        # 延迟解析 reporter（支持 bot.reporter 属性延迟绑定）
        r = reporter() if callable(reporter) else reporter

        # 提取参数为可读字符串
        try:
            args_str = json.dumps(call.arguments, ensure_ascii=False)
        except Exception:
            args_str = str(call.arguments)

        # 判断是否需要审批
        if not is_dangerous_command(call.name, args_str):
            return True, ""

        # 挂起等待审批
        result = await global_approval_mgr.wait_for_approval(
            tool_name=call.name,
            args=args_str,
            reporter=r,
            timeout=timeout,
        )

        return result.allowed, result.reason

    return _mw
