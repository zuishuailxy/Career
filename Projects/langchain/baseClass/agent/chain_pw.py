"""
结构化工具（Structured Tool） 是 LangChain 中一种功能更强大的工具类型，它允许工具接收任意数量、任意类型的输入参数，而不仅仅是单个字符串。这使得 Agent 能够执行更复杂、更精确的操作。
"""

import asyncio
from playwright.async_api import async_playwright
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from utils import create_llm
from langchain.agents import create_agent


async def main():
    # 手动创建浏览器：绕过 create_async_playwright_browser() 的事件循环冲突
    # 该函数内部用 asyncio.get_event_loop().run_until_complete()，
    # 在 asyncio.run() 中会报 "This event loop is already running"
    pw = await async_playwright().start()
    async_browser = await pw.chromium.launch(headless=True)

    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()

    llm = create_llm(0.5)

    agent_chain = create_agent(
        tools=tools,
        model=llm,
    )

    response = await agent_chain.ainvoke(
        {
            "messages": [
                {"role": "user", "content": "What are the headers on baidu.com?"}
            ]
        }
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
