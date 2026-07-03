from dotenv import load_dotenv
import os
from typing import Literal, Annotated, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from utils import create_llm
from langchain_tavily import TavilySearch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain.tools import tool
from langchain_experimental.utilities import PythonREPL
from langsmith import Client
from langgraph.checkpoint.memory import InMemorySaver
from openai import BadRequestError

load_dotenv()


# ---- LangSmith 配置 ----
os.environ["LANGSMITH_TRACING"] = "true"  # 必须显式设为 "true"
os.environ["LANGSMITH_PROJECT"] = "graph"  # 项目名，必填！
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "")
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")

client = Client()
# 初始化 Tavily 搜索工具
tavily_tool = TavilySearch(
    max_results=2,  # 返回的最大结果数[reference:14]
    topic="general",  # 搜索主题，可选 "general" 或 "news"[reference:15]
    search_depth="basic",  # 搜索深度，"basic" 或 "advanced"[reference:16]
    include_answer=False,  # 是否包含答案摘要[reference:17]
    include_raw_content=False,  # 是否包含原始内容[reference:18]
)

# Python REPL 工具，用于执行 Python 代码
repl = PythonREPL()


# 第一步 定义研究员的部分
# 创建search 大模型
search_llm = create_llm()
# 研究员专用工具: tavily search
researcher_tools = [tavily_tool]
researcher_tool_node = ToolNode(researcher_tools)
# 绑定工具给模型
researcher_model = search_llm.bind_tools(researcher_tools)


# 定义研究员节点的函数
def researcher_node(state: MessagesState):
    """调用研究员模型，并返回更新后的消息列表。"""
    pulled_prompt = client.pull_prompt("my-search-prompt")
    formatted_messages = pulled_prompt.invoke({"input": state["messages"][-1].content})
    try:
        response = researcher_model.invoke(formatted_messages)
    except BadRequestError as e:
        return {"messages": [AIMessage(content=f"研究员请求被拦截: {e}")]}
    return {"messages": [response]}


# 定于研究员子图
researcher_graph = StateGraph(MessagesState)
researcher_graph.add_node("researcher_agent", researcher_node)
researcher_graph.add_node("researcher_tools", researcher_tool_node)

# 定于研究员子图的边
researcher_graph.add_edge(START, "researcher_agent")
researcher_graph.add_conditional_edges(
    "researcher_agent",
    tools_condition,  # LangGraph 内置：检测消息中是否有 tool_calls
    {
        "tools": "researcher_tools",
        END: END,
    },
)
# 工具执行完后回到 agent 继续对话
researcher_graph.add_edge("researcher_tools", "researcher_agent")

# 编译研究员子图
researcher_subgraph = researcher_graph.compile(checkpointer=InMemorySaver())


