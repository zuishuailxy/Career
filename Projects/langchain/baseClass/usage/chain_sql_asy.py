"""
利用llm 操作数据库
"""

from langchain.agents import create_agent
from utils import create_llm
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
import asyncio

db_uri = "postgresql+psycopg2://admin:123456@localhost:5432/mydatabase"
db = SQLDatabase.from_uri(db_uri)
llm = create_llm(0)

# 获取 SQL 工具包中的所有工具
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

agent = create_agent(llm, tools)

# question = "库存最多的鲜花是哪一种？它的库存量是多少？"
# response = agent.invoke({"messages": [("user", question)]})
# # 取最后一条 AI 消息作为答案
# final_message = response["messages"][-1]
# print("回答：", final_message.content)

# question = "Lily的销量+10"
# response = agent.invoke({"messages": [("user", question)]})
# # 取最后一条 AI 消息作为答案
# final_message = response["messages"][-1]
# print("回答：", final_message.content)


# async def main():
#     question = "库存最多的鲜花是哪一种？它的库存量是多少？"
#     # 使用 ainvoke 替代 invoke
#     response = await agent.ainvoke({"messages": [("user", question)]})
#     final_message = response["messages"][-1]
#     print("回答：", final_message.content)


async def main1():
    # 定义多个需要查询的问题
    questions = [
        "库存最多的鲜花是哪一种？",
        "价格最高的鲜花是哪一种？",
        "所有鲜花的总库存是多少？",
    ]
    # 并发执行所有查询
    tasks = [agent.ainvoke({"messages": [("user", q)]}) for q in questions]
    # asyncio.gather 会并发执行所有任务
    results = await asyncio.gather(*tasks)
    # 打印结果
    for q, r in zip(questions, results):
        print(f"问题: {q}")
        print(f"回答: {r['messages'][-1]}\n")


async def main():

    question = "库存最多的鲜花是哪一种？它的库存量是多少？"
    # 使用 astream 替代 ainvoke
    async for event in agent.astream(
        {"messages": [("user", question)]},
        stream_mode="values"  # 流式返回每一步的完整状态
    ):
        # 打印每一步的消息
        if "messages" in event:
            event["messages"][-1].pretty_print()


# 7. 运行异步主函数
if __name__ == "__main__":
    asyncio.run(main())
