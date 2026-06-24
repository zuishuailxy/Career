from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from utils import create_llm

llm = create_llm()
# 1. 定义示例
examples = [
    {
        "question": "小明有 5 个苹果，小红给了他 3 个，小明现在有几个？",
        "answer": "推理：5 + 3 = 8\n答案：8 个",
    },
    {
        "question": "一个班级有 20 个学生，其中 1/4 是女生，男生有多少人？",
        "answer": "推理：20 × 1/4 = 5 人，20 - 5 = 15 人\n答案：15 人",
    },
]

# 2. 创建示例格式化模板
example_prompt = PromptTemplate.from_template("问题：{question}\n{answer}")

# 3. 创建 FewShotPromptTemplate
few_shot_cot = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix="请按照以下示例的方式，一步步推理并回答问题。",
    suffix="问题：{question}\n",
    input_variables=["question"],
)

llm = create_llm()
chain = few_shot_cot | llm

response = chain.invoke(
    {
        "question": "若函数y=(x)的定义域和值域分别为A={1,2,3)和B={1,2}，则组成函数的个数是?",
    }
)

print(response.content)
