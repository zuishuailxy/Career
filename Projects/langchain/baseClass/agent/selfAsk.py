"""
Self-Ask with Search 也是 LangChain 中的一个有用的代理类型（SELF_ASK_WITH_SEARCH）。它利用一种叫做 “Follow-up Question（追问）”加“Intermediate Answer（中间答案）”的技巧，来辅助大模型寻找事实性问题的过渡性答案，从而引出最终答案。
"""

import os
from dotenv import load_dotenv
from utils import create_llm
from langchain_community.utilities import SerpAPIWrapper
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

load_dotenv()
os.environ["SERPAPI_API_KEY"] = os.getenv("SERPAPI_API_KEY")
search_tool = SerpAPIWrapper()

llm = create_llm(0)


# 2. 定义Agent状态
class AgentState(TypedDict):
    """Agent的共享状态"""

    original_question: str  # 用户的原始复杂问题
    current_question: str  # 当前要搜索的子问题
    search_result: Optional[str]  # 最新一次搜索的结果
    intermediate_steps: list  # 存储所有(子问题, 答案)对
    final_answer: Optional[str]  # 最终答案


# 4. 定义节点函数

# ---- Self-Ask 核心流程 ----
# 1. decompose_node: LLM 将原始问题拆分为第一个子问题
# 2. search_node: 搜索子问题，获取中间答案
# 3. judge_node: LLM 评估中间答案，决定继续追问还是生成最终答案
#    追问 → 回到 search_node（循环）
#    最终答案 → 进入 answer_node
# 4. answer_node: 汇总所有中间答案，生成最终答案


def decompose_node(state: AgentState) -> dict:
    """
    Self-Ask 第一步：LLM 读取原始问题，拆解出第一个简单子问题。
    这是 Self-Ask 区别于普通搜索的关键 —— 不直接搜索原始复杂问题。
    """
    print(f"🧠 原始问题: {state['original_question']}")
    print("🔧 正在拆解问题...")

    prompt = f"""
你是一个擅长分解复杂问题的专家。你的任务是将用户的复杂问题拆解为更简单的子问题，逐步解决。

请阅读以下问题，并提出一个**简单、直接**的子问题，这个子问题的答案将帮助你逐步回答最终问题。

<最终问题>
{state['original_question']}
</最终问题>

你需要做的：
1. 思考：要回答最终问题，第一步需要知道什么？
2. 提出一个简单直接的子问题（能够通过一次搜索直接得到答案的问题）

请只回复子问题本身，不要加任何前缀或解释。例如：
- 如果最终问题是"2023年美网冠军的家乡是哪里？"
- 你应该回复："2023年美国网球公开赛男子单打冠军是谁？"
"""
    first_question = llm.invoke(prompt).content.strip()
    print(f"📌 第一个子问题: {first_question}")
    return {"current_question": first_question}


def search_node(state: AgentState) -> dict:
    """搜索节点：对当前子问题执行搜索"""
    question = state["current_question"]
    print(f"🔍 正在搜索: {question}")
    try:
        result = search_tool.run(question)
    except Exception as e:
        result = f"搜索出错: {str(e)}"
    print(f"📄 搜索结果预览: {result[:150]}...")
    return {"search_result": result}


