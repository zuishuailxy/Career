"""
LangGraph + InMemorySaver + Streamlit 实现带记忆的聊天机器人
"""

from typing import Annotated, TypedDict
from uuid import uuid4
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from models import create_llm
import streamlit as st

# ---- LangGraph 部分（与 main2.py 相同）----


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


# ---- Streamlit 界面 ----

st.set_page_config(page_title="易速鲜花客服", page_icon="🌸")
st.title("🌸 易速鲜花聊天客服")

# 用 session_state 维护 thread_id（每个浏览器窗口独立会话）
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid4())
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    # 首次初始化 system 消息
    graph.invoke(
        {
            "messages": [
                SystemMessage(
                    content="你是一个花卉行家，热情回答用户关于鲜花的各种问题。"
                )
            ]
        },
        config=config,
    )
    st.session_state.messages = []

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# 渲染历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入
if prompt := st.chat_input("请输入你的问题..."):
    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用 LangGraph（InMemorySaver 自动带上历史）
    state = graph.invoke(
        {"messages": [HumanMessage(content=prompt)]},
        config=config,
    )
    reply = state["messages"][-1].content

    # 显示 AI 回复
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
