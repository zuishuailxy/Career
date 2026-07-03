"""
用户提出一个话题，系统会先搜索相关信息，然后基于这些信息写一篇短文，最后对文章进行评分和润色建议。整个流程涉及多个步骤、条件分支和并行处理。
"""

from utils import create_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.runnables import (
    RunnableParallel,
    RunnableLambda,
    RunnableBranch,
    RunnablePassthrough,
)
from pydantic import BaseModel, Field
from typing import List

model = create_llm()


# ---------- 1. 定义数据模型 ----------
class ArticleReview(BaseModel):
    score: int = Field(description="文章质量评分，1-10分")
    feedback: str = Field(description="改进建议")
    strengths: List[str] = Field(description="文章的优点")


# ---------- 2. 初始化模型 ----------
model = create_llm()
structured_model = model.with_structured_output(ArticleReview)

# ---------- 3. 定义各个步骤的提示模板 ----------
# ---------- 定义额外信息的提示模板 ----------
extra_info_prompt = ChatPromptTemplate.from_template("""
请提供关于 "{topic}" 的历史背景信息，包括：
1. 重要里程碑
2. 关键人物
3. 对社会的影响（简短）
""")

# 步骤1：搜索/研究
research_prompt = ChatPromptTemplate.from_template("""
请提供关于 "{topic}" 的以下信息：
1. 核心定义
2. 3个关键事实
3. 一个相关的近期发展（2025-2026年）
请用简洁的要点形式输出。
""")

# 步骤2：写作
write_prompt_combined = ChatPromptTemplate.from_template("""
基于以下信息，写一篇150字左右的短文：

【研究信息】
{research}

【历史背景】
{extra_info}

要求：
- 标题要吸引人
- 结构清晰
- 语言生动
""")

# 步骤3：审查（将使用结构化输出）
review_prompt = ChatPromptTemplate.from_template("""
请对以下文章进行审查，给出评分、改进建议和优点：

文章标题：{title}
文章内容：
{content}
""")

# ---------- 4. 构建各个步骤的链 ----------
# ---------- 创建额外信息链 ----------
extra_info_chain = extra_info_prompt | model | StrOutputParser()
# 研究链
research_chain = research_prompt | model | StrOutputParser()

# 定义写作链（现在接受 research 和 extra_info）
write_combined_chain = write_prompt_combined | model | StrOutputParser()

# 审查链（使用结构化输出）
review_chain = review_prompt | structured_model


# ---------- 5. 组装完整的工作流 ----------
def extract_title(text):
    if hasattr(text, "content"):
        text = text.content
    if not text or not text.strip():
        return "未命名文章"
    return text.strip().split("\n")[0].strip()


# 5.1 使用 RunnableParallel 并行执行研究步骤
#  ---------- 并行执行两个任务 ----------
parallel_tasks = RunnableParallel(
    {
        "research": research_chain,
        # 可以添加更多并行的任务
        "extra_info": extra_info_chain,
    }
)


# 5.2 使用 RunnableLambda 执行自定义函数
extract_title_runnable = RunnableLambda(extract_title)


# 5.3 使用 RunnableBranch 实现条件分支
def should_skip_review(inputs: dict) -> bool:
    """根据条件决定是否跳过审查"""
    # 如果文章太短（少于50字），跳过审查
    return len(inputs.get("content", "")) < 50


branch_chain = RunnableBranch(
    (
        lambda x: should_skip_review(x),
        # 如果文章太短，直接返回一个默认的审查结果
        lambda x: {"score": 5, "feedback": "文章太短，建议扩充内容", "strengths": []},
    ),
    # 否则执行完整的审查链
    review_chain,
)


# 5.4 组装主链
main_chain = (
    # 第一步：传入主题并执行并行研究
    {"topic": lambda x: x["topic"]}
    | parallel_tasks  # 输出: {"research": "...", "extra_info": "..."}
    # 第二步：写文章，同时保留原有字段
    | RunnablePassthrough.assign(
        article=write_combined_chain  # 输入是 research 和 extra_info，输出文章字符串
    )  # 现在上下文包含 research, extra_info, article
    # 第三步：提取标题，并复制 article 为 content
    | RunnablePassthrough.assign(
        title=lambda x: extract_title(x["article"]),
        content=lambda x: x["article"],  # 复制 article 为 content，便于后续审查
    )  # 现在上下文包含 research, extra_info, article, title, content
    # 第四步：审查（可能跳过）
    | RunnablePassthrough.assign(
        review=lambda x: branch_chain.invoke(
            {"title": x["title"], "content": x["content"]}
        )
    )  # 现在上下文包含 research, extra_info, article, title, content, review
    # 第五步：最终输出
    | RunnableLambda(
        lambda x: {
            "article": x["content"],  # 原始文章
            "review": x["review"],  # 审查结果
            "extra_info": x["extra_info"],  # 历史背景
            "research": x["research"],  # 研究信息（可选）
        }
    )
)

# ---------- 6. 执行测试 ----------
if __name__ == "__main__":
    # 执行一次完整的调用
    result = main_chain.invoke({"topic": "AI领域的最新进展"})

    # 3. 输出原始文章和审查结果
    print("===== 原始文章 =====")
    print(result["article"])
    print("\n===== 审查结果 =====")
    print(f"评分：{result['review'].score}/10")
    print(f"优点：{', '.join(result['review'].strengths)}")
    print(f"改进建议：{result['review'].feedback}")
    print("历史背景：", result["extra_info"])
    print("research", result["research"])
