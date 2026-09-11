"""tiny-claw 基准测试入口

跑分哲学：**真金白银只花一次**。
本次运行把 API 计量、工具输出体积、每轮压缩前的上下文快照全部录成语料
（.claw/sandbox/traces/）。之后调阈值（COMPACT_TOKENS_* / READ_MAX_CHARS /
BASH_MAX_OUTPUT）一律用 tools/replay_thresholds.py 在本地重放语料，零 API 成本。

Usage:
    python run_benchmark.py                      # 全套件，默认预算 ¥2
    python run_benchmark.py --only test_001_edit # 只跑指定用例
    python run_benchmark.py --budget-cny 5       # 放宽预算
"""

import os
import sys
from pathlib import Path

# 跑分环境要最小化外部依赖：LangSmith 没配 key，开着只会让后台线程
# 反复重试上报拖慢用例。必须在 import tiny_claw 之前设置——
# config 是 import 时快照，晚了就关不掉了。
os.environ["LANGSMITH_TRACING"] = "false"

# 路径引导：项目尚未 pip install -e .（README.md 缺失会导致安装失败，
# 属于待补的门面），与 tests/conftest.py 同款手法直接指向 src/
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import argparse
import asyncio
import logging

from tiny_claw import config
from tiny_claw.eval.benchmark import BenchmarkRunner, TestCase

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")


# ═══════════════════════════════════════════════════════════════
# 测试用例定义
# ═══════════════════════════════════════════════════════════════
#
# 用例分两类：
#   短任务（001/002）→ 验证基础能力与「跑一轮的基线开销」
#   长上下文（003/004）→ 刻意制造大工具输出 / 多轮累积，
#     为阈值校准提供语料。没有这两类，8000 token 的压缩阈值
#     在跑分里永远触发不了，所谓「实测调参」就是空话。

CASES: list[TestCase] = [
    TestCase(
        id="test_001_edit",
        name="测试模糊替换工具的准确性",
        max_turns=8,
        # 准备靶机：生成一个有错误的 JSON 文件
        setup_script=(
            'echo \'{"name": "tiny-claw", "version": "v1.0.0"}\' > config.json'
        ),
        # 考题：要求修改版本号
        task_prompt=(
            "当前目录下有一个 config.json。"
            "请你使用 edit_file 工具，将其中的 version 从 v1.0.0 改为 v2.0.0。"
            "不要做其他多余操作。"
        ),
        # 判卷脚本：检查文件是否包含 v2.0.0
        validate_script='grep \'"version": "v2.0.0"\' config.json',
    ),
    TestCase(
        id="test_002_code_gen",
        name="测试代码阅读与创建新文件的综合能力",
        max_turns=10,
        # 准备靶机：生成一个简单的乘法函数
        setup_script=(
            "echo 'def multiply(a, b):\\n    return a * b\\n' > math_utils.py"
        ),
        # 考题：阅读代码后写单元测试（使用内置 unittest，不需要安装第三方包）
        task_prompt=(
            "当前目录下有一个 math_utils.py，里面有一个 multiply 函数。"
            "请你仔细阅读它，然后在同级目录下，帮我写一个规范的单元测试文件 "
            "test_math_utils.py，使用 Python 内置的 unittest 框架（import unittest）"
            "来测试 multiply 函数。请务必包含正常的测试用例。"
        ),
        # 判卷脚本：使用内置 unittest（不需要 pytest）
        validate_script=("python -m unittest test_math_utils.py -v 2>&1"),
    ),
    TestCase(
        id="test_003_big_read",
        name="测试大文件读取：截断/卸载/分段取回",
        max_turns=12,
        # 生成约 1200 行的中文文档（~40k 字符，远超 read_file 的 8000 字符上限），
        # 每隔 100 行埋一个核对点 —— 无论 agent 从哪一段读起都能找到，
        # 保证判卷稳定，同时逼出「大输出如何进入上下文」的真实路径。
        setup_script=(
            "python -c \"\n"
            "lines = []\n"
            "for i in range(1, 1201):\n"
            "    if i % 100 == 0:\n"
            "        lines.append(f'第{i}行 [CHECKPOINT-7f3a] 库存核对点，区间状态正常')\n"
            "    else:\n"
            "        lines.append(f'第{i}行：常规巡检记录，各项指标平稳，无异常上报。')\n"
            "open('inventory_log.txt', 'w', encoding='utf-8').write('\\n'.join(lines))\n"
            "\""
        ),
        task_prompt=(
            "当前目录下有一个 inventory_log.txt，内容很长。"
            "里面散布着若干个含 CHECKPOINT-7f3a 的核对点。"
            "请你阅读这个文件，找出所有核对点，并把每个核对点所在行号"
            "写入 answer.txt（每行一个，格式如：第200行）。"
        ),
        # 12 个核对点都在 100 的整数倍行上，agent 读到任何一段都能报出行号。
        # ⚠️ 判卷用 grep -E（POSIX ERE）：`a\|b` 这种 BRE 交替写法在
        # macOS 的 BSD grep 上不生效，曾把正确产出判成假阴性（2/4 变 4/4）。
        validate_script="grep -Eq 'CHECKPOINT|行' answer.txt && test -s answer.txt",
    ),
    TestCase(
        id="test_004_multi_step",
        name="测试多轮累积上下文下的跨文件整合",
        max_turns=12,
        # 三个分片文件，逼 agent 至少读 3 次文件 + 写 1 次，
        # 制造多轮上下文累积，为压缩阈值提供「多轮后上下文多大」的语料
        setup_script=(
            "printf '销售额：1200万，同比增长15%%\\n' > q1.txt && "
            "printf '销售额：1450万，同比增长21%%\\n' > q2.txt && "
            "printf '销售额：1980万，同比增长37%%\\n' > q3.txt"
        ),
        task_prompt=(
            "当前目录下有 q1.txt、q2.txt、q3.txt 三个季度报告。"
            "请你全部阅读后，写一份 summary.md，内容包括："
            "三个季度的销售额总和、增长最快的季度、以及一句话趋势结论。"
        ),
        validate_script=(
            "grep -q '4630' summary.md && grep -Eq 'q3|Q3|三' summary.md"
        ),
    ),
]


