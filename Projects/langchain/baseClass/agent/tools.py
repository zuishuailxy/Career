import asyncio
import math
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from utils import create_llm


@tool
def calculator(expression: str) -> str:
    """执行数学计算。输入一个数学表达式（如 '2 + 3 * 4'、'sqrt(144)'、'1879 * 3'），返回计算结果。
    支持的运算：+, -, *, /, ** (幂), sqrt(), abs(), sin(), cos(), log() 等 math 模块函数。"""
    try:
        # 允许使用 math 模块的函数
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("_")
        }
        allowed_names["__builtins__"] = {}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算出错: {e}。请提供有效的数学表达式。"


async def main():
    llm = create_llm()

    search = DuckDuckGoSearchRun(api_wrapper=DuckDuckGoSearchAPIWrapper())

    agent = create_react_agent(llm, [search, calculator])

    inputs = {
        "messages": [("user", "爱因斯坦的出生年份是多少？他的年龄乘以 3 等于多少？")]
    }
    async for event in agent.astream(inputs, stream_mode="values"):
        event["messages"][-1].pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
