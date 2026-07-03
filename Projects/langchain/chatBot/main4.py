"""
LangGraph + InMemorySaver + Gradio 实现带记忆的聊天机器人
"""

from typing import Annotated, TypedDict
from uuid import uuid4
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import SystemMessage, HumanMessage
from models import create_llm
import gradio as gr

# ---- LangGraph 部分 ----


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


def chat_node(state: ChatState):
    model = create_llm()
    response = model.invoke(state["messages"])
    return {"messages": [response]}


builder = StateGraph(ChatState)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

# 全局 system prompt
SYSTEM_MSG = SystemMessage(content="你是一个花卉行家，热情回答用户关于鲜花的各种问题。")


# ---- Gradio 聊天函数 ----


def respond(message: str, history: list, request: gr.Request):
    """
    Gradio ChatInterface 回调：
    - message: 当前用户输入
    - history: 之前的对话历史
    - request: Gradio 请求对象（用于获取 session_hash 做会话隔离）
    """
    # 每个 Gradio 会话用独立 thread_id
    thread_id = getattr(request, "session_hash", str(uuid4()))
    config = {"configurable": {"thread_id": thread_id}}

    # 判断是否首次对话：history 为空时先注入 system 消息
    if not history:
        graph.invoke({"messages": [SYSTEM_MSG]}, config=config)

    # 调用 LangGraph，InMemorySaver 自动带上历史
    state = graph.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    return state["messages"][-1].content


# ---- 启动 Gradio ----

if __name__ == "__main__":
    demo = gr.ChatInterface(
        fn=respond,
        title="🌸 易速鲜花聊天客服",
        description="我是花卉行家，有什么关于鲜花的问题尽管问我！",
        examples=["玫瑰有什么寓意？", "如何养护百合花？", "送什么花给女朋友比较好？"],
    )
    demo.launch(share=True)
