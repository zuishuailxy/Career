"""tiny-claw 入口 — 对应 cmd/claw/main.go"""

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

# LangSmith 追踪
import tiny_claw.tracing
from tiny_claw.engine import AgentEngine
from tiny_claw.provider import DeepSeekProvider
from tiny_claw.tools import RegistryImpl
from tiny_claw.tools.builtin import ReadFileTool, WriteFileTool, BashTool, EditFileTool

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
logger = logging.getLogger("tiny-claw")


# ==========================================
# 组装运行
# ==========================================
def main():
    logger.info("tiny-claw starting...")
    asyncio.run(_run())


async def _run():
    work_dir = os.getcwd()

    # 1. 初始化真实的大脑 — DeepSeek
    llm = DeepSeekProvider()

    # 2. 初始化 Tool Registry 并挂载真实工具
    registry = RegistryImpl()
    registry.register(ReadFileTool(work_dir))
    registry.register(WriteFileTool(work_dir))
    registry.register(BashTool(work_dir))
    registry.register(EditFileTool(work_dir))

    # 3. 启动引擎（关闭慢思考以加快速度）
    engine = AgentEngine(llm, registry, work_dir, enable_thinking=False)

    # 4. 执行任务
    await engine.run(
        """ 我当前目录下有一个 test.go 文件。 请帮我把里面 "TODO: 增加鉴权逻辑" 下面的那个 if 语句，整个替换为： if user == nil { fmt.Println("Forbidden!") return } """
    )


if __name__ == "__main__":
    main()
