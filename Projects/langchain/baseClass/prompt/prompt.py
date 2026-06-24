from ..utils import create_llm
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    FewShotPromptTemplate,
    PromptTemplate,
    FewShotChatMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import HumanMessage, AIMessage

llm = create_llm()

# ChatPromptTemplate
# 1. 分别创建系统消息和用户消息的模板
system_template = SystemMessagePromptTemplate.from_template(
    "你是一位精通{field}的专家。"
)
human_template = HumanMessagePromptTemplate.from_template("请解释一下{concept}。")
prompt = ChatPromptTemplate.from_messages(
    [
        system_template,
        human_template,
    ]
)


# 使用 | 操作符构建链
chain = prompt | llm

# 调用链，传入参数
response = chain.invoke({"field": "物理", "concept": "力的三大定律"})

# print(response.content)  # 输出翻译结果


# few shot
# 1. 定义示例列表
samples = [
    {
        "flower_type": "玫瑰",
        "occasion": "爱情",
        "ad_copy": "玫瑰，浪漫的象征，是你向心爱的人表达爱意的最佳选择。",
    },
    {
        "flower_type": "康乃馨",
        "occasion": "母亲节",
        "ad_copy": "康乃馨代表着母爱的纯洁与伟大，是母亲节赠送给母亲的完美礼物。",
    },
    {
        "flower_type": "百合",
        "occasion": "庆祝",
        "ad_copy": "百合象征着纯洁与高雅，是你庆祝特殊时刻的理想选择。",
    },
    {
        "flower_type": "向日葵",
        "occasion": "鼓励",
        "ad_copy": "向日葵象征着坚韧和乐观，是你鼓励亲朋好友的最好方式。",
    },
]

# 2. 定义单个示例的格式化模板
example_prompt = PromptTemplate.from_template(
    "鲜花类型: {flower_type}\n场合: {occasion}\n文案: {ad_copy}"
)

# 3. 创建一个FewShotPromptTemplate对象
few_shot_prompt = FewShotPromptTemplate(
    examples=samples,
    example_prompt=example_prompt,
    suffix="鲜花类型: {flower_type}\n场合: {occasion}",
    input_variables=["flower_type", "occasion"],
)
# print(few_shot_prompt.format(flower_type="野玫瑰", occasion="爱情"))

chain2 = few_shot_prompt | llm
# response = chain2.invoke({"flower_type": "野玫瑰", "occasion": "爱情"})
# print(response.content)


chat_example_prompt = ChatPromptTemplate.from_messages(
    [
        ("human", "鲜花类型: {flower_type}\n场合: {occasion}"),
        ("ai", "{ad_copy}"),
    ]
)

# few shot chat message
few_shot_chat_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=chat_example_prompt,
    examples=samples,
)


# # 2. 组合最终提示（加入系统消息和用户输入）
final_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "请写出合适的文案"),
        few_shot_chat_prompt,
        ("human", "{flower_type}, {occasion}"),
    ]
)

chain3 = final_prompt | llm
# response = chain3.invoke({"flower_type": "野玫瑰", "occasion": "爱情"})
# print(response.content)


# 3。 利用MessagesPlaceholder手动构造example messages 然后传递给模型，比较灵活

# 首先 将示例转换为消息列表（HumanMessage + AIMessage 配对）
example_messages = []
for sample in samples:
    example_messages.append(
        HumanMessage(
            content=f"鲜花类型: {sample['flower_type']}\n场合: {sample['occasion']}"
        )
    )
    example_messages.append(AIMessage(content=sample["ad_copy"]))

# 3. 构建聊天模板，使用 MessagesPlaceholder 插入示例
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一位专业的鲜花店文案撰写员。"),
        MessagesPlaceholder(variable_name="examples"),  # 示例消息将在这里插入
        ("human", "鲜花类型: {flower_type}\n场合: {occasion}"),
    ]
)

chain4 = prompt | llm
# 调用链，传入变量（注意：需要同时传递 examples、flower_type、occasion）
response = chain4.invoke(
    {"examples": example_messages, "flower_type": "向日葵", "occasion": "鼓励"}
)
print(response.content)
