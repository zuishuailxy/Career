from utils import create_llm
import pandas as pd
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

llm = create_llm()


# 定义我们想要接收的数据格式
class FlowerDescription(BaseModel):
    flower_type: str = Field(description="鲜花的种类")
    price: int = Field(description="鲜花的价格")
    description: str = Field(description="鲜花的描述文案")
    reason: str = Field(description="为什么要这样写这个文案")


structured_model = llm.with_structured_output(FlowerDescription)

# 3. 构建提示模板（聊天格式）
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一位专业的鲜花店文案撰写员。"),
        ("human", "请为售价 {price} 元的 {flower} 写一段吸引人的描述，并说明理由。"),
    ]
)

# 4. 构建 LCEL 链
chain = prompt | structured_model


# 数据准备
flowers = ["玫瑰", "百合", "康乃馨"]
prices = ["50", "30", "20"]
df = pd.DataFrame(columns=["flower_type", "price", "description", "reason"])

# 6. 循环调用（每条数据单独调用，也可以批量）
for flower, price in zip(flowers, prices):
    result = chain.invoke({"flower": flower, "price": price})
    # result 已经是 FlowerDescription 对象，可以直接转为字典
    df.loc[len(df)] = {
        "flower": flower,
        "price": price,
        "description": result.description,
        "reason": result.reason,
    }

print(df.to_dict(orient="records"))
