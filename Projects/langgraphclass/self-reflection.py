from utils import create_llm
from dotenv import load_dotenv
import os
import logging
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from typing import Annotated  # 用于类型注解
from langgraph.graph import END, StateGraph, START  # 导入状态图的相关常量和类
from langgraph.graph.message import add_messages  # 用于在状态中处理消息
from typing_extensions import TypedDict  # 用于定义带有键值对的字典类型
from langgraph.checkpoint.memory import InMemorySaver
import re
import asyncio

load_dotenv()

# ---- LangSmith 环境变量 ----
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "self-reflection"
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
# os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "")
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
logger = logging.getLogger("self-reflection")


# 创建一个writer agent
writer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一名专业写作助手，根据用户要求创作文章。\n\n"
            "核心规则：\n"
            "1. 文章必须严格控制在 400 字左右（380-420 字），写完后在末尾标注字数。\n"
            "2. 结构清晰：开篇点题 → 主体论证/叙述 → 结尾升华。\n"
            "3. 语言生动，善用比喻和排比，让读者有代入感。\n"
            "4. 如果用户提供了修改意见，逐条对照修改，并在回复中说明改了什么。\n"
            "5. 如果老师反馈文章已合格无需修改，请**直接输出原文**（去掉修改说明和字数标注），不要写客套话。",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


write_model = create_llm(model="deepseek-v4-pro", temperature=1.2)
writer_agent = writer_prompt | write_model


# 反思结果的结构化输出
class ReflectionResult(BaseModel):
    """语文老师对文章的批改结果"""

    total_score: float = Field(ge=0, le=10, description="总分，满分 10 分")
    issues: list[str] = Field(
        description="仍需改进的具体问题；若无明显问题则返回空列表"
    )
    suggestions: list[str] = Field(
        description="2-3 条具体可操作的修改方向；若已合格则仅含「文章已合格，无需修改」"
    )
    passed: bool = Field(description="文章是否达到合格标准（8 分及以上）")


# 创建一个自我反思的 agent
reflection_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一名严格的语文老师，正在批改学生提交的文章。\n\n"
            "评分维度（满分 10 分，8 分以上为合格）：\n"
            "- 内容切题（3分）：是否紧扣主题，不跑题\n"
            "- 结构逻辑（3分）：开篇→主体→结尾是否完整，论证是否清晰\n"
            "- 语言表达（2分）：是否生动流畅，善用修辞\n"
            "- 字数控制（2分）：是否接近 400 字（380-420 字满分）\n\n"
            "评分标准：只有文章在各方面都基本达标时才给 8 分以上，不要轻易给高分。\n"
            "将 issues 逐条列出仍需改进之处；suggestions 给出 2-3 条可操作的修改方向。\n"
            "若已合格，issues 可为空，suggestions 仅写「文章已合格，无需修改」，passed 设为 true。",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

reflection_model = create_llm(model="deepseek-chat", temperature=0.2)
reflection_agent = reflection_prompt | reflection_model.with_structured_output(
    ReflectionResult
)


def _extract_latest_draft(messages: list) -> str:
    """从消息列表中提取最新一版 writer 生成的文章"""
    ai_messages = [
        msg for msg in messages if isinstance(msg, AIMessage) and msg.content
    ]
    if not ai_messages:
        return ""
    article = max(ai_messages, key=lambda m: len(m.content)).content
    return re.split(r"\n---", article)[0]


# 定义状态类，使用TypedDict以保存消息
class State(TypedDict):
    messages: Annotated[list, add_messages]
    round: int
    score: float  # 最新一轮的评分
    best_draft: str  # 历史最高分对应的文章
    best_score: float
    best_round: int


# 异步生成节点函数：生成内容（如作文）
async def generation_node(state: State) -> State:
    return {"messages": [await writer_agent.ainvoke(state["messages"])]}


def _format_reflection_feedback(result: ReflectionResult) -> str:
    """将结构化反思结果格式化为传给 writer 的文本"""
    issues_block = ""
    if result.issues:
        issues_block = "具体问题：\n" + "\n".join(
            f"- {issue}" for issue in result.issues
        )
        issues_block += "\n\n"

    suggestions_block = "\n".join(f"- {s}" for s in result.suggestions)
    return (
        f"【老师评分：{result.total_score}/10】\n"
        f"{issues_block}"
        f"修改意见如下，请对照修改：\n{suggestions_block}"
    )


