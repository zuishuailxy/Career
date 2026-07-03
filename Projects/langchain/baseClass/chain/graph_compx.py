"""用 LangGraph 实现近期原始消息 + 远期摘要的混合记忆策略。这个示例会展示如何在一个对话中，既保留最新的几条完整消息，又不断压缩更早的对话为摘要，从而避免超出 Token 限制。"""

from utils import create_llm
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import List, Optional


# ---------- 1. 定义状态 ----------
class AgentState(MessagesState):
    summary: str  # 存储对话摘要


llm = create_llm()


# ---------- 3. 定义节点 ----------
def chat_node(state: AgentState):
    """调用模型回复用户的最新消息"""
    # 构造消息列表：如果有摘要，先放摘要作为系统消息，再放最近的消息
    messages = state["messages"]
    if state.get("summary"):
        system_msg = SystemMessage(content=f"对话历史摘要：{state['summary']}")
        # 注意：实际应用中，摘要应放在最前面，但这里我们与最近消息一起传给模型
        messages = [system_msg] + messages[
            -3:
        ]  # 仅保留最近3条原始消息（包括用户最新提问）

    response = llm.invoke(messages)
    # 将模型回复添加到消息列表中
    return {"messages": messages + [response]}


def update_summary_node(state: AgentState):
    """更新对话摘要（只保留最新2条原始消息，其余压缩为摘要）"""
    messages = state["messages"]
    if len(messages) <= 2:
        # 消息太少，无需摘要
        return {}
    # 提取所有非系统消息（即用户和助手的对话）
    conversation = [m for m in messages if not isinstance(m, SystemMessage)]
    # 保留最新2条原始消息，其余用于生成摘要
    recent = conversation[-2:]
    old = conversation[:-2]
    if old:
        # 生成或更新摘要
        old_text = "\n".join([f"{m.type}: {m.content}" for m in old])
        summary_prompt = f"这是之前的对话：\n{old_text}\n请用一段话总结这段对话。"
        if state.get("summary"):
            summary_prompt = f"这是之前的总结：{state['summary']}\n\n现在有新的对话内容需要补充：\n{old_text}\n请更新总结，保留最重要的信息。"

        new_summary = llm.invoke([HumanMessage(content=summary_prompt)]).content
    else:
        # 如果没有旧消息，但已有摘要，则保持摘要不变
        new_summary = state.get("summary", "")

    # 更新状态：只保留最新2条消息 + 摘要
    return {
        "summary": new_summary,
        "messages": recent,
    }  # 重要：将消息列表替换为最近2条


# ---------- 4. 构建图 ----------
builder = StateGraph(AgentState)
# 添加节点
builder.add_node("chat", chat_node)
builder.add_node("update_summary", update_summary_node)
# 定义流转边：chat → update_summary → END
builder.set_entry_point("chat")
builder.add_edge("chat", "update_summary")
builder.add_edge("update_summary", END)

# 编译图，注入检查点器
memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)


# ---------- 5. 模拟对话 ----------
def run_conversation(user_input: str, thread_id: str = "user-123"):
    """执行一轮对话"""
    config = {"configurable": {"thread_id": thread_id}}

    # 调用图
    result = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config)

    # 打印最新回复
    latest_msg = result["messages"][-1]
    print(f"AI: {latest_msg.content}")
    print(f"当前摘要: {result.get('summary', '无')}\n")
    return result


# 开始对话
if __name__ == "__main__":
    thread_id = "test-user"

    # 第一轮
    print("=" * 10, "第一轮")
    run_conversation("你好，我叫小明，我是程序员。", thread_id)

    # 第二轮
    print("=" * 10, "第2轮")
    run_conversation("我喜欢用Python写代码。", thread_id)

    # 第三轮（此时摘要应该已经生成）
    print("=" * 10, "第3轮")
    run_conversation("你还记得我叫什么名字吗？", thread_id)

    # 第四轮
    print("=" * 10, "第4轮")
    run_conversation("我刚才说我喜欢用什么语言？", thread_id)

    # 第五轮（继续新话题）
    print("=" * 10, "第5轮")
    run_conversation("你最近有什么新功能吗？", thread_id)