async def main() -> None:
    parser = argparse.ArgumentParser(description="tiny-claw 基准测试")
    parser.add_argument(
        "--budget-cny",
        type=float,
        default=2.0,
        help="金额止损（元）。默认 2.0 —— 按 v4-flash 闲时未命中价约可跑 130 万输入 token",
    )
    parser.add_argument(
        "--budget-tokens",
        type=int,
        default=800_000,
        help="token 兜底止损。不依赖价格表，价格缺失时金额止损会失效，这个必须留",
    )
    parser.add_argument(
        "--only",
        action="append",
        help="只跑指定 case_id，可多次传入",
    )
    args = parser.parse_args()

    if not config.has_llm_credentials():
        print(
            "未找到模型凭据：请在项目根 .env 中设置 DEEPSEEK_API_KEY"
            "（或 ANTHROPIC_API_KEY），参考 .env.example"
        )
        raise SystemExit(1)

    cases = CASES
    if args.only:
        wanted = set(args.only)
        cases = [c for c in CASES if c.id in wanted]
        missing = wanted - {c.id for c in cases}
        if missing:
            print(f"未知的用例 ID: {sorted(missing)}，可用: {[c.id for c in CASES]}")
            raise SystemExit(1)

    # 模型统一取 tiny_claw.config.MODEL，与 CLI 保持一致——
    # 否则跑分用的模型和正式跑的模型不是同一个，数据没有可比性。
    runner = BenchmarkRunner(
        model=config.MODEL,
        base_work_dir=str(Path.cwd()),
        budget_cny=args.budget_cny,
        budget_tokens=args.budget_tokens,
    )
    report = await runner.run_suite(cases)
    report_path = runner.save_report(report)

    # 给用户一句人话总结：钱花在哪、下一步去哪重放
    print(
        f"\n跑分完成: {report.passed}/{report.total} 通过 | "
        f"¥{report.total_cost_cny:.4f} | "
        f"{report.total_prompt_tokens + report.total_completion_tokens} token | "
        f"校准系数 {report.calibration_ratio:.2f}\n"
        f"报告: {report_path}\n"
        f"语料: {runner._trace_dir}/ （用 tools/replay_thresholds.py 离线调阈值）"
    )

    raise SystemExit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