## 第二步 定义画图专家 agent
# 定义画图tool
@tool
def python_repl(
    code: Annotated[str, "The python code to execute to generate your chart."],
):
    """Use this to execute python code. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""
    try:
        result = repl.run(code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"

    result_str = f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"

    return (
        result_str + "\n\nIf you have completed all tasks, respond with FINAL ANSWER."
    )


# 创建search 大模型
chart_llm = create_llm(0)
# 画图专用工具: python repl
chart_tools = [python_repl]
chart_tool_node = ToolNode(chart_tools)
# 绑定工具给模型
chart_model = chart_llm.bind_tools(chart_tools)


# 定义画图专家节点的函数
def chart_node(state: MessagesState):
    """调用画图专家模型，并返回更新后的消息列表。"""
    pulled_prompt = client.pull_prompt("my-chart-prompt")
    system_messages = pulled_prompt.format_messages()

    # 清理消息：只保留 chart agent 自己的 python_repl tool_calls，
    # 移除 researcher 的 tavily tool_calls，避免模型模仿调用不存在的工具
    cleaned_messages = []
    chart_tool_call_ids = set()  # 收集 chart 自己的 tool_call_id
    for msg in state["messages"]:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            chart_calls = [
                tc for tc in msg.tool_calls if tc.get("name") == "python_repl"
            ]
            if chart_calls:
                cleaned_messages.append(
                    AIMessage(content=msg.content, tool_calls=chart_calls)
                )
                for tc in chart_calls:
                    if tc.get("id"):
                        chart_tool_call_ids.add(tc["id"])
            else:
                # 非 chart 的 tool_calls（如 tavily）→ 当成普通文本
                cleaned_messages.append(AIMessage(content=msg.content))
        elif isinstance(msg, ToolMessage):
            # 只保留 chart agent 自己的 ToolMessage
            if msg.tool_call_id in chart_tool_call_ids:
                cleaned_messages.append(msg)
        else:
            cleaned_messages.append(msg)

    # 截取最近消息，确保第一条不是 ToolMessage
    max_count = 8
    if len(cleaned_messages) <= max_count:
        recent = cleaned_messages
    else:
        recent = cleaned_messages[-max_count:]
        while recent and isinstance(recent[0], ToolMessage):
            max_count += 1
            if max_count > len(cleaned_messages):
                recent = cleaned_messages
                break
            recent = cleaned_messages[-max_count:]

    formatted_messages = system_messages + list(recent)
    try:
        response = chart_model.invoke(formatted_messages)
    except BadRequestError as e:
        return {"messages": [AIMessage(content=f"画图专家请求被拦截: {e}")]}
    return {"messages": [response]}


# 构建子图
chart_graph = StateGraph(MessagesState)
chart_graph.add_node("chart_agent", chart_node)
chart_graph.add_node("chart_tools", chart_tool_node)
chart_graph.add_edge(START, "chart_agent")
chart_graph.add_conditional_edges(
    "chart_agent",
    tools_condition,
    {
        "tools": "chart_tools",
        END: END,
    },
)
chart_graph.add_edge("chart_tools", "chart_agent")
chart_subgraph = chart_graph.compile(checkpointer=InMemorySaver())


# 🧠 第三步：构建主图（Supervisor 架构）
class MultiAgentState(TypedDict):
    messages: Annotated[List, add_messages]
    next_agent: Literal["researcher", "chart", "FINISH"]


# 路由函数
def route_supervisor(
    state: MultiAgentState,
) -> Literal["researcher", "chart", "FINISH"]:
    return state["next_agent"]


# 创建supervisor 大模型
supervisor_llm = create_llm(0)


def supervisor_node(state: MultiAgentState):
    """监督者节点：决定下一步调用哪个子图。"""
    # 1. 获取对话历史并格式化为字符串
    messages = state["messages"]
    # 将消息列表转换为人类可读的文本
    history_lines = []
    for msg in messages:
        if hasattr(msg, "name") and msg.name:
            role = msg.name
        else:
            role = msg.type  # 可能是 'human', 'ai', 'tool' 等
        content = msg.content
        history_lines.append(f"{role}: {content}")
    history_text = "\n".join(history_lines)

    # 2. 从 LangSmith 拉取提示词模板
    prompt_template = client.pull_prompt("my-supervisor-prompt")

    # 3. 填充占位符 {messages}
    formatted_messages = prompt_template.invoke({"messages": history_text})

    # 4. 调用模型（不绑定工具，只需文本输出）
    try:
        response = supervisor_llm.invoke(formatted_messages)
    except BadRequestError as e:
        return {
            "next_agent": "FINISH",
            "messages": [AIMessage(content=f"监督者请求被拦截: {e}")],
        }
    decision = response.content.strip().lower()

    # 5. 解析决策（精确匹配，避免 "researcher" 误匹配包含该词的长文本）
    print(f"[Supervisor 决策]: {decision}")  # 调试用，可看到每次路由结果
    if decision == "researcher":
        return {"next_agent": "researcher"}
    elif decision == "chart":
        return {"next_agent": "chart"}
    elif decision == "finish":
        return {"next_agent": "FINISH"}
    # 兼容模型输出额外内容的情况：取第一行第一个词
    first_word = decision.split()[0] if decision else ""
    if first_word == "researcher":
        return {"next_agent": "researcher"}
    elif first_word == "chart":
        return {"next_agent": "chart"}
    else:
        return {"next_agent": "FINISH"}


# 构建主图
main_graph = StateGraph(MultiAgentState)

main_graph.add_node("supervisor", supervisor_node)
main_graph.add_node("researcher_subgraph", researcher_subgraph)
main_graph.add_node("chart_subgraph", chart_subgraph)

main_graph.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "researcher": "researcher_subgraph",
        "chart": "chart_subgraph",
        "FINISH": END,
    },
)
# 子图执行后回到 supervisor
main_graph.add_edge("researcher_subgraph", "supervisor")
main_graph.add_edge("chart_subgraph", "supervisor")
main_graph.set_entry_point("supervisor")

memory = InMemorySaver()
app = main_graph.compile(checkpointer=memory)

# 画图
# 1. 获取 PNG 二进制数据
img_data = app.get_graph().draw_png()

# 2. 写入文件
with open("multi.png", "wb") as f:
    f.write(img_data)

print("图片已保存为 multi.png")

# 3. 通过 thread_id 保持会话，并设置递归限制
config = {"configurable": {"thread_id": "user-123"}, "recursion_limit": 80}


# 执行
events = app.stream(
    {
        "messages": [
            HumanMessage(
                content="获取中国成都市的2026年端午期间的机场的出行情况,然后用Python绘制折线图。生成图表后完成任务"
            )
        ],
        "next_agent": "",
    },
    config=config,
    stream_mode="values",
)

for event in events:
    if "messages" in event:
        event["messages"][-1].pretty_print()  # 打印消息内容
