"""
LangGraph + InMemorySaver 实现带记忆的聊天机器人
"""

from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import SystemMessage, HumanMessage
from models import create_llm


# 1. 定义状态：messages 用 add_messages 自动合并历史
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


# 2. 聊天节点：调用 LLM 并返回响应
def chat_node(state: ChatState):
    model = create_llm()
    response = model.invoke(state["messages"])
    return {"messages": [response]}


# 3. 构建图 + 编译（checkpointer 是记忆的关键）
builder = StateGraph(ChatState)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)


# 4. 命令行聊天循环
if __name__ == "__main__":
    # thread_id 用于隔离不同会话的记忆
    config = {"configurable": {"thread_id": "user-session-1"}}

    # 设置系统角色（仅首次）
    system_msg = SystemMessage(content="你是一个花卉行家。")

    print("Chatbot 已启动! 输入'exit'来退出程序。")

    # 首次调用先传入 system 消息初始化
    graph.invoke({"messages": [system_msg]}, config=config)

    while True:
        user_input = input("你: ")
        if user_input.lower() == "exit":
            print("再见!")
            break

        # 每次传入新消息，InMemorySaver 自动保留历史
        state = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )
        print(f"Chatbot: {state['messages'][-1].content}")
