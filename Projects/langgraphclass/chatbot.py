from dotenv import load_dotenv
import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from utils import create_llm

load_dotenv()
llm = create_llm()

# ---- LangSmith 配置 ----
os.environ["LANGSMITH_TRACING"] = "true"  # 必须显式设为 "true"
os.environ["LANGSMITH_PROJECT"] = "graph"  # 项目名，必填！
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")


# 定义状态类型，继承自 TypedDict，并使用 add_messages 函数将消息追加到现有列表
class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot(state: State) -> dict:
    """
    聊天节点函数：
    - state: 当前状态，包含消息列表
    - 返回值: 新的状态，包含最新的消息列表
    """
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


# 创建一个状态图对象，传入状态定义
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)  # 添加聊天节点
graph_builder.add_edge(START, "chatbot")  # 添加起始边
graph_builder.add_edge("chatbot", END)  # 添加结束边

# 编译时注入 checkpointer，否则 config 不生效
memory = InMemorySaver()
graph = graph_builder.compile(checkpointer=memory)

# 画图
# # 1. 获取 PNG 二进制数据
# img_data = graph.get_graph().draw_png()

# # 2. 写入文件
# with open("graph.png", "wb") as f:
#     f.write(img_data)

# print("图片已保存为 graph.png")

# 3. 通过 thread_id 保持会话
config = {"configurable": {"thread_id": "user-123"}}


# Stream event 实现流世输出
def async_run_chatbot():
    """运行聊天机器人，通过 astream_events 实现逐 token 流式输出"""
    import asyncio

    async def chat():
        while True:
            user_input = input("你: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            print("Assistant: ", end="", flush=True)
            # astream_events 支持 v2，逐 token 输出
            async for event in graph.astream_events(
                {"messages": [("user", user_input)]},
                config=config,
                version="v2",
            ):
                if event["event"] == "on_chat_model_stream":
                    token = event["data"]["chunk"].content
                    if token:
                        print(token, end="", flush=True)
            print()

    asyncio.run(chat())


def run_chatbot():
    """运行聊天机器人"""

    while True:
        user_input = input("你: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        for event in graph.stream(
            {"messages": [("user", user_input)]},
            config=config,
        ):
            # 遍历每个事件的值
            for value in event.values():
                # 打印输出 chatbot 生成的最新消息
                print("Assistant:", value["messages"][-1].content)


if __name__ == "__main__":
    # async_run_chatbot()
    run_chatbot()
