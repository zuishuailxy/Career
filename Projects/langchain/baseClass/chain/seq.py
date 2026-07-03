from utils import create_llm
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

model = create_llm()

# ---------- 定义三个独立的子链 ----------
# 1. 生成自我介绍（需要 name, color）
introduction_chain = (
    ChatPromptTemplate.from_messages(
        [
            (
                "user",
                "My name is {name}. My favorite color is {color}. Write a short introduction.",
            )
        ]
    )
    | model
    | StrOutputParser()
)

# 2. 对自我介绍进行评论（需要 introduction）
review_chain = (
    ChatPromptTemplate.from_messages(
        [
            (
                "user",
                "Here is an introduction: {introduction}. Write a review of the introduction.",
            )
        ]
    )
    | model
    | StrOutputParser()
)

# 3. 生成社交媒体帖子（需要 review）
social_post_chain = (
    ChatPromptTemplate.from_messages(
        [("user", "Based on this review: {review}, write a social media post.")]
    )
    | model
    | StrOutputParser()
)

# ---------- 组装成顺序管道 ----------
overall_chain = (
    RunnablePassthrough.assign(introduction=introduction_chain)  # 添加 introduction
    | RunnablePassthrough.assign(review=review_chain)  # 添加 review
    | RunnablePassthrough.assign(
        social_post_text=social_post_chain
    )  # 添加 social_post_text
)

# ---------- 调用 ----------
result = overall_chain.invoke({"name": "Alice", "color": "blue"})

# 结果包含所有字段
print(result["introduction"])
print(result["review"])
print(result["social_post_text"])
