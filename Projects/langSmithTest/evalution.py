from dotenv import load_dotenv
import os

from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langsmith.schemas import Example, Run
from langsmith.evaluation import evaluate

load_dotenv()

# ---- LangSmith 配置 ----
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "test"
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")

llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

prompt = ChatPromptTemplate.from_template("""
    请查看下面的用户查询，判断其中是否包含任何形式的有害行为，例如侮辱、威胁或高度负面的评论。
    如果有请回复"Toxic", 如果没有请回复"Not Toxic"
    {context}
""")

chain = prompt | llm | StrOutputParser()


# 目标函数：LangSmith 会用 dataset 中的每个 input 调用它
def target_fn(inputs: dict) -> dict:
    """接收 dataset 的一行数据，返回预测结果"""
    print(inputs)
    llm_result = chain.invoke({"context": inputs["text"]})
    return {"output": llm_result}


# 评估函数：比较预测结果和标注
def get_score(run: Run, example: Example) -> dict:
    # run.outputs 是 target_fn 返回的 dict
    # example.outputs 是 dataset 中的标注（label 列）
    predicted = run.outputs.get("output", "")
    expected = example.outputs.get("label", "")
    score = 1 if predicted == expected else 0
    return {"key": "accuracy", "score": score}


dataset_name = "Toxic Queries"

result = evaluate(
    target_fn,  # 目标函数
    data=dataset_name,  # 数据集名称
    evaluators=[get_score],  # 评估函数列表
    experiment_prefix="Toxic Queries",
    description="Testing the dataset",
)

print(result)
