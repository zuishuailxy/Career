from dotenv import load_dotenv
import os
import re
import logging
from dataclasses import dataclass, field
from typing import Literal, Annotated, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from utils import create_llm
from langchain_tavily import TavilySearch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, trim_messages
from langchain.tools import tool
from langchain_experimental.utilities import PythonREPL
from langsmith import Client
from langgraph.checkpoint.memory import InMemorySaver
from openai import BadRequestError

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
logger = logging.getLogger("multi-agent")


# ========== 集中配置 ==========
@dataclass
class AgentCfg:
    """单个 Agent 的配置"""

    name: str
    prompt_id: str  # LangSmith prompt 名称
    temperature: float = 0.7
    max_truncate_tokens: int = 2000  # 传入 LLM 的消息 token 上限


@dataclass
class AppConfig:
    """全局应用配置"""

    # ---- LangSmith ----
    langsmith_project: str = "graph"

    # ---- Graph ----
    recursion_limit: int = 80
    graph_image_path: str = "multi.png"
    thread_id: str = "user-123"

    # ---- Agent 配置 ----
    researcher: AgentCfg = field(
        default_factory=lambda: AgentCfg(
            name="researcher",
            prompt_id="my-search-prompt",
            temperature=0.7,
            max_truncate_tokens=2000,
        )
    )
    chart: AgentCfg = field(
        default_factory=lambda: AgentCfg(
            name="chart",
            prompt_id="my-chart-prompt",
            temperature=0,
            max_truncate_tokens=2000,
        )
    )
    supervisor: AgentCfg = field(
        default_factory=lambda: AgentCfg(
            name="supervisor",
            prompt_id="my-supervisor-prompt",
            temperature=0,
        )
    )

    # ---- Tavily 搜索 ----
    tavily_max_results: int = 2
    tavily_search_depth: str = "basic"
    tavily_include_answer: bool = False
    tavily_include_raw_content: bool = False

    # ---- 反循环 ----
    loop_detection_threshold: int = 3  # 连续同 agent 次数阈值


cfg = AppConfig()

# ---- LangSmith 环境变量 ----
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = cfg.langsmith_project
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "")
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")

client = Client()
# 初始化 Tavily 搜索工具
tavily_tool = TavilySearch(
    max_results=cfg.tavily_max_results,
    topic="general",
    search_depth=cfg.tavily_search_depth,
    include_answer=cfg.tavily_include_answer,
    include_raw_content=cfg.tavily_include_raw_content,
)

# Python REPL 工具，用于执行 Python 代码
repl = PythonREPL()


# ========== 公共工具函数 ==========
def clean_messages(messages: list, keep_tool_names: set[str]) -> list:
    """清理消息：只保留指定 tool 的 tool_calls/ToolMessage，其余转纯文本。

    防止 agent 看到历史中其他 agent 的 tool_calls 后模仿调用不存在的工具。
    """
    cleaned = []
    kept_ids: set[str] = set()
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            my_calls = [
                tc for tc in msg.tool_calls if tc.get("name") in keep_tool_names
            ]
            if my_calls:
                cleaned.append(AIMessage(content=msg.content, tool_calls=my_calls))
                for tc in my_calls:
                    if tc.get("id"):
                        kept_ids.add(tc["id"])
            else:
                cleaned.append(AIMessage(content=msg.content))
        elif isinstance(msg, ToolMessage):
            if msg.tool_call_id in kept_ids:
                cleaned.append(msg)
        else:
            cleaned.append(msg)
    return cleaned


def smart_truncate(messages: list, max_tokens: int = 2000) -> list:
    """基于 token 估算动态截断，确保 tool_call/ToolMessage 成对。

    用字符数 len() 作为 token 近似（中文 ~1 token/char，英文 ~0.25 token/char），
    生产环境可替换为 tiktoken。
    """
    if len(messages) <= 3:
        return messages
    trimmed = trim_messages(
        messages,
        max_tokens=max_tokens,  # token 预算，留给 system prompt + LLM 回复空间
        token_counter=len,  # 字符数近似（生产可换 tiktoken）
        strategy="last",  # 保留最新的消息
        allow_partial=False,  # 不打断 tool_call/ToolMessage 对
        start_on="human",  # 从 human 消息起始
    )
    # 兜底：至少保留最后一条
    return trimmed if trimmed else messages[-2:]


