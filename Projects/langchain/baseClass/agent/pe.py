"""
下面是一个基于 LangGraph 构建的 Plan-and-Execute Agent 完整代码示例。

这个 Agent 会针对一个复杂问题（例如“撰写一份关于人工智能在医疗领域应用的简短报告”），先由“规划器”生成一个分步计划，再由“执行器”逐步执行，最终汇总结果。
"""

import operator
from typing import TypedDict, Annotated, List, Literal
from langgraph.graph import StateGraph, END
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from utils import create_llm

llm = create_llm()
# 使用 DuckDuckGo 作为免费搜索工具（无需 API Key）
search = DuckDuckGoSearchRun(api_wrapper=DuckDuckGoSearchAPIWrapper())


# 2. 定义 Agent 状态
class PlanExecuteState(TypedDict):
    input: str  # 用户原始输入
    plan: List[str]  # 任务计划（步骤列表）
    past_steps: Annotated[List[tuple], operator.add]  # 已执行步骤及结果
    response: str  # 最终响应


# 3. 规划器节点 (Planner)
def planner(state: PlanExecuteState):
    """根据用户输入生成执行计划"""
    prompt = f"""
你是一个任务规划专家。请为以下任务制定一个详细的、可执行的步骤计划。

任务：{state['input']}

要求：
1. 将任务分解为 3-5 个清晰的步骤
2. 每个步骤应该是独立的、可执行的动作
3. 只返回步骤列表，每行一个步骤，使用数字编号

示例输出：
1. 搜索关于人工智能在医疗领域应用的最新信息
2. 整理搜索结果，提取关键应用场景
3. 撰写一份包含引言、主体和结论的简短报告
"""
    response = llm.invoke(prompt)
    # 解析计划
    plan_lines = [line.strip() for line in response.content.split("\n") if line.strip()]
    plan = [line for line in plan_lines if line[0].isdigit()]
    return {"plan": plan}


# 4. 执行器节点 (Executor)
def executor(state: PlanExecuteState):
    """执行计划中的下一个步骤（按索引顺序执行，避免字符串匹配问题）"""
    plan = state["plan"]
    past_steps = state.get("past_steps", [])

    # 已执行的步骤数 = 下一个要执行的步骤索引
    step_index = len(past_steps)

    if step_index >= len(plan):
        return {"response": "所有步骤已执行完成。"}

    next_step = plan[step_index]
    print(f"🔧 正在执行第{step_index + 1}步: {next_step}")
    try:
        result = search.run(next_step)
    except Exception as e:
        result = f"执行出错: {str(e)}"

    return {"past_steps": [(next_step, result)]}


# 5. 判断节点 (Should Continue)
def should_continue(state: PlanExecuteState) -> Literal["executor", "responder"]:
    """判断是否还有未执行的步骤"""
    plan = state["plan"]
    past_steps = state.get("past_steps", [])

    if len(past_steps) >= len(plan):
        return "responder"
    return "executor"


# 6. 响应生成器节点 (Responder)
def responder(state: PlanExecuteState):
    """汇总所有执行结果，生成最终响应"""
    past_steps = state.get("past_steps", [])

    if not past_steps:
        return {"response": "无法生成响应，因为没有执行任何步骤。"}

    # 构建汇总提示
    context = "\n".join(
        [f"步骤: {step}\n结果: {result}" for step, result in past_steps]
    )
    prompt = f"""
根据以下步骤执行结果，回答用户的原始问题。

原始问题：{state['input']}

执行记录：
{context}

请生成一个完整、连贯的最终回答。
"""
    response = llm.invoke(prompt)
    return {"response": response.content}


# 7. 构建工作流
workflow = StateGraph(PlanExecuteState)
# 添加节点
workflow.add_node("planner", planner)
workflow.add_node("executor", executor)
workflow.add_node("responder", responder)

# 设置入口
workflow.set_entry_point("planner")
# 添加边
workflow.add_edge("planner", "executor")
workflow.add_conditional_edges(
    "executor",
    should_continue,
    {
        "executor": "executor",  # 继续执行下一步
        "responder": "responder",  # 所有步骤完成，生成响应
    },
)
workflow.add_edge("responder", END)
# 编译应用
app = workflow.compile()

# 8. 运行 Agent
if __name__ == "__main__":
    inputs = {"input": "撰写一份关于人工智能在医疗领域应用的简短报告"}
    final_state = app.invoke(inputs)
    print("\n" + "=" * 50)
    print("📝 最终报告:")
    print(final_state["response"])
    print("=" * 50)
