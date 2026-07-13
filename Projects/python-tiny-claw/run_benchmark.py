"""tiny-claw 基准测试入口

Usage:
    python run_benchmark.py
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from tiny_claw.eval.benchmark import BenchmarkRunner, TestCase

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")


# ═══════════════════════════════════════════════════════════════
# 测试用例定义
# ═══════════════════════════════════════════════════════════════

CASES: list[TestCase] = [
    TestCase(
        id="test_001_edit",
        name="测试模糊替换工具的准确性",
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
]


async def main():
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("请先导出 DEEPSEEK_API_KEY 环境变量进行跑分测试")
        raise SystemExit(1)

    runner = BenchmarkRunner(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        base_work_dir=os.getcwd(),
    )
    report = await runner.run_suite(CASES)
    runner.save_report(report)

    raise SystemExit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
