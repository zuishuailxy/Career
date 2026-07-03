"""
基于 LCEL（LangChain 表达式语言）和模型的结构化输出（Structured Output）功能，构建一个智能路由系统
"""

from utils import create_llm
from operator import itemgetter
from typing import Literal
from typing_extensions import TypedDict
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.tracers.stdout import ConsoleCallbackHandler

model = create_llm()
# 构建两个场景的模板
flower_care_template = """
你是一个经验丰富的园丁，擅长解答关于养花育花的问题。回复的第一句必须先自己介绍。
下面是需要你来回答的问题:
"""

flower_deco_template = """
你是一位网红插花大师，擅长解答关于鲜花装饰的问题。回复的第一句必须先自己介绍。
下面是需要你来回答的问题:
"""


flower_care_chain = (
    ChatPromptTemplate.from_messages(
        [("system", flower_care_template), ("human", "{query}")]
    )
    | model
    | StrOutputParser()
)
flower_deco_chain = (
    ChatPromptTemplate.from_messages(
        [("system", flower_deco_template), ("human", "{query}")]
    )
    | model
    | StrOutputParser()
)

default_chain = (
    ChatPromptTemplate.from_messages(
        [("system", "你是令人开心的助手"), ("human", "{query}")]
    )
    | model
    | StrOutputParser()
)


# 3. 定义路由逻辑 (使用结构化输出)
class RouteQuery(TypedDict):
    """将查询路由到目标专家。"""

    destination: Literal["flower_care", "flower_deco", "default"]  # 限制目标


# 4. 构建专家映射字典（方便扩展）
expert_map = {
    "flower_care": flower_care_chain,
    "flower_deco": flower_deco_chain,
    "default": default_chain,
}


route_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Route the user's query to either the flower_care, flower_deco expert or default.",
        ),
        ("human", "{query}"),
    ]
)

# 核心路由链：生成结构化输出 -> 提取目标字段 "destination"
router = (
    route_prompt | model.with_structured_output(RouteQuery) | itemgetter("destination")
)

# 4. 组合成完整链
full_chain = {
    "destination": router,  # 路由结果
    "query": lambda x: x["query"],  # 原样传递用户输入
} | RunnableLambda(lambda x: expert_map[x["destination"]])

# 测试1
# result = full_chain.invoke({"query": "如何为玫瑰浇水？"})
# print(result)
# 测试2
# print(full_chain.invoke({"query": "如何为婚礼场地装饰花朵？"}))
# 测试3
print(
    full_chain.invoke(
        {"query": "如何上北大"}, config={"callbacks": [ConsoleCallbackHandler()]}
    )
)
# full_chain.get_graph().print_ascii()

# 获取链中使用的所有提示词模板
# prompts = full_chain.get_prompts()
# print(prompts)
