from dotenv import load_dotenv
import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from utils import create_llm
from langchain_tavily import TavilySearch
from langsmith import Client

load_dotenv()
llm = create_llm()
client = Client()
# ---- LangSmith 配置 ----
os.environ["LANGSMITH_TRACING"] = "true"  # 必须显式设为 "true"
os.environ["LANGSMITH_PROJECT"] = "graph"  # 项目名，必填！
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "")
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")


# 定义状态类型，继承自 TypedDict，并使用 add_messages 函数将消息追加到现有列表
class State(TypedDict):
    messages: Annotated[list, add_messages]


# 初始化 Tavily 搜索工具
tavily_tool = TavilySearch(
    max_results=2,  # 返回的最大结果数[reference:14]
    topic="general",  # 搜索主题，可选 "general" 或 "news"[reference:15]
    search_depth="basic",  # 搜索深度，"basic" 或 "advanced"[reference:16]
    include_answer=False,  # 是否包含答案摘要[reference:17]
    include_raw_content=False,  # 是否包含原始内容[reference:18]
)


# 将工具绑定到 LLM，让模型能决定何时调用搜索
tools = [tavily_tool]
llm_with_tools = llm.bind_tools(tools)


def chatbot(state: State) -> dict:
    """
    聊天节点：LLM 自行决定是直接回答还是调用工具
    """
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


# 构建图：chatbot ↔ tools
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)

# ToolNode 自动执行 LLM 请求的工具调用
tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "chatbot")

# 条件边：有 tool_calls → 执行工具，否则 → 结束
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,  # LangGraph 内置：检测消息中是否有 tool_calls
)
# 工具执行完后回到 chatbot 继续对话
graph_builder.add_edge("tools", "chatbot")

# 编译时注入 checkpointer，否则 config 不生效
memory = InMemorySaver()
graph = graph_builder.compile(
    checkpointer=memory,
    # interrupt_before=["tools"]
)  # 在 tools 节点前中断，便于调试

# 画图
# 1. 获取 PNG 二进制数据
img_data = graph.get_graph().draw_png()

# 2. 写入文件
with open("graph_with_tools.png", "wb") as f:
    f.write(img_data)

print("图片已保存为 graph_with_tools.png")

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
            {"messages": [("user", user_input)]}, config=config, stream_mode="values"
        ):
            # 跳过 interrupt 事件，只处理包含 messages 的状态
            if "messages" in event:
                event["messages"][-1].pretty_print()

        # interrupt_before=["tools"] 导致图在工具节点前中断，自动恢复执行
        # state = graph.get_state(config)
        # if state.next:
        #     result = graph.invoke(None, config=config)
        #     result["messages"][-1].pretty_print()


if __name__ == "__main__":
    # async_run_chatbot()
    run_chatbot()
