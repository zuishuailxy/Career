from utils.models import create_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List


# 定义一个名为TextParsing的模型，描述了如何解析大V信息
class TextParsing(BaseModel):
    summary: str = Field(description="大V个人简介")  # 大V的简介或背景信息
    facts: List[str] = Field(description="大V的特点")  # 大V的一些显著特点或者事实
    interest: List[str] = Field(
        description="这个大V可能感兴趣的事情"
    )  # 大V可能感兴趣的主题或活动
    letter: List[str] = Field(
        description="一篇联络这个大V的邮件"
    )  # 联络大V的建议邮件内容


# 生成文案的函数
def generate_letter(information):
    # 设计提示模板
    letter_template = """
          下面是这个人的微博信息 {information}
          请你帮我:
          1. 写一个简单的总结
          2. 挑两件有趣的事情说一说
          3. 找一些他比较感兴趣的事情
          4. 写一篇热情洋溢的介绍信
          """

    prompt_template = ChatPromptTemplate.from_template(letter_template)

    # 初始化大模型
    llm = create_llm()

    # 初始化链
    chain = prompt_template | llm.with_structured_output(TextParsing)

    # 生成文案
    result = chain.invoke({"information": information})

    return result
