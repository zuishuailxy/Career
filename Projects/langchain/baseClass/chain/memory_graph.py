"""
LangGraph 检查点器（Checkpointer） 的一个代码示例，它替代了 ConversationBufferWindowMemory 在单次会话中记忆最近对话的功能。
"""

from utils import create_llm
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent

# 1. 初始化模型和工具（如果有）
model = create_llm()
tools = []  # 你的工具列表

# 2. 创建内存检查点器 (替代 ConversationBufferWindowMemory)
memory = InMemorySaver()  # 生产环境可用 SqliteSaver 或 PostgresSaver[reference:13]

# 3. 创建 Agent 时传入 checkpointer
agent = create_agent(model, tools, checkpointer=memory)  # 关键：注入记忆能力

# 4. 通过 thread_id 保持会话
config = {"configurable": {"thread_id": "user-123"}}

# 第一轮对话
agent.invoke({"messages": [{"role": "user", "content": "你好，我叫小明"}]}, config)


# 第二轮对话，模型会记得你
response = agent.invoke(
    {"messages": [{"role": "user", "content": "我叫什么名字？"}]}, config
)
print(response["messages"][-1].content)  # 输出: 你的名字是小明。
