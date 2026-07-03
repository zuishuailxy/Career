"""
将大语言模型 (LLM)、对话记忆 (Memory) 和提示模板 (Prompt Template) 这三个核心组件捆绑在一起，目标是让你能用最少的代码快速构建一个能记住上下文的聊天机器人
"""

from utils import create_llm
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory

model = create_llm()
# 1. 定义提示模板，显式地使用 MessagesPlaceholder 来插入历史消息
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个乐于助人的助手。"),
        MessagesPlaceholder(variable_name="history"),  # 历史消息将插入在这里
        ("human", "{input}"),
    ]
)

# 2. 用 LCEL 构建基础链 (prompt | llm)
chain = prompt | model

# 3. 创建用于存储不同会话历史的字典
store = {}


# 4. 定义一个函数，根据 session_id 获取或创建对应的对话历史
def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


# 5. 用 RunnableWithMessageHistory 包装基础链，使其具备记忆能力
wrapped_chain = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",  # 指定用户输入对应的 key
    history_messages_key="history",  # 指定历史消息对应的 key (与 Prompt 中定义的变量名一致)
)

# 6. 调用对话，通过 config 指定 session_id 来隔离不同会话
response_1 = wrapped_chain.invoke(
    {"input": "你好，我叫小明"}, config={"configurable": {"session_id": "user_123"}}
)
print(response_1.content)
response_2 = wrapped_chain.invoke(
    {"input": "我叫什么呢？如果我是小明的话，请叫我魔力明"},
    config={"configurable": {"session_id": "user_123"}},
)
print(response_2.content)
response_3 = wrapped_chain.invoke(
    {"input": "魔力明是谁"},
    config={"configurable": {"session_id": "user_123"}},
)
print(response_3.content)
