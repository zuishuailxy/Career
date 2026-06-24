from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

prompt_template = """您是一位专业的鲜花店文案撰写员。
对于售价为 {price} 元的 {flower_name} ，您能提供一个吸引人的简短描述吗？{format_instructions}
"""
# prompt = PromptTemplate.from_template(template)


# 推荐使用 deepseek-chat 模型，它功能最完整[reference:9]
llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.7,  # 控制随机性，范围 0-1[reference:10]
    max_tokens=None,  # 最大生成 token 数[reference:11]
    timeout=None,  # 请求超时时间[reference:12]
    max_retries=2,  # 最大重试次数[reference:13]
)


# 1. 用 Pydantic 定义数据结构（替代 ResponseSchema）
class FlowerDescription(BaseModel):
    description: str = Field(description="鲜花的描述文案")
    reason: str = Field(description="为什么要这样写这个文案")


# # 创建输出解析器
# output_parser = JsonOutputParser(pydantic_object=FlowerDescription)


# # 获取格式指示
# format_instructions = output_parser.get_format_instructions()
# # 根据模板创建提示，同时在提示中加入输出解析器的说明
# prompt = PromptTemplate.from_template(
#     prompt_template, partial_variables={"format_instructions": format_instructions}
# )

# 方案二：使用模型原生结构化输出（最推荐，无需解析器）
structured_llm = llm.with_structured_output(FlowerDescription)
prompt_template2 = """您是一位专业的鲜花店文案撰写员。
对于售价为 {price} 元的 {flower_name} ，您能提供一个吸引人的简短描述吗？
"""
# 数据准备
flowers = ["玫瑰", "百合", "康乃馨"]
prices = ["50", "30", "20"]

for flower, price in zip(flowers, prices):
    # 根据提示准备模型的输入
    input = prompt_template2.format(flower_name=flower, price=price)

    # 获取模型的输出
    output = structured_llm.invoke(input)
    # print(output)

    # 解析模型的输出（这是一个字典结构）
    # parsed_output = output_parser.parse(output.content)

    print(output)
