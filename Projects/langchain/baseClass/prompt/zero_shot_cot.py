from langchain_core.prompts import ChatPromptTemplate
from utils import create_llm

llm = create_llm()
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

# 2. 构建链
chain = cot_prompt | llm

# 3. 调用
response = chain.invoke(
    {
        "question": "若函数y=(x)的定义域和值域分别为A={1,2,3)和B={1,2}，则组成函数的个数是?"
    }
)
print(response.content)
