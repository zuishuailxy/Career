from langchain_community.tools import DuckDuckGoSearchRun
from langchain.tools import tool
from langchain.agents import create_agent
from utils import create_llm

# 1. 初始化搜索工具
search = DuckDuckGoSearchRun()


@tool
def web_search(query: str):
    "当你需要查询实时信息或当前事件时非常有用。输入应该是一个搜索查询。"
    return search.invoke(query)


model = create_llm()

agent = create_agent(model=model, tools=[web_search])
response = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "谁是去年的TI冠军,一步一步思考",
            }
        ]
    }
)
# 5. 输出最终答案
print(response["messages"][-1].content)
