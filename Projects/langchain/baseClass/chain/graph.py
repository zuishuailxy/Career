"""
通过一个 checkpointer 让代理记住你是谁。"""

from utils import create_llm
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import SystemMessage

model = create_llm()

# 定义系统提示
SYSTEM_PROMPT = SystemMessage(content="你是一个友好的助手，用中文回答所有问题。")


# 定义简单的图
def call_model(state: MessagesState):
    # 首次调用时，消息列表前插入 system prompt
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM_PROMPT] + messages
    response = model.invoke(messages)
    return {"messages": response}


# 2. 构建并编译图，注入 checkpointer
builder = StateGraph(MessagesState)
builder.add_node("call_model", call_model)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)
checkpointer = InMemorySaver()  # 创建内存检查点
graph = builder.compile(checkpointer=checkpointer)

# 3. 通过 thread_id 保持会话
config = {"configurable": {"thread_id": "user-123"}}

# 第一轮对话
graph.invoke({"messages": [{"role": "user", "content": "你好，我叫小明"}]}, config)
# 第二轮对话，模型会记得你
response = graph.invoke(
    {"messages": [{"role": "user", "content": "我叫什么名字？"}]}, config
)
print(response["messages"][-1].content)
