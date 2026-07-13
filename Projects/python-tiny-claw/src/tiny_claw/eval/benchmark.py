"""基准测试/评估系统 — 对应 internal/eval/benchmark.go

每个测试用例完全物理隔离：独立沙箱目录、独立引擎、独立 Session。
"""

import asyncio
import json
import logging
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from tiny_claw.engine import AgentEngine
from tiny_claw.engine.session import Session
from tiny_claw.provider import DeepSeekProvider
from tiny_claw.schema import Message, Role
from tiny_claw.tools import RegistryImpl
from tiny_claw.tools.builtin import BashTool, EditFileTool, ReadFileTool, WriteFileTool
from tiny_claw.tracing import CostTracker

logger = logging.getLogger("tiny-claw.eval")


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════


@dataclass
class TestCase:
    """一个需要 Agent 去完成并验证的独立任务"""

    id: str  # 用例唯一标识
    name: str  # 用例名称
    task_prompt: str  # 发送给 Agent 的任务指令
    setup_script: str = ""  # 【可选】Agent 运行前执行的 bash 脚本
    validate_script: str = ""  # 【核心】Agent 结束后执行的校验脚本，exit 0=成功
    max_turns: int = 30  # 允许 Agent 尝试的最大轮数


@dataclass
class TestResult:
    """单次跑分结果"""

    case_id: str
    case_name: str
    passed: bool
    duration_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_cny: float = 0.0
    error_msg: str = ""
    # ---- 顺滑度指标 ----
    error_turns: int = 0  # 包含至少一次工具调用失败的 Turn 数 (0 = 一发入魂)
    total_turns: int = 0  # 总 Turn 数（辅助计算比例）
    first_error_token: int = 0  # 首次错误时的累计 Token 数

    @property
    def waste_ratio(self) -> float:
        """试错浪费比：首次错误出现后消耗的 Token 占总 Token 的比例。

        0.0  = 零浪费（完美执行或首轮直接失败）
        0.5  = 一半的 Token 花在错误之后
        """
        total = self.prompt_tokens + self.completion_tokens
        if total == 0 or self.first_error_token == 0:
            return 0.0
        waste_tokens = total - self.first_error_token
        return max(0.0, waste_tokens / total)


