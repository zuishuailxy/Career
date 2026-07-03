from utils import create_llm
import pandas as pd
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

llm = create_llm()
df = pd.DataFrame(columns=["flower_type", "price", "description", "reason"])

# 数据准备
flowers = ["玫瑰", "百合", "康乃馨"]
prices = ["50", "30", "20"]


# 定义我们想要接收的数据格式
class FlowerDescription(BaseModel):
    flower_type: str = Field(description="鲜花的种类")
    price: int = Field(description="鲜花的价格")
    description: str = Field(description="鲜花的描述文案")
    reason: str = Field(description="为什么要这样写这个文案")


# ------Part 3
# 创建输出解析器
output_parser = PydanticOutputParser(pydantic_object=FlowerDescription)

# 获取输出格式指示
format_instructions = output_parser.get_format_instructions()
# 打印提示
print("输出格式：", format_instructions)


# ------Part 4
# 创建提示模板
prompt_template = """您是一位专业的鲜花店文案撰写员。
对于售价为 {price} 元的 {flower} ，您能提供一个吸引人的简短中文描述吗？
{format_instructions}"""

# 根据模板创建提示，同时在提示中加入输出解析器的说明
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "您是一位专业的鲜花店文案撰写员。对于售价为 {price} 元的 {flower} ，您能提供一个吸引人的简短中文描述吗？\n{format_instructions}",
        ),
        ("human", "{price} {flower}"),
    ]
).partial(format_instructions=format_instructions)


# 使用 LCEL 构建链，最后一步是 parser
chain = prompt | llm | output_parser

for flower, price in zip(flowers, prices):
    # 获取模型的输出
    result = chain.invoke({"flower": flower, "price": price})
    df.loc[len(df)] = {
        "flower": flower,
        "price": price,
        "description": result.description,
        "reason": result.reason,
    }

# 打印字典
print("输出的数据：", df.to_dict(orient="records"))
