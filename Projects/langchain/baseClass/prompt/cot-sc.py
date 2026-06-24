from langchain_core.prompts import ChatPromptTemplate
from collections import Counter
import re
from utils import create_llm

# 1. 定义 CoT 提示模板
cot_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一个善于逐步推理的助手。请一步一步地分析问题，并给出最终答案。",
        ),
        ("human", "问题：{question}\n让我们一步一步地思考："),
    ]
)

llm = create_llm()
# 3. 构建单次调用的链
chain = cot_prompt | llm


def extract_answer(text: str) -> str:
    """
    从模型的推理文本中提取最终答案。
    假设模型最终输出格式为 "答案：xxx" 或 "最终答案：xxx"
    """
    # 尝试匹配常见的答案标记
    patterns = [
        r"答案[：:]\s*(.+)",
        r"最终答案[：:]\s*(.+)",
        r"因此，答案是\s*(.+)",
        r"结果为\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    # 如果没有标记，则返回最后一行（回退方案）
    return text.strip().split("\n")[-1]


def cot_sc_invoke(question: str, n: int = 5) -> str:
    """执行 CoT-SC：多次采样并投票"""
    answers = []
    for i in range(n):
        response = chain.invoke({"question": question})
        full_text = response.content
        # 可以打印中间过程查看（可选）
        print(f"--- 采样 {i+1} ---\n{full_text}\n")

        final_answer = extract_answer(full_text)
        answers.append(final_answer)

    # 统计投票结果
    vote_counter = Counter(answers)
    most_common_answer = vote_counter.most_common(1)[0][0]

    print(f"各采样答案分布: {vote_counter}")
    return most_common_answer


# 4. 测试
if __name__ == "__main__":
    question = "若函数y=(x)的定义域和值域分别为A={1,2,3)和B={1,2}，则组成函数的个数是?"
    final = cot_sc_invoke(question, n=5)
    print(f"\n最终投票结果: {final}")