@dataclass
class BenchmarkReport:
    """汇总报告"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    total_cost_cny: float = 0.0
    total_duration_ms: int = 0
    results: list[TestResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0


# ═══════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════


class BenchmarkRunner:
    """自动化回归测试执行器。

    每个用例拥有独立的沙箱目录、引擎实例、Session，确保完全隔离。
    """

    def __init__(
        self, model: str = "deepseek-v4-pro", base_work_dir: str | None = None
    ):
        self._model = model
        self._base_dir = Path(base_work_dir or Path.cwd()) / ".claw" / "sandbox"

    # ------------------------------------------------------------------
    # 套件入口
    # ------------------------------------------------------------------
    async def run_suite(self, cases: list[TestCase]) -> BenchmarkReport:
        """批量执行测试套件"""
        logger.info("=" * 50)
        logger.info("🚀 启动自动化 Benchmark 评估 | 模型: %s", self._model)
        logger.info("=" * 50)

        report = BenchmarkReport(total=len(cases))

        for tc in cases:
            logger.info("\n>>> ⏳ 正在执行用例 [%s]: %s", tc.id, tc.name)
            r = await self._run_single(tc)
            report.results.append(r)
            report.total_duration_ms += r.duration_ms
            report.total_cost_cny += r.cost_cny

            if r.passed:
                report.passed += 1
                logger.info(
                    ">>> ✅ [%s] 通过 | 耗时: %dms | 花费: ¥%.6f",
                    tc.id,
                    r.duration_ms,
                    r.cost_cny,
                )
            else:
                report.failed += 1
                logger.info(
                    ">>> ❌ [%s] 失败 | 错误: %s",
                    tc.id,
                    r.error_msg[:80],
                )

        # 终极报表
        logger.info("\n================ 🏆 跑分终极报告 ================")
        logger.info(
            "总用例: %d | 通过: %d | 失败: %d | 成功率: %.1f%%",
            report.total,
            report.passed,
            report.failed,
            report.pass_rate * 100,
        )
        logger.info("总消耗成本: ¥%.6f", report.total_cost_cny)
        logger.info("==================================================")

        return report

    # ------------------------------------------------------------------
    # 单用例执行（核心）— 对应 Go 的 runSingleTest
    # ------------------------------------------------------------------
    async def _run_single(self, tc: TestCase) -> TestResult:
        start = time.monotonic()

        # ---- 1. 创建物理隔离沙箱目录 ----
        sandbox = self._base_dir / f"{tc.id}_{int(time.time())}"
        sandbox.mkdir(parents=True, exist_ok=True)
        work_dir = str(sandbox)

        # ---- 2. Setup 脚本 ----
        if tc.setup_script:
            ok, output = await _run_bash(tc.setup_script, work_dir)
            if not ok:
                return TestResult(
                    case_id=tc.id,
                    case_name=tc.name,
                    passed=False,
                    error_msg=f"Setup 失败: {output[:200]}",
                )

        # ---- 3. 为每个用例创建独立引擎（完全物理隔离）----
        raw_provider = DeepSeekProvider()
        cost_tracker = CostTracker(raw_provider, model=self._model)

        registry = RegistryImpl()
        registry.register(ReadFileTool(work_dir))
        registry.register(WriteFileTool(work_dir))
        registry.register(BashTool(work_dir))
        registry.register(EditFileTool(work_dir))

        engine = AgentEngine(
            cost_tracker,
            registry,
            enable_thinking=False,
            plan_mode=False,
        )

        session = Session(tc.id, work_dir)
        cost_tracker.bind_session(session)

        # ---- 4. 驱动 Agent ----
        await session.append(Message(role=Role.USER, content=tc.task_prompt))

        try:
            await engine.run(session)
        except Exception as e:
            return TestResult(
                case_id=tc.id,
                case_name=tc.name,
                passed=False,
                error_msg=f"Agent 崩溃: {e}",
                cost_cny=session.total_cost_cny,
                prompt_tokens=session.total_prompt_tokens,
                completion_tokens=session.total_completion_tokens,
                error_turns=session.error_turns,
                total_turns=session.total_turns,
                first_error_token=session.first_error_token or 0,
            )

        # ---- 5. 验收成果 ----
        if tc.validate_script:
            ok, output = await _run_bash(tc.validate_script, work_dir)
            if not ok:
                return TestResult(
                    case_id=tc.id,
                    case_name=tc.name,
                    passed=False,
                    error_msg=f"校验失败: {output[:200]}",
                    cost_cny=session.total_cost_cny,
                    prompt_tokens=session.total_prompt_tokens,
                    completion_tokens=session.total_completion_tokens,
                    error_turns=session.error_turns,
                    total_turns=session.total_turns,
                    first_error_token=session.first_error_token or 0,
                )

        # ---- 6. 返回结果 ----
        duration = int((time.monotonic() - start) * 1000)
        return TestResult(
            case_id=tc.id,
            case_name=tc.name,
            passed=True,
            duration_ms=duration,
            cost_cny=session.total_cost_cny,
            prompt_tokens=session.total_prompt_tokens,
            completion_tokens=session.total_completion_tokens,
            error_turns=session.error_turns,
            total_turns=session.total_turns,
            first_error_token=session.first_error_token or 0,
        )

    # ------------------------------------------------------------------
    # 报告持久化
    # ------------------------------------------------------------------
    def save_report(self, report: BenchmarkReport, path: str | None = None) -> str:
        """保存报告为 JSON"""
        if path is None:
            path = str(self._base_dir / "benchmark_report.json")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "pass_rate": round(report.pass_rate, 4),
            "total_cost_cny": round(report.total_cost_cny, 6),
            "total_duration_ms": report.total_duration_ms,
            "results": [
                {
                    "case_id": r.case_id,
                    "case_name": r.case_name,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "cost_cny": round(r.cost_cny, 6),
                    "error_msg": r.error_msg,
                    "error_turns": r.error_turns,
                    "total_turns": r.total_turns,
                    "waste_ratio": round(r.waste_ratio, 4),
                }
                for r in report.results
            ],
        }
        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("[Benchmark] 报告已保存: %s", path)
        return path


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════


async def _run_bash(script: str, cwd: str) -> tuple[bool, str]:
    """执行 bash 脚本，返回 (成功?, 输出)"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode("utf-8", errors="replace")
        return proc.returncode == 0, output
    except asyncio.TimeoutError:
        return False, "脚本执行超时(60s)"
    except Exception as e:
        return False, str(e)