def create_agent_subgraph(
    agent_node,
    tools: list,
    agent_name: str,
) -> StateGraph:
    """工厂函数：创建 agent ↔ tools 循环的子图。"""
    graph = StateGraph(MessagesState)
    tool_node = ToolNode(tools)
    graph.add_node(f"{agent_name}_agent", agent_node)
    graph.add_node(f"{agent_name}_tools", tool_node)
    graph.add_edge(START, f"{agent_name}_agent")
    graph.add_conditional_edges(
        f"{agent_name}_agent",
        tools_condition,
        {"tools": f"{agent_name}_tools", END: END},
    )
    graph.add_edge(f"{agent_name}_tools", f"{agent_name}_agent")
    return graph.compile(checkpointer=InMemorySaver())


# 第一步 定义研究员的部分
search_llm = create_llm(cfg.researcher.temperature)
researcher_model = search_llm.bind_tools([tavily_tool])


# 定义研究员节点的函数
def researcher_node(state: MessagesState):
    """调用研究员模型，并返回更新后的消息列表。"""
    pulled_prompt = client.pull_prompt(cfg.researcher.prompt_id)
    formatted_messages = pulled_prompt.invoke({"input": state["messages"][-1].content})
    try:
        response = researcher_model.invoke(formatted_messages)
    except BadRequestError as e:
        return {"messages": [AIMessage(content=f"研究员请求被拦截: {e}")]}
    return {"messages": [response]}


researcher_subgraph = create_agent_subgraph(
    researcher_node, [tavily_tool], cfg.researcher.name
)


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


chart_llm = create_llm(cfg.chart.temperature)
chart_model = chart_llm.bind_tools([python_repl])


# 定义画图专家节点的函数
def chart_node(state: MessagesState):
    """调用画图专家模型，并返回更新后的消息列表。"""
    pulled_prompt = client.pull_prompt(cfg.chart.prompt_id)
    system_messages = pulled_prompt.format_messages()

    # 清理消息：移除 researcher 的 tavily tool_calls，只保留 chart 自己的 python_repl
    cleaned = clean_messages(state["messages"], {"python_repl"})
    recent = smart_truncate(cleaned, max_tokens=cfg.chart.max_truncate_tokens)
    formatted_messages = system_messages + list(recent)

    try:
        response = chart_model.invoke(formatted_messages)
    except BadRequestError as e:
        return {"messages": [AIMessage(content=f"画图专家请求被拦截: {e}")]}
    return {"messages": [response]}


chart_subgraph = create_agent_subgraph(chart_node, [python_repl], cfg.chart.name)


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
supervisor_llm = create_llm(cfg.supervisor.temperature)


def supervisor_node(state: MultiAgentState):
    """监督者节点：决定下一步调用哪个子图。"""
    # 1. 格式化对话历史
    messages = state["messages"]
    history_lines = []
    for msg in messages:
        if hasattr(msg, "name") and msg.name:
            role = msg.name
        else:
            role = msg.type
        history_lines.append(f"{role}: {msg.content}")
    history_text = "\n".join(history_lines)

    # 2. 拉取提示词并调用 LLM
    prompt_template = client.pull_prompt(cfg.supervisor.prompt_id)
    formatted_messages = prompt_template.invoke({"messages": history_text})

    try:
        response = supervisor_llm.invoke(formatted_messages)
    except BadRequestError as e:
        logger.warning("Supervisor 请求被拦截: %s", e)
        return {
            "next_agent": "FINISH",
            "messages": [AIMessage(content=f"监督者请求被拦截: {e}")],
        }

    decision = response.content.strip().lower()
    logger.info("Supervisor 决策: %s", decision)

    # 3. 正则提取 agent 名，防循环：连续同 agent ≥N 次则强制 FINISH
    match = re.search(r"\b(researcher|chart|finish)\b", decision)
    next_agent = match.group(1) if match else "finish"

    # 反循环计数器
    last_decisions = getattr(supervisor_node, "_last_decisions", [])
    last_decisions.append(next_agent)
    if len(last_decisions) > cfg.loop_detection_threshold:
        last_decisions.pop(0)
    supervisor_node._last_decisions = last_decisions

    if (
        len(last_decisions) >= cfg.loop_detection_threshold
        and len(set(last_decisions)) == 1
    ):
        logger.warning("检测到循环路由 %s，强制 FINISH", next_agent)
        return {"next_agent": "FINISH"}

    return {"next_agent": next_agent if next_agent != "finish" else "FINISH"}


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
with open(cfg.graph_image_path, "wb") as f:
    f.write(img_data)

logger.info("图片已保存为 %s", cfg.graph_image_path)

# 3. 通过 thread_id 保持会话，并设置递归限制
config = {
    "configurable": {"thread_id": cfg.thread_id},
    "recursion_limit": cfg.recursion_limit,
}


# 执行
events = app.stream(
    {
        "messages": [
            HumanMessage(
                content="获取中国2024-2026年成都市房价情况,然后用Python绘制折线图。生成图表后完成任务"
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