# 异步反思节点函数：对生成的内容进行反思和反馈
async def reflection_node(state: State) -> State:
    cls_map = {"ai": HumanMessage, "human": AIMessage}
    translated = [state["messages"][0]] + [
        cls_map[msg.type](content=msg.content) for msg in state["messages"][1:]
    ]
    result: ReflectionResult = await reflection_agent.ainvoke(translated)

    parsed_score = result.total_score
    current_round = state.get("round", 0) + 1
    draft = _extract_latest_draft(state["messages"])

    best_score = state.get("best_score", 0)
    best_draft = state.get("best_draft", "")
    best_round = state.get("best_round", 0)
    if draft and (parsed_score >= best_score or not best_draft):
        best_draft = draft
        best_score = parsed_score
        best_round = current_round

    logger.info(
        "第 %d 轮反思，评分: %.1f/10，合格: %s",
        current_round,
        result.total_score,
        result.passed,
    )
    return {
        "messages": [HumanMessage(content=_format_reflection_feedback(result))],
        "round": current_round,
        "score": parsed_score,
        "best_draft": best_draft,
        "best_score": best_score,
        "best_round": best_round,
    }


# 保存节点：评分达标或达到最大轮次后将文章保存为 txt
def save_node(state: State) -> State:
    """达标时保存最新稿；未达标但达最大轮次时保存历史最高分版本"""
    passed = state.get("score", 0) >= PASS_SCORE

    if passed:
        article = _extract_latest_draft(state["messages"])
        save_round = state.get("round", 0)
        save_score = state.get("score", 0)
        status = "文章已达标"
    else:
        article = state.get("best_draft") or _extract_latest_draft(state["messages"])
        save_round = state.get("best_round", state.get("round", 0))
        save_score = state.get("best_score", 0)
        status = f"未达 {PASS_SCORE} 分标准，已保存历史最佳版本（第 {save_round} 轮）"

    filename = f"article_round{save_round}_score{save_score:.0f}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(article)

    logger.info("%s，已保存为 %s", status, filename)
    return {"messages": [AIMessage(content=f"✅ {status}，保存为 {filename}")]}


MAX_ROUND = 3
PASS_SCORE = 9  # 达到此分提前结束


def should_continue(state: State):
    if state.get("score", 0) >= PASS_SCORE:
        logger.info("评分 %.1f 达标（≥%d），保存并结束", state["score"], PASS_SCORE)
        return "save"
    if state.get("round", 0) >= MAX_ROUND:
        logger.info(
            "达到最大轮次 %d（最佳 %.1f 分），保存历史最佳版本",
            MAX_ROUND,
            state.get("best_score", 0),
        )
        return "save"
    return "reflect"


# 创建状态图，传入初始状态结构
builder = StateGraph(State)

# 在状态图中添加"writer"节点，节点负责生成内容
builder.add_node("writer", generation_node)

# 在状态图中添加"reflect"节点，节点负责生成反思反馈
builder.add_node("reflect", reflection_node)
builder.add_node("save", save_node)

builder.add_edge(START, "writer")

builder.add_conditional_edges(
    "writer",
    should_continue,
    {
        "reflect": "reflect",
        "save": "save",
        END: END,
    },
)

builder.add_edge("reflect", "writer")
builder.add_edge("save", END)

# 创建内存保存机制，允许在流程中保存中间状态和检查点
memory = InMemorySaver()

# 编译状态图，使用检查点机制
app = builder.compile(checkpointer=memory)

# 画图
# 1. 获取 PNG 二进制数据
img_data = app.get_graph().draw_png()

# 2. 写入文件
with open("reflection_graph.png", "wb") as f:
    f.write(img_data)

logger.info("图片已保存为 %s", "reflection_graph.png")


# 定义装饰器，记录函数调用次数
def track_steps(func):
    step_counter = {"count": 0}  # 用于记录调用次数

    def wrapper(event, *args, **kwargs):
        # 增加调用次数
        step_counter["count"] += 1
        # 在函数调用之前打印 step
        print(f"## Round {step_counter['count']}")
        # 调用原始函数
        return func(event, *args, **kwargs)

    return wrapper


# 使用装饰器装饰 pretty_print_event_markdown 函数
@track_steps
def pretty_print_event_markdown(event):
    # 如果是生成写作部分
    if "writer" in event:
        generate_md = "#### 写作生成:\n"
        for message in event["writer"]["messages"]:
            generate_md += f"- {message.content}\n"
        print(generate_md)

    # 如果是反思评论部分
    if "reflect" in event:
        reflect_md = "#### 评论反思:\n"
        for message in event["reflect"]["messages"]:
            reflect_md += f"- {message.content}\n"
        print(reflect_md)

    if "save" in event:
        print("#### ✅ 保存:\n" + event["save"]["messages"][0].content)


def run_self_reflection():

    inputs = {
        "messages": [
            HumanMessage(content="参考斗破苍穹的说话风格，写一篇奉劝讽刺中国足球的文章")
        ],
        "round": 0,
        "score": 0.0,
        "best_draft": "",
        "best_score": 0.0,
        "best_round": 0,
    }
    config = {"configurable": {"thread_id": "1"}}

    async def chat():
        async for event in app.astream(inputs, config):
            pretty_print_event_markdown(event)

    asyncio.run(chat())


if __name__ == "__main__":
    run_self_reflection()