def judge_node(state: AgentState) -> dict:
    """
    Self-Ask 核心判断节点：拿到搜索结果后，LLM 决定：
    - 追问（Follow-up）：还需要更多信息 → 生成下一个子问题
    - 最终答案（Final Answer）：信息足够 → 给出最终答案
    """
    print("🧐 正在评估：信息是否足够回答最终问题？")

    # 构建中间步骤的历史记录
    steps_text = ""
    for i, (q, a) in enumerate(state["intermediate_steps"], 1):
        steps_text += f"\n第{i}步 - 子问题: {q}\n第{i}步 - 答案: {a[:200]}...\n"

    prompt = f"""
你是一个擅长分解问题的专家，使用 Self-Ask（自我提问）方法逐步回答复杂问题。

<最终问题>
{state['original_question']}
</最终问题>

<已完成的步骤>
{steps_text if steps_text else "（尚无已完成的步骤）"}
</已完成的步骤>

<当前子问题>
{state['current_question']}
</当前子问题>

<当前搜索结果>
{state['search_result'][:500]}
</当前搜索结果>

请根据以上所有信息，判断下一步行动。你必须严格按照以下两种格式之一回复：

格式1 - 如果你现在**已经可以回答最终问题**：
最终答案: [你的答案]

格式2 - 如果还**需要更多信息**，请提出一个具体的新子问题：
追问: [新的子问题]

重要规则：
- "追问"必须比上一个子问题更进一步，是基于已有答案的自然延续
- 子问题必须简洁、可以通过一次搜索直接回答
- 不要重复已经问过的子问题
- 当所有必要信息都已获取时，及时给出"最终答案"
"""
    response = llm.invoke(prompt).content
    print(f"🤖 LLM 判断:\n{response}")

    # 解析 LLM 回复
    if response.strip().startswith("最终答案:"):
        final_answer = response.replace("最终答案:", "", 1).strip()
        # 保存最后一步中间结果
        new_steps = state["intermediate_steps"] + [
            (state["current_question"], state["search_result"])
        ]
        return {
            "final_answer": final_answer,
            "intermediate_steps": new_steps,
        }
    elif response.strip().startswith("追问:"):
        next_question = response.replace("追问:", "", 1).strip()
        new_steps = state["intermediate_steps"] + [
            (state["current_question"], state["search_result"])
        ]
        print(f"📌 下一个子问题: {next_question}")
        return {
            "current_question": next_question,
            "intermediate_steps": new_steps,
        }
    else:
        # 容错：尝试从回复中提取有用信息
        print("⚠️ LLM 输出格式不符合预期，尝试作为最终答案处理。")
        return {"final_answer": response.strip()}


def answer_node(state: AgentState) -> dict:
    """最终答案节点：汇总所有中间步骤，生成完整答案"""
    print("📝 正在生成最终答案...")

    # 如果 judge_node 已经给出了最终答案，直接使用
    if state.get("final_answer"):
        return {}

    # 否则让 LLM 基于所有中间步骤汇总
    steps_text = ""
    for i, (q, a) in enumerate(state["intermediate_steps"], 1):
        steps_text += f"\n步骤{i}: 问「{q}」→ 答「{a[:200]}...」\n"

    prompt = f"""
根据以下逐步推理过程，回答最终问题。

<最终问题>
{state['original_question']}
</最终问题>

<推理过程>
{steps_text}
</推理过程>

请给出一个简洁、准确的最终答案。
"""
    final_answer = llm.invoke(prompt).content
    return {"final_answer": final_answer}


# 5. 构建并编译工作流
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("decompose", decompose_node)
workflow.add_node("search", search_node)
workflow.add_node("judge", judge_node)
workflow.add_node("answer", answer_node)

# 设置 Self-Ask 流程的边
# decompose → search → judge → search（循环追问）/ answer（得出答案）→ END
workflow.set_entry_point("decompose")
workflow.add_edge("decompose", "search")
workflow.add_edge("search", "judge")
workflow.add_conditional_edges(
    "judge",
    lambda state: "answer" if state.get("final_answer") is not None else "search",
    {"search": "search", "answer": "answer"},
)
workflow.add_edge("answer", END)

# 编译应用
app = workflow.compile()

# 6. 运行Agent
if __name__ == "__main__":
    # 初始化状态
    initial_state = {
        "original_question": "西游记中孙悟空的第一任师傅的师傅是谁?",
        "current_question": "",
        "search_result": None,
        "intermediate_steps": [],
        "final_answer": None,
    }

    print("🚀 启动 Self-Ask Agent...")
    final_state = app.invoke(initial_state)
    print("\n" + "=" * 50)
    print(f"✅ 最终答案: {final_state['final_answer']}")
    print("=" * 50)
