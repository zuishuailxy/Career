"""
ReAct 框架，大模型将被引导生成一个任务解决轨迹，即观察环境 - 进行思考 - 采取行动。观察和思考阶段被统称为推理（Reasoning），而实施下一步行动的阶段被称为行动（Acting）。在每一步推理过程中，都会详细记录下来，这也改善了大模型解决问题时的可解释性和可信度。
"""

import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain.agents import create_agent
from utils import create_llm
import serpapi

load_dotenv()
llm = create_llm(0)
# 初始化 SerpAPI 搜索器


# 定义计算平方的函数
@tool
def square(n: int):
    """计算一个整数的平方。"""  # 这里是文档字符串
    return int(n) ** 2


# 使用 @tools 装饰器将其包装为 LangChain 工具[reference:3]
@tool
def web_search(query: str) -> str:
    """使用 SerpApi 在互联网上搜索最新的信息。
    当用户询问实时信息、新闻、天气、股票等需要联网搜索的内容时，应使用此工具。"""
    api_key = os.environ["SERPAPI_API_KEY"]
    client = serpapi.Client(api_key=api_key)
    results = client.search(
        {
            "engine": "google",
            "q": query,
        }
    )
    # 提取有机搜索结果
    organic_results = results.get("organic_results", [])
    if not organic_results:
        return "未找到相关搜索结果。"

    # 返回前几条结果的摘要
    snippets = []
    for r in organic_results[:5]:
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")
        snippets.append(f"标题: {title}\n摘要: {snippet}\n链接: {link}")

    return "\n\n".join(snippets)


agent = create_agent(
    tools=[square, web_search],  # 传入工具列表
    model=llm,
)
response = agent.invoke(
    # {"messages": [{"role": "user", "content": "计算 5 的平方，然后加上 3"}]}
    {
        "messages": [
            {
                "role": "user",
                "content": "今天成都适合出门吗？一步一步思考",
            }
        ]
    }
)
# 5. 输出最终答案
print(response["messages"][-1].content)
print(response)
